from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import hashlib
import imagehash
from PIL import Image
import io
import sqlite3
from datetime import datetime
import os
from typing import Optional, Dict
import numpy as np
from pathlib import Path
import subprocess
import tempfile
import wave
import struct

# Import our custom modules
from blockchain import BlockchainManager
from ai_detector import AITamperingDetector

app = FastAPI(title="Authx API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
print("Initializing Authx backend services...")
try:
    blockchain_manager = BlockchainManager()
    print("✓ Blockchain manager initialized")
except Exception as e:
    print(f"⚠ Blockchain manager error: {e}")
    blockchain_manager = None

try:
    ai_detector = AITamperingDetector()
    print("✓ AI detector initialized")
except Exception as e:
    print(f"⚠ AI detector error: {e}")
    ai_detector = None

# Database setup
DATABASE_PATH = "authx.db"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def init_db():
    """Initialize SQLite database with schema"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if we need to add new columns to existing table
    cursor.execute("PRAGMA table_info(content_registry)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_name TEXT NOT NULL,
            owner_address TEXT,
            content_type TEXT NOT NULL,
            description TEXT,
            ai_tool TEXT,
            sha256 TEXT UNIQUE NOT NULL,
            phash TEXT,
            dhash TEXT,
            ahash TEXT,
            audio_fingerprint TEXT,
            video_fingerprint TEXT,
            text_fingerprint TEXT,
            file_path TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tx_hash TEXT,
            block_number INTEGER,
            tamper_score REAL,
            tamper_confidence REAL,
            detected_artifacts TEXT
        )
    """)
    
    # Add new columns if they don't exist
    new_columns = [
        ("dhash", "TEXT"),
        ("ahash", "TEXT"),
        ("audio_fingerprint", "TEXT"),
        ("video_fingerprint", "TEXT"),
        ("text_fingerprint", "TEXT")
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE content_registry ADD COLUMN {col_name} {col_type}")
                print(f"✓ Added column: {col_name}")
            except sqlite3.OperationalError:
                pass
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sha256 ON content_registry(sha256)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_phash ON content_registry(phash)")
    
    conn.commit()
    conn.close()

init_db()

def compute_sha256(file_bytes: bytes) -> str:
    """Compute SHA-256 hash of file"""
    return hashlib.sha256(file_bytes).hexdigest()

def compute_audio_fingerprint(file_bytes: bytes) -> Optional[str]:
    """Compute audio fingerprint using spectral analysis"""
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.audio', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        
        # Try to read as WAV or convert
        try:
            with wave.open(tmp_path, 'rb') as wav:
                frames = wav.readframes(wav.getnframes())
                sample_width = wav.getsampwidth()
                
                # Convert to numpy array
                if sample_width == 1:
                    audio_data = np.frombuffer(frames, dtype=np.uint8)
                elif sample_width == 2:
                    audio_data = np.frombuffer(frames, dtype=np.int16)
                else:
                    audio_data = np.frombuffer(frames, dtype=np.int32)
                
                # Compute spectral hash (simplified)
                # Take FFT of chunks and hash the magnitude peaks
                chunk_size = 4096
                fingerprint = []
                
                for i in range(0, min(len(audio_data), 100000), chunk_size):
                    chunk = audio_data[i:i+chunk_size]
                    if len(chunk) < chunk_size:
                        break
                    
                    # FFT
                    fft = np.fft.rfft(chunk)
                    magnitudes = np.abs(fft)
                    
                    # Get top frequency bins
                    top_bins = np.argsort(magnitudes)[-8:]
                    fingerprint.extend(top_bins)
                
                # Convert to hash string
                fingerprint_str = ''.join([f'{x:04x}' for x in fingerprint[:32]])
                os.unlink(tmp_path)
                return fingerprint_str
        except:
            # If not WAV, try using ffmpeg to extract audio features (if available)
            os.unlink(tmp_path)
            return None
            
    except Exception as e:
        print(f"Error computing audio fingerprint: {e}")
        return None

def compute_video_fingerprint(file_bytes: bytes) -> Optional[str]:
    """Compute video fingerprint by sampling keyframes"""
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.video', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        
        # Try to extract frames using ffmpeg (if available)
        # For now, we'll use a simpler approach: hash chunks of the file
        chunk_size = 1024 * 1024  # 1MB chunks
        fingerprint = []
        
        # Sample 10 chunks across the file
        file_size = len(file_bytes)
        step = max(file_size // 10, chunk_size)
        
        for offset in range(0, file_size, step):
            chunk = file_bytes[offset:offset+chunk_size]
            chunk_hash = hashlib.md5(chunk).hexdigest()[:8]
            fingerprint.append(chunk_hash)
            if len(fingerprint) >= 10:
                break
        
        os.unlink(tmp_path)
        return ''.join(fingerprint)
        
    except Exception as e:
        print(f"Error computing video fingerprint: {e}")
        return None

def compute_text_fingerprint(file_bytes: bytes) -> Optional[str]:
    """Compute text fingerprint using shingling"""
    try:
        # Try to decode as text
        text = file_bytes.decode('utf-8', errors='ignore')
        
        # Remove whitespace and normalize
        text = ' '.join(text.split()).lower()
        
        # Create character-level shingles (n-grams)
        shingle_size = 5
        shingles = set()
        
        for i in range(len(text) - shingle_size + 1):
            shingle = text[i:i+shingle_size]
            shingles.add(shingle)
        
        # Convert shingles to hash
        shingle_hashes = [hash(s) % (2**32) for s in sorted(shingles)][:64]
        fingerprint = ''.join([f'{h:08x}' for h in shingle_hashes[:16]])
        
        return fingerprint
        
    except Exception as e:
        print(f"Error computing text fingerprint: {e}")
        return None

def compute_multi_hashes(file_bytes: bytes, content_type: str) -> Dict:
    """Compute appropriate hashes based on content type"""
    hashes = {
        "phash": None,
        "dhash": None,
        "ahash": None,
        "audio_fingerprint": None,
        "video_fingerprint": None,
        "text_fingerprint": None
    }
    
    if content_type.startswith("image"):
        try:
            image = Image.open(io.BytesIO(file_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            hashes["phash"] = str(imagehash.phash(image, hash_size=8))
            hashes["dhash"] = str(imagehash.dhash(image, hash_size=8))
            hashes["ahash"] = str(imagehash.average_hash(image, hash_size=8))
        except Exception as e:
            print(f"Error computing image hashes: {e}")
    
    elif content_type.startswith("audio"):
        hashes["audio_fingerprint"] = compute_audio_fingerprint(file_bytes)
    
    elif content_type.startswith("video"):
        # For video, compute both video fingerprint and extract a frame for image hash
        hashes["video_fingerprint"] = compute_video_fingerprint(file_bytes)
    
    elif content_type.startswith("text") or "pdf" in content_type.lower():
        hashes["text_fingerprint"] = compute_text_fingerprint(file_bytes)
    
    return hashes

def hamming_distance(hash1: str, hash2: str) -> int:
    """Calculate Hamming distance between two hashes"""
    try:
        if not hash1 or not hash2:
            return 64
        return bin(int(hash1, 16) ^ int(hash2, 16)).count('1')
    except:
        return 64

def string_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings (0-1)"""
    if not str1 or not str2:
        return 0.0
    
    # Simple character-level similarity
    matches = sum(c1 == c2 for c1, c2 in zip(str1, str2))
    max_len = max(len(str1), len(str2))
    return matches / max_len if max_len > 0 else 0.0

def calculate_multi_similarity(new_hashes: dict, stored_hashes: dict, content_type: str) -> dict:
    """Calculate similarity using appropriate algorithms based on content type"""
    distances = {}
    
    if content_type.startswith("image"):
        # Use perceptual hashing for images
        if new_hashes["phash"] and stored_hashes["phash"]:
            distances["phash"] = hamming_distance(new_hashes["phash"], stored_hashes["phash"])
        
        if new_hashes["dhash"] and stored_hashes["dhash"]:
            distances["dhash"] = hamming_distance(new_hashes["dhash"], stored_hashes["dhash"])
        
        if new_hashes["ahash"] and stored_hashes["ahash"]:
            distances["ahash"] = hamming_distance(new_hashes["ahash"], stored_hashes["ahash"])
    
    elif content_type.startswith("audio"):
        # Use audio fingerprint
        if new_hashes["audio_fingerprint"] and stored_hashes["audio_fingerprint"]:
            similarity = string_similarity(new_hashes["audio_fingerprint"], 
                                          stored_hashes["audio_fingerprint"])
            # Convert to distance (higher similarity = lower distance)
            distances["audio"] = int((1.0 - similarity) * 64)
    
    elif content_type.startswith("video"):
        # Use video fingerprint
        if new_hashes["video_fingerprint"] and stored_hashes["video_fingerprint"]:
            similarity = string_similarity(new_hashes["video_fingerprint"], 
                                          stored_hashes["video_fingerprint"])
            distances["video"] = int((1.0 - similarity) * 64)
    
    elif content_type.startswith("text") or "pdf" in content_type.lower():
        # Use text fingerprint
        if new_hashes["text_fingerprint"] and stored_hashes["text_fingerprint"]:
            similarity = string_similarity(new_hashes["text_fingerprint"], 
                                          stored_hashes["text_fingerprint"])
            distances["text"] = int((1.0 - similarity) * 64)
    
    # Get minimum distance (best match)
    if distances:
        min_distance = min(distances.values())
        return {
            "min_distance": min_distance,
            "distances": distances,
            "best_match_type": min(distances, key=distances.get)
        }
    
    return {"min_distance": 64, "distances": {}, "best_match_type": None}

@app.post("/register")
async def register_content(
    owner_name: str = Form(...),
    owner_address: str = Form(""),
    content_type: str = Form(...),
    description: str = Form(""),
    ai_tool: str = Form(""),
    file: UploadFile = File(...)
):
    """Register new content with blockchain and AI verification"""
    try:
        # Read file
        file_bytes = await file.read()
        
        # Determine actual content type from file
        actual_content_type = file.content_type or content_type
        print(f"[Registration] Content type: {actual_content_type}, Size: {len(file_bytes)} bytes")
        
        # Compute hashes
        sha256_hash = compute_sha256(file_bytes)
        hashes = compute_multi_hashes(file_bytes, actual_content_type)
        
        print(f"[Hashing] SHA256: {sha256_hash[:16]}...")
        print(f"[Hashing] Computed fingerprints: {[k for k, v in hashes.items() if v]}")
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Layer 1: Check for exact SHA-256 match
        cursor.execute("SELECT id, owner_name FROM content_registry WHERE sha256 = ?", (sha256_hash,))
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return JSONResponse({
                "status": "already_registered",
                "message": f"Content already registered by {existing[1]}",
                "existing_record": {
                    "id": existing[0],
                    "owner": existing[1]
                }
            }, status_code=409)
        
        # Run AI tampering detection EARLY
        tampering_result = {"tamper_probability": 0.0, "confidence": 0.0, "detected_artifacts": []}
        has_tampering = False
        
        try:
            if ai_detector:
                tampering_result = ai_detector.analyze(file_bytes, actual_content_type)
                tamper_prob = tampering_result.get("tamper_probability", 0)
                has_tampering = tamper_prob > 0.3
                print(f"[AI Detection] Tamper probability: {tamper_prob:.2f}, Has tampering: {has_tampering}")
        except Exception as e:
            print(f"AI detection error (non-fatal): {e}")
        
        # Layer 2: Content-type specific similarity check
        if any(hashes.values()):
            # Query similar content types
            if actual_content_type.startswith("image"):
                query = "SELECT id, owner_name, owner_address, registered_at, phash, dhash, ahash, tamper_score, content_type FROM content_registry WHERE content_type LIKE 'image%'"
            elif actual_content_type.startswith("audio"):
                query = "SELECT id, owner_name, owner_address, registered_at, phash, dhash, ahash, tamper_score, content_type, audio_fingerprint FROM content_registry WHERE content_type LIKE 'audio%'"
            elif actual_content_type.startswith("video"):
                query = "SELECT id, owner_name, owner_address, registered_at, phash, dhash, ahash, tamper_score, content_type, video_fingerprint FROM content_registry WHERE content_type LIKE 'video%'"
            else:
                query = "SELECT id, owner_name, owner_address, registered_at, phash, dhash, ahash, tamper_score, content_type, text_fingerprint FROM content_registry WHERE content_type LIKE 'text%' OR content_type LIKE '%pdf%'"
            
            cursor.execute(query)
            
            # ADAPTIVE THRESHOLDS based on content type and tampering
            if has_tampering:
                # AI-modified: very lenient
                if actual_content_type.startswith("image"):
                    MAX_DISTANCE = 35
                elif actual_content_type.startswith("audio"):
                    MAX_DISTANCE = 40  # Audio more forgiving
                elif actual_content_type.startswith("video"):
                    MAX_DISTANCE = 42  # Video most forgiving
                else:
                    MAX_DISTANCE = 38  # Text/PDF moderate
            else:
                # Natural edits: stricter
                if actual_content_type.startswith("image"):
                    MAX_DISTANCE = 18
                elif actual_content_type.startswith("audio"):
                    MAX_DISTANCE = 25
                elif actual_content_type.startswith("video"):
                    MAX_DISTANCE = 30
                else:
                    MAX_DISTANCE = 20
            
            print(f"[Similarity] Using threshold: {MAX_DISTANCE} (content: {actual_content_type.split('/')[0]}, tampering: {has_tampering})")
            
            for row in cursor.fetchall():
                stored_hashes = {
                    "phash": row[4] if len(row) > 4 else None,
                    "dhash": row[5] if len(row) > 5 else None,
                    "ahash": row[6] if len(row) > 6 else None,
                    "audio_fingerprint": row[9] if len(row) > 9 else None,
                    "video_fingerprint": row[9] if len(row) > 9 and actual_content_type.startswith("video") else None,
                    "text_fingerprint": row[9] if len(row) > 9 and (actual_content_type.startswith("text") or "pdf" in actual_content_type.lower()) else None
                }
                
                # Calculate similarity using appropriate algorithm
                similarity = calculate_multi_similarity(hashes, stored_hashes, actual_content_type)
                min_distance = similarity["min_distance"]
                
                print(f"[Similarity] Comparing to record {row[0]}:")
                print(f"  - Distances: {similarity['distances']}")
                print(f"  - Min distance: {min_distance} (threshold: {MAX_DISTANCE})")
                
                # Check if too similar
                if min_distance <= MAX_DISTANCE:
                    similarity_percentage = max(0, round((1 - min_distance / 64) * 100))
                    conn.close()
                    
                    content_type_name = actual_content_type.split('/')[0].title()
                    
                    if has_tampering:
                        message = f"🚫 AI-modified {content_type_name.lower()} detected! Very similar to content registered by {row[1]}"
                        recommendation = (
                            f"Our AI detection flagged this as modified "
                            f"(similarity: {similarity_percentage}%, tamper: {tampering_result.get('tamper_probability', 0):.1%}). "
                            f"Original content is protected. If you're the creator, use your unmodified original."
                        )
                    else:
                        message = f"⚠️ Similar {content_type_name.lower()} already registered by {row[1]}"
                        recommendation = f"This appears to be a near-duplicate (similarity: {similarity_percentage}%). Verify ownership with the original creator."
                    
                    return JSONResponse({
                        "status": "similar_content_exists",
                        "message": message,
                        "similarity": f"{similarity_percentage}%",
                        "hash_distance": min_distance,
                        "best_match_algorithm": similarity['best_match_type'],
                        "all_distances": similarity['distances'],
                        "content_type": content_type_name,
                        "ai_tampering_detected": has_tampering,
                        "tampering_score": round(tampering_result.get("tamper_probability", 0), 3),
                        "original_record": {
                            "id": row[0],
                            "owner_name": row[1],
                            "owner_address": row[2],
                            "registered_at": row[3],
                            "original_tamper_score": row[7] if len(row) > 7 else 0.0
                        },
                        "recommendation": recommendation
                    }, status_code=409)
        
        # Layer 3: Block extremely high tampering
        if tampering_result.get("tamper_probability", 0) > 0.8:
            conn.close()
            content_type_name = actual_content_type.split('/')[0].title()
            return JSONResponse({
                "status": "high_tampering_detected",
                "message": f"⚠️ {content_type_name} shows signs of heavy AI modification",
                "tampering_analysis": tampering_result,
                "recommendation": "This content appears heavily AI-modified. If you're the original creator, register the original version first."
            }, status_code=400)
        
        # Save file
        file_extension = Path(file.filename).suffix
        file_path = UPLOAD_DIR / f"{sha256_hash}{file_extension}"
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        
        # Register on blockchain
        try:
            blockchain_result = blockchain_manager.register(
                sha256_hash=sha256_hash,
                owner_name=owner_name,
                content_type=actual_content_type
            )
        except Exception as e:
            print(f"Blockchain error (non-fatal): {e}")
            blockchain_result = {"tx_hash": None, "block_number": None}
        
        # Store in database
        try:
            cursor.execute("""
                INSERT INTO content_registry 
                (owner_name, owner_address, content_type, description, ai_tool, 
                 sha256, phash, dhash, ahash, audio_fingerprint, video_fingerprint, 
                 text_fingerprint, file_path, tx_hash, block_number, 
                 tamper_score, tamper_confidence, detected_artifacts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                owner_name, owner_address, actual_content_type, description, ai_tool,
                sha256_hash, hashes["phash"], hashes["dhash"], hashes["ahash"],
                hashes["audio_fingerprint"], hashes["video_fingerprint"],
                hashes["text_fingerprint"], str(file_path),
                blockchain_result.get("tx_hash"),
                blockchain_result.get("block_number"),
                tampering_result.get("tamper_probability", 0.0),
                tampering_result.get("confidence", 0.0),
                ",".join(tampering_result.get("detected_artifacts", []))
            ))
            
            content_id = cursor.lastrowid
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            conn.close()
        
        return JSONResponse({
            "status": "ok",
            "message": "Content registered successfully",
            "proof": {
                "id": content_id,
                "sha256": sha256_hash,
                "phash": hashes.get("phash"),
                "fingerprints": {k: v for k, v in hashes.items() if v and k != "phash"},
                "tx_hash": blockchain_result.get("tx_hash"),
                "block_number": blockchain_result.get("block_number"),
                "tamper_score": tampering_result.get("tamper_probability", 0.0),
                "proof_url": f"http://127.0.0.1:8000/proof/{content_id}",
                "tampering_analysis": tampering_result
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Registration error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/verify")
async def verify_content(file: UploadFile = File(...)):
    """Verify content authenticity using multi-layer detection"""
    try:
        file_bytes = await file.read()
        content_type = file.content_type or "application/octet-stream"
        
        sha256_hash = compute_sha256(file_bytes)
        hashes = compute_multi_hashes(file_bytes, content_type)
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Layer 1: Exact match
        cursor.execute("""
            SELECT id, owner_name, owner_address, registered_at, tx_hash, 
                   tamper_score, content_type
            FROM content_registry WHERE sha256 = ?
        """, (sha256_hash,))
        exact_match = cursor.fetchone()
        
        if exact_match:
            conn.close()
            return JSONResponse({
                "result": "exact_match",
                "confidence": 1.0,
                "verification_type": "sha256_exact",
                "match_details": {
                    "id": exact_match[0],
                    "owner_name": exact_match[1],
                    "owner_address": exact_match[2],
                    "registered_at": exact_match[3],
                    "tx_hash": exact_match[4],
                    "original_tamper_score": exact_match[5] or 0.0,
                    "content_type": exact_match[6]
                },
                "message": "✅ Exact match - Content is authentic original"
            })
        
        # Layer 2: Similarity check
        cursor.execute("SELECT id, owner_name, owner_address, registered_at, tx_hash, phash, dhash, ahash, tamper_score, content_type, audio_fingerprint, video_fingerprint, text_fingerprint FROM content_registry")
        
        best_match = None
        best_distance = float('inf')
        
        for row in cursor.fetchall():
            stored_content_type = row[9]
            
            # Only compare same content types
            if content_type.split('/')[0] != stored_content_type.split('/')[0]:
                continue
            
            stored_hashes = {
                "phash": row[5],
                "dhash": row[6],
                "ahash": row[7],
                "audio_fingerprint": row[10],
                "video_fingerprint": row[11],
                "text_fingerprint": row[12]
            }
            
            similarity = calculate_multi_similarity(hashes, stored_hashes, content_type)
            
            if similarity["min_distance"] <= 35 and similarity["min_distance"] < best_distance:
                best_distance = similarity["min_distance"]
                best_match = {
                    "id": row[0],
                    "owner_name": row[1],
                    "owner_address": row[2],
                    "registered_at": row[3],
                    "tx_hash": row[4],
                    "hash_distance": similarity["min_distance"],
                    "match_type": similarity["best_match_type"],
                    "original_tamper_score": row[8] or 0.0,
                    "content_type": stored_content_type
                }
        
        # AI tampering detection
        tampering_result = ai_detector.analyze(file_bytes, content_type) if ai_detector else {}
        
        conn.close()
        
        if best_match:
            confidence = max(0.0, 1.0 - (best_match["hash_distance"] / 64.0))
            is_tampered = tampering_result.get("tamper_probability", 0) > 0.3
            
            return JSONResponse({
                "result": "near_duplicate",
                "confidence": confidence,
                "verification_type": f"similarity_{best_match['match_type']}",
                "match_details": best_match,
                "tampering_analysis": tampering_result,
                "potential_theft": is_tampered,
                "message": f"⚠️ Similar content found - AI modification detected. Original by {best_match['owner_name']}" if is_tampered 
                          else f"ℹ️ Near-duplicate found. Original by {best_match['owner_name']}"
            })
        
        return JSONResponse({
            "result": "not_found",
            "confidence": 0.0,
            "tampering_analysis": tampering_result,
            "message": "❌ Content not found in database",
            "suggestions": [
                "This content may be original and not yet registered",
                "Try registering it to establish ownership"
            ]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/proof/{content_id}")
async def get_proof(content_id: int):
    """Retrieve proof certificate"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, owner_name, owner_address, content_type, description, 
                   ai_tool, sha256, phash, registered_at, tx_hash, block_number,
                   tamper_score, tamper_confidence, detected_artifacts
            FROM content_registry WHERE id = ?
        """, (content_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="Proof not found")
        
        artifacts = result[13].split(",") if result[13] else []
        
        return JSONResponse({
            "id": result[0],
            "owner_name": result[1],
            "owner_address": result[2],
            "content_type": result[3],
            "description": result[4],
            "ai_tool": result[5],
            "sha256": result[6],
            "phash": result[7],
            "registered_at": result[8],
            "tx_hash": result[9],
            "block_number": result[10],
            "tamper_score": result[11],
            "tampering_analysis": {
                "tamper_probability": result[11] or 0.0,
                "confidence": result[12] or 0.0,
                "detected_artifacts": artifacts
            },
            "verification_url": f"http://127.0.0.1:8000/verify"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("Starting Authx Backend Server")
    print("="*60)
    print(f"Server will run at: http://127.0.0.1:8000")
    print(f"API Documentation: http://127.0.0.1:8000/docs")
    print(f"Health Check: http://127.0.0.1:8000/health")
    print("="*60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="debug")