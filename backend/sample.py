"""app.py - Main FastAPI application for Authx backend"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from video_fingerprint_patch import compute_video_fingerprint, compare_video_fingerprints
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
import re
import hashlib
from collections import Counter
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
    """
    Improved audio fingerprinting using multiple spectral features
    More robust to edits like volume changes, trimming, compression
    """
    try:
        with tempfile.NamedTemporaryFile(suffix='.audio', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        
        try:
            with wave.open(tmp_path, 'rb') as wav:
                frames = wav.readframes(wav.getnframes())
                sample_width = wav.getsampwidth()
                framerate = wav.getframerate()
                
                # Convert to numpy array
                if sample_width == 1:
                    audio_data = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
                elif sample_width == 2:
                    audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                else:
                    audio_data = np.frombuffer(frames, dtype=np.int32).astype(np.float32)
                
                # Normalize
                audio_data = audio_data / np.max(np.abs(audio_data) + 1e-9)
                
                # IMPROVED: Use multiple robust features
                fingerprint_parts = []
                
                # 1. Spectral centroid pattern (robust to volume changes)
                chunk_size = 8192
                num_chunks = min(50, len(audio_data) // chunk_size)
                
                for i in range(num_chunks):
                    start = i * len(audio_data) // num_chunks
                    end = start + chunk_size
                    chunk = audio_data[start:end]
                    
                    if len(chunk) < chunk_size:
                        break
                    
                    # FFT
                    fft = np.fft.rfft(chunk)
                    magnitudes = np.abs(fft)
                    
                    # Spectral centroid (weighted average of frequencies)
                    freqs = np.fft.rfftfreq(len(chunk), 1/framerate)
                    centroid = np.sum(freqs * magnitudes) / (np.sum(magnitudes) + 1e-9)
                    
                    # Quantize to make robust
                    centroid_bin = int(centroid / 100)  # 100 Hz bins
                    fingerprint_parts.append(f'{centroid_bin:04x}')
                
                # 2. Energy distribution pattern (robust to compression)
                energy_bands = []
                band_edges = [0, 500, 2000, 5000, 10000, framerate//2]
                
                for i in range(len(band_edges)-1):
                    band_start = int(band_edges[i] * len(audio_data) / framerate)
                    band_end = int(band_edges[i+1] * len(audio_data) / framerate)
                    band_energy = np.sum(audio_data[band_start:band_end]**2)
                    energy_bands.append(int(np.log10(band_energy + 1) * 100))
                
                fingerprint_parts.extend([f'{e:04x}' for e in energy_bands])
                
                # 3. Zero crossing rate pattern (robust to pitch shifts)
                zcr_chunks = []
                for i in range(0, len(audio_data) - chunk_size, len(audio_data) // 20):
                    chunk = audio_data[i:i+chunk_size]
                    zcr = np.sum(np.abs(np.diff(np.sign(chunk)))) / len(chunk)
                    zcr_chunks.append(int(zcr * 1000))
                
                fingerprint_parts.extend([f'{z:03x}' for z in zcr_chunks[:10]])
                
                os.unlink(tmp_path)
                return ''.join(fingerprint_parts[:64])  # Fixed length
                
        except Exception as e:
            os.unlink(tmp_path)
            return None
            
    except Exception as e:
        print(f"Error computing audio fingerprint: {e}")
        return None





def compute_text_fingerprint(file_bytes: bytes) -> Optional[str]:
    """
    FIXED: More sensitive text fingerprinting
    """
    try:
        # Try to decode as text
        text = file_bytes.decode('utf-8', errors='ignore')
        
        # Normalize text
        text = ' '.join(text.split()).lower()
        text_no_punct = re.sub(r'[^\w\s]', '', text)
        
        fingerprint_parts = []
        
        # 1. Character n-grams (5-grams for better matching)
        char_ngrams = set()
        for i in range(len(text_no_punct) - 4):
            ngram = text_no_punct[i:i+5]
            if ngram.strip():
                char_ngrams.add(ngram)
        
        # Take top 50 most frequent
        char_hashes = sorted([hash(c) % (2**32) for c in char_ngrams])[:50]
        fingerprint_parts.extend([f'{h:08x}' for h in char_hashes])
        
        # 2. Word-level n-grams (trigrams)
        words = text_no_punct.split()
        word_trigrams = set()
        for i in range(len(words) - 2):
            trigram = ' '.join(words[i:i+3])
            word_trigrams.add(trigram)
        
        trigram_hashes = sorted([hash(t) % (2**32) for t in word_trigrams])[:30]
        fingerprint_parts.extend([f'{h:08x}' for h in trigram_hashes])
        
        # 3. Word frequency signature
        from collections import Counter
        word_freq = Counter(words)
        top_words = [w for w, _ in word_freq.most_common(30)]
        word_sig = ''.join(sorted(top_words))
        word_sig_hash = hashlib.md5(word_sig.encode()).hexdigest()
        fingerprint_parts.append(word_sig_hash)
        
        # 4. Structural signature
        sentences = re.split(r'[.!?]+', text)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        length_pattern = [min(l // 3, 20) for l in sentence_lengths[:30]]
        length_hash = hashlib.md5(str(length_pattern).encode()).hexdigest()
        fingerprint_parts.append(length_hash)
        
        result = ''.join(fingerprint_parts)
        print(f"[Text Fingerprint] Generated: {len(result)} chars")
        return result
        
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

def fuzzy_string_similarity(str1: str, str2: str, window_size: int = 8) -> float:
    """
    FIXED: Improved similarity using multiple methods for better accuracy
    """
    if not str1 or not str2:
        return 0.0
    
    # Method 1: Sliding window (Jaccard)
    if len(str1) >= window_size and len(str2) >= window_size:
        windows1 = set(str1[i:i+window_size] for i in range(len(str1) - window_size + 1))
        windows2 = set(str2[i:i+window_size] for i in range(len(str2) - window_size + 1))
        
        intersection = len(windows1 & windows2)
        union = len(windows1 | windows2)
        
        jaccard_sim = intersection / union if union > 0 else 0.0
    else:
        jaccard_sim = 0.0
    
    # Method 2: Character-level similarity (for robustness)
    min_len = min(len(str1), len(str2))
    max_len = max(len(str1), len(str2))
    
    if min_len > 0:
        matches = sum(c1 == c2 for c1, c2 in zip(str1[:min_len], str2[:min_len]))
        char_sim = matches / max_len
    else:
        char_sim = 0.0
    
    # Method 3: Subsequence matching
    def longest_common_subsequence(s1, s2):
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    lcs_length = longest_common_subsequence(str1, str2)
    lcs_sim = lcs_length / max_len if max_len > 0 else 0.0
    
    # Combine methods with weights
    # Jaccard is most important, then LCS, then character similarity
    combined_similarity = (
        jaccard_sim * 0.5 +
        lcs_sim * 0.3 +
        char_sim * 0.2
    )
    
    return combined_similarity


def calculate_multi_similarity(new_hashes: dict, stored_hashes: dict, content_type: str) -> dict:
    """
    FIXED similarity calculation with proper thresholds
    """
    distances = {}
    
    if content_type.startswith("image"):
        # Use perceptual hashing for images (this works fine)
        if new_hashes["phash"] and stored_hashes["phash"]:
            distances["phash"] = hamming_distance(new_hashes["phash"], stored_hashes["phash"])
        
        if new_hashes["dhash"] and stored_hashes["dhash"]:
            distances["dhash"] = hamming_distance(new_hashes["dhash"], stored_hashes["dhash"])
        
        if new_hashes["ahash"] and stored_hashes["ahash"]:
            distances["ahash"] = hamming_distance(new_hashes["ahash"], stored_hashes["ahash"])
    
    elif content_type.startswith("audio"):
        # FIXED: Use improved fuzzy matching for audio
        if new_hashes["audio_fingerprint"] and stored_hashes["audio_fingerprint"]:
            similarity = fuzzy_string_similarity(
                new_hashes["audio_fingerprint"], 
                stored_hashes["audio_fingerprint"],
                window_size=8  # Smaller window for more sensitivity
            )
            # Convert to distance (0-64 scale) - FIXED conversion
            distances["audio"] = int((1.0 - similarity) * 64)
            print(f"[Audio Debug] Similarity: {similarity:.3f}, Distance: {distances['audio']}")
    
    elif content_type.startswith("video"):
        if new_hashes["video_fingerprint"] and stored_hashes["video_fingerprint"]:
            distances["video"] = compare_video_fingerprints(
                new_hashes["video_fingerprint"],
                stored_hashes["video_fingerprint"]
            )
    
    elif content_type.startswith("text") or "pdf" in content_type.lower():
        # FIXED: Use improved fuzzy matching for text
        if new_hashes["text_fingerprint"] and stored_hashes["text_fingerprint"]:
            similarity = fuzzy_string_similarity(
                new_hashes["text_fingerprint"], 
                stored_hashes["text_fingerprint"],
                window_size=12  # Smaller window for text sensitivity
            )
            distances["text"] = int((1.0 - similarity) * 64)
            print(f"[Text Debug] Similarity: {similarity:.3f}, Distance: {distances['text']}")
    
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
            content_modality = actual_content_type.split('/')[0]  # 'video', 'audio', 'text', 'image'
            if content_modality == "image":
                query = """SELECT id, owner_name, owner_address, registered_at, 
                   phash, dhash, ahash, tamper_score, content_type 
                   FROM content_registry WHERE content_type LIKE 'image%'"""
            elif content_modality == "audio":
                query = """SELECT id, owner_name, owner_address, registered_at, 
                   phash, dhash, ahash, tamper_score, content_type, audio_fingerprint 
                   FROM content_registry WHERE content_type LIKE 'audio%'"""
            elif content_modality == "video":
                query = """SELECT id, owner_name, owner_address, registered_at, 
                   phash, dhash, ahash, tamper_score, content_type, video_fingerprint 
                   FROM content_registry WHERE content_type LIKE 'video%'"""
            else:  # text/documents
                query = """SELECT id, owner_name, owner_address, registered_at, 
                   phash, dhash, ahash, tamper_score, content_type, text_fingerprint 
                   FROM content_registry WHERE content_type LIKE 'text%' 
                   OR content_type LIKE '%pdf%' OR content_type LIKE 'application%'"""
            cursor.execute(query)
            
            # ADAPTIVE THRESHOLDS based on content type and tampering
            def get_threshold(content_type, has_tampering):
                if has_tampering:
                    if content_type.startswith("image"): return 35
                    elif content_type.startswith("audio"): return 40  
                    elif content_type.startswith("video"): return 16 if has_tampering else 10
                    else: return 38  # FIXED: was 42 for text
                else:
                    if content_type.startswith("image"): return 18
                    elif content_type.startswith("audio"): return 25  
                    elif content_type.startswith("video"): return 10  # FIXED: was 38
                    else: return 22
            MAX_DISTANCE = get_threshold(actual_content_type, has_tampering)
            
            for row in cursor.fetchall():
                stored_hashes = {
            "phash": row[4] if len(row) > 4 else None,
            "dhash": row[5] if len(row) > 5 else None,
            "ahash": row[6] if len(row) > 6 else None,
            "audio_fingerprint": row[9] if len(row) > 9 and content_modality == "audio" else None,
            "video_fingerprint": row[9] if len(row) > 9 and content_modality == "video" else None,
            "text_fingerprint": row[9] if len(row) > 9 and content_modality in ["text", "application"] else None
        }
                if content_modality == "audio" and not stored_hashes.get("audio_fingerprint"):
                    continue
                if content_modality == "video" and not stored_hashes.get("video_fingerprint"):
                    continue
                if content_modality in ("text", "application") and not stored_hashes.get("text_fingerprint"):
                    continue
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
            _vt = 10 if content_type.startswith("video") else 35
            if similarity["min_distance"] <= _vt and similarity["min_distance"] < best_distance:
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