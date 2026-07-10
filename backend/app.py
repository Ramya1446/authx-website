"""
app.py — Journal AuthX Backend (upgraded from Conference AuthX)
===============================================================

New endpoints
-------------
POST /analyze              — Full multimodal forensic analysis (Contribution 1)
POST /authenticity-score   — Unified Authenticity + Trust + Risk score (Contribution 2)
POST /cross-modal-verify   — Cross-modal consistency verification (Contribution 3)
POST /register             — Enhanced registration with all new signals stored
POST /verify               — Enhanced verification with unified score in response
GET  /proof/{id}           — Returns full forensic evidence including localization map
GET  /health               — Health check

All existing endpoints are preserved and backward-compatible.
"""

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
from typing import Optional, Dict, List
import numpy as np
from pathlib import Path
import subprocess
import tempfile
import wave
import struct
import re
import json
from collections import Counter

# ── Core modules (unchanged) ─────────────────────────────────
from video_fingerprint_patch import compute_video_fingerprint, compare_video_fingerprints
from blockchain import BlockchainManager
from ai_detector import AITamperingDetector

# ── Journal AuthX: new modules ───────────────────────────────
from multimodal_forensics import MultimodalForensics
from authenticity_scorer import AuthenticityScorer
from cross_modal_verifier import CrossModalVerifier

app = FastAPI(
    title="Journal AuthX API",
    version="2.0.0",
    description="Hybrid AI-Blockchain Multimodal Digital Content Authentication Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Service initialisation ────────────────────────────────────
print("\n" + "=" * 60)
print("  Initialising Journal AuthX backend services …")
print("=" * 60)

def _safe_init(name, factory):
    try:
        obj = factory()
        print(f"  ✓ {name}")
        return obj
    except Exception as e:
        print(f"  ⚠ {name}: {e}")
        return None

blockchain_manager  = _safe_init("Blockchain manager",      BlockchainManager)
ai_detector         = _safe_init("AI detector (legacy)",    AITamperingDetector)
forensics_engine    = _safe_init("Multimodal forensics",    MultimodalForensics)
authenticity_scorer = _safe_init("Authenticity scorer",     AuthenticityScorer)
cross_modal_verifier= _safe_init("Cross-modal verifier",    CrossModalVerifier)

print("=" * 60 + "\n")

# ── Database ──────────────────────────────────────────────────
DATABASE_PATH = "authx.db"
UPLOAD_DIR    = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def init_db():
    conn   = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

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
            -- Legacy AI detection
            tamper_score REAL,
            tamper_confidence REAL,
            detected_artifacts TEXT,
            -- Journal AuthX: new forensic columns
            authenticity_score REAL,
            trust_score REAL,
            risk_level TEXT,
            forensic_localization TEXT,
            forensic_artifacts TEXT,
            cross_modal_score REAL
        )
    """)

    # Migrate existing tables
    cursor.execute("PRAGMA table_info(content_registry)")
    existing = {col[1] for col in cursor.fetchall()}
    new_cols = [
        ("dhash",                "TEXT"),
        ("ahash",                "TEXT"),
        ("audio_fingerprint",    "TEXT"),
        ("video_fingerprint",    "TEXT"),
        ("text_fingerprint",     "TEXT"),
        ("authenticity_score",   "REAL"),
        ("trust_score",          "REAL"),
        ("risk_level",           "TEXT"),
        ("forensic_localization","TEXT"),
        ("forensic_artifacts",   "TEXT"),
        ("cross_modal_score",    "REAL"),
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing:
            try:
                cursor.execute(f"ALTER TABLE content_registry ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sha256 ON content_registry(sha256)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_phash  ON content_registry(phash)")
    conn.commit()
    conn.close()


init_db()


# ═════════════════════════════════════════════════════════════
#  SHARED UTILITIES  (kept from Conference AuthX)
# ═════════════════════════════════════════════════════════════

def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def compute_audio_fingerprint(file_bytes: bytes) -> Optional[str]:
    try:
        with tempfile.NamedTemporaryFile(suffix='.audio', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            with wave.open(tmp_path, 'rb') as wav:
                frames     = wav.readframes(wav.getnframes())
                sample_width = wav.getsampwidth()
                framerate  = wav.getframerate()
                if sample_width == 1:
                    audio_data = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
                elif sample_width == 2:
                    audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                else:
                    audio_data = np.frombuffer(frames, dtype=np.int32).astype(np.float32)
                audio_data = audio_data / np.max(np.abs(audio_data) + 1e-9)
                parts = []
                chunk_size = 8192
                num_chunks = min(50, len(audio_data) // chunk_size)
                for i in range(num_chunks):
                    start = i * len(audio_data) // num_chunks
                    chunk = audio_data[start:start + chunk_size]
                    if len(chunk) < chunk_size: break
                    fft = np.fft.rfft(chunk)
                    magnitudes = np.abs(fft)
                    freqs = np.fft.rfftfreq(len(chunk), 1 / framerate)
                    centroid = np.sum(freqs * magnitudes) / (np.sum(magnitudes) + 1e-9)
                    parts.append(f'{int(centroid / 100):04x}')
                os.unlink(tmp_path)
                return ''.join(parts[:64])
        except Exception:
            os.unlink(tmp_path)
            return None
    except Exception:
        return None

def _clean_pdf_text(text: str) -> str:
    """
    Normalize PDF-extracted text to maximize similarity detection
    across different versions/formats of the same document.
    """
    # Remove IEEE copyright boilerplate (XXX-X-XXXX-XXXX-X/XX/$XX.00)
    text = re.sub(r'x{2,}[\w\-x©$\.\/]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\d{2,4}xx\s+ieee', '', text, flags=re.IGNORECASE)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove figure and table captions
    text = re.sub(r'fig\.?\s*\d+[^.\n]*\.', '', text, flags=re.IGNORECASE)
    text = re.sub(r'figure\s*\d+[^.\n]*\.', '', text, flags=re.IGNORECASE)
    text = re.sub(r'table\s+[ivxlIVXL\d]+[^.\n]*\.', '', text, flags=re.IGNORECASE)
    
    # Remove reference section entirely (both papers share refs but
    # minor formatting differences destroy shingle matches)
    text = re.sub(r'\breferences\b.*', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove standalone numbers (page numbers, citation brackets like [1])
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\b\d{1,4}\b', '', text)
    
    # Normalize department/school/affiliation variants so they don't
    # create mismatches between conference and journal versions
    text = re.sub(r'\b(school|department)\s+of\b', 'dept of', text, flags=re.IGNORECASE)
    text = re.sub(r'\bassistant professor\b.*?(?=abstract|i\s*\.|introduction)', 
                  '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Collapse all whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def compute_text_fingerprint(file_bytes: bytes, is_pdf: bool = False) -> Optional[str]:
    try:
        if is_pdf:
            try:
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                print(f"[TextFP] PDF extracted {len(text)} chars")
            except Exception as e:
                print(f"[TextFP] fitz failed: {e}")
                text = file_bytes.decode('utf-8', errors='ignore')
        else:
            text = file_bytes.decode('utf-8', errors='ignore')

        # Clean exactly like your friend's clean_text()
        import string
        text = text.lower()
        text = text.translate(str.maketrans("", "", string.punctuation))
        text = " ".join(text.split())

        if len(text) < 50:
            return None

        # Store the cleaned text itself — comparison happens at verify time
        # Truncate to 8000 chars to fit DB column comfortably
        return text[:8000]

    except Exception as e:
        print(f"[TextFP] Error: {e}")
        return None


def compute_multi_hashes(file_bytes: bytes, content_type: str) -> Dict:
    hashes = {k: None for k in
              ["phash", "dhash", "ahash", "audio_fingerprint",
               "video_fingerprint", "text_fingerprint"]}
    if content_type.startswith("image"):
        try:
            image = Image.open(io.BytesIO(file_bytes))
            if image.mode != 'RGB': image = image.convert('RGB')
            hashes["phash"] = str(imagehash.phash(image, hash_size=8))
            hashes["dhash"] = str(imagehash.dhash(image, hash_size=8))
            hashes["ahash"] = str(imagehash.average_hash(image, hash_size=8))
        except Exception: pass
    elif content_type.startswith("audio"):
        hashes["audio_fingerprint"] = compute_audio_fingerprint(file_bytes)
    elif content_type.startswith("video"):
        hashes["video_fingerprint"] = compute_video_fingerprint(file_bytes)
    elif content_type.startswith("text") or "pdf" in content_type.lower():
        is_pdf = "pdf" in content_type.lower()
        fp = compute_text_fingerprint(file_bytes, is_pdf=is_pdf)
        print(f"[MultiHash] text_fingerprint length={len(fp) if fp else None}, prefix={fp[:32] if fp else None}")
        hashes["text_fingerprint"] = fp
    return hashes


def hamming_distance(hash1: str, hash2: str) -> int:
    try:
        if not hash1 or not hash2: return 64
        return bin(int(hash1, 16) ^ int(hash2, 16)).count('1')
    except Exception:
        return 64


def fuzzy_string_similarity(str1: str, str2: str, window_size: int = 8) -> float:
    if not str1 or not str2: return 0.0
    if len(str1) >= window_size and len(str2) >= window_size:
        w1 = set(str1[i:i+window_size] for i in range(len(str1) - window_size + 1))
        w2 = set(str2[i:i+window_size] for i in range(len(str2) - window_size + 1))
        inter = len(w1 & w2); union = len(w1 | w2)
        jaccard = inter / union if union > 0 else 0.0
    else:
        jaccard = 0.0
    min_len = min(len(str1), len(str2)); max_len = max(len(str1), len(str2))
    char_sim = sum(c1 == c2 for c1, c2 in zip(str1[:min_len], str2[:min_len])) / max(max_len, 1)
    return jaccard * 0.6 + char_sim * 0.4


def calculate_multi_similarity(new_hashes: dict, stored_hashes: dict, content_type: str) -> dict:
    distances = {}
    if content_type.startswith("image"):
        for key in ["phash", "dhash", "ahash"]:
            if new_hashes.get(key) and stored_hashes.get(key):
                distances[key] = hamming_distance(new_hashes[key], stored_hashes[key])
    elif content_type.startswith("audio"):
        if new_hashes.get("audio_fingerprint") and stored_hashes.get("audio_fingerprint"):
            sim = fuzzy_string_similarity(
                new_hashes["audio_fingerprint"], stored_hashes["audio_fingerprint"], 8)
            distances["audio"] = int((1.0 - sim) * 64)
    elif content_type.startswith("video"):
        if new_hashes.get("video_fingerprint") and stored_hashes.get("video_fingerprint"):
            distances["video"] = compare_video_fingerprints(
                new_hashes["video_fingerprint"], stored_hashes["video_fingerprint"])
    else:
        if new_hashes.get("text_fingerprint") and stored_hashes.get("text_fingerprint"):
            sim = _text_jaccard(
                new_hashes["text_fingerprint"],
                stored_hashes["text_fingerprint"],
                n=3
            )
            distances["text"] = int((1.0 - sim) * 64)
            print(f"[TextSim] distance={distances['text']}")

    if distances:
        min_d = min(distances.values())
        return {"min_distance": min_d, "distances": distances,
                "best_match_type": min(distances, key=distances.get)}
    return {"min_distance": 64, "distances": {}, "best_match_type": None}


def get_threshold(content_type: str, has_tampering: bool) -> int:
    if has_tampering:
        if content_type.startswith("image"):  return 35
        if content_type.startswith("audio"):  return 40
        if content_type.startswith("video"):  return 30
        return 45   # text — tampered docs may differ more
    else:
        if content_type.startswith("image"):  return 18
        if content_type.startswith("audio"):  return 25
        if content_type.startswith("video"):  return 28
        return 38   # text — 75%+ similar = distance ≤ 38 (jaccard ≥ ~0.40)

def _text_jaccard(fp1: str, fp2: str, n: int = 3) -> float:
    """
    Character n-gram Jaccard similarity.
    Adapted from friend's plagiarism tracker — robust to paraphrasing.
    """
    try:
        def char_ngrams(text):
            text = text.replace(" ", "_")  # preserve word boundaries
            return set(text[i:i+n] for i in range(len(text) - n + 1))

        set1 = char_ngrams(fp1)
        set2 = char_ngrams(fp2)

        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        jaccard = len(set1 & set2) / len(set1 | set2)
        print(f"[TextSim] char-3gram jaccard={jaccard:.3f}")
        return jaccard
    except Exception:
        return 0.0
# ═════════════════════════════════════════════════════════════
#  JOURNAL AUTHX: CONTRIBUTION 1 — MULTIMODAL FORENSICS
# ═════════════════════════════════════════════════════════════

@app.post("/analyze")
async def analyze_content(file: UploadFile = File(...)):
    """
    Full multimodal forensic analysis with tampering localization.

    Returns per-modality forensic report including:
    - tamper_probability
    - confidence
    - detected_artifacts
    - localization (spatial / temporal / textual regions)
    - analysis_details (per-method scores)
    """
    try:
        file_bytes   = await file.read()
        content_type = file.content_type or "application/octet-stream"

        if not forensics_engine:
            raise HTTPException(503, "Forensics engine not available.")

        report = forensics_engine.analyze(file_bytes, content_type)

        return JSONResponse({
            "status": "analyzed",
            "file_name": file.filename,
            "content_type": content_type,
            "forensic_report": report.to_dict(),
        })

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(500, f"Analysis failed: {str(e)}")


# ═════════════════════════════════════════════════════════════
#  JOURNAL AUTHX: CONTRIBUTION 2 — UNIFIED AUTHENTICITY SCORE
# ═════════════════════════════════════════════════════════════

@app.post("/authenticity-score")
async def compute_authenticity_score(
    file: UploadFile = File(...),
    blockchain_verified: bool = Form(False),
    exact_hash_match:    bool = Form(False),
):
    """
    Compute the unified Authenticity Score (0–100), Trust Score (0–100),
    and Risk Level (LOW / MEDIUM / HIGH / CRITICAL).

    Combines:
    - Full forensic analysis (Contribution 1)
    - Blockchain verification status
    - Hash integrity
    - Localization density
    """
    try:
        file_bytes   = await file.read()
        content_type = file.content_type or "application/octet-stream"

        if not forensics_engine or not authenticity_scorer:
            raise HTTPException(503, "Scoring engine not available.")

        forensic_report = forensics_engine.analyze(file_bytes, content_type)
        auth_report     = authenticity_scorer.score(
            forensic_report,
            blockchain_verified=blockchain_verified,
            exact_hash_match=exact_hash_match,
        )

        return JSONResponse({
            "status":  "scored",
            "file_name": file.filename,
            "content_type": content_type,
            "authenticity_report": auth_report.to_dict(),
        })

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(500, f"Scoring failed: {str(e)}")


# ═════════════════════════════════════════════════════════════
#  JOURNAL AUTHX: CONTRIBUTION 3 — CROSS-MODAL VERIFICATION
# ═════════════════════════════════════════════════════════════

@app.post("/cross-modal-verify")
async def cross_modal_verify(
    video:   Optional[UploadFile] = File(None),
    audio:   Optional[UploadFile] = File(None),
    image:   Optional[UploadFile] = File(None),
    text:    Optional[UploadFile] = File(None),
):
    """
    Cross-modal consistency verification.

    Upload any combination of video, audio, image, text files.
    The engine checks all applicable modality pairs for inconsistencies:

    - video ↔ audio  (AV sync, noise floor, energy envelope)
    - audio ↔ text   (speaking rate, vocabulary complexity, pause/paragraph match)
    - image ↔ text   (colour description, brightness, complexity)
    - video ↔ text   (motion vs action verbs, scene vs paragraph count)

    Returns ConsistencyViolations with severity, description, and evidence.
    """
    try:
        if not cross_modal_verifier:
            raise HTTPException(503, "Cross-modal verifier not available.")

        files: Dict = {}
        if video:
            b = await video.read()
            files["video"] = (b, video.content_type or "video/mp4")
        if audio:
            b = await audio.read()
            files["audio"] = (b, audio.content_type or "audio/wav")
        if image:
            b = await image.read()
            files["image"] = (b, image.content_type or "image/jpeg")
        if text:
            b = await text.read()
            files["text"] = (b, text.content_type or "text/plain")

        if len(files) < 2:
            raise HTTPException(422, "At least two files from different modalities are required.")

        report = cross_modal_verifier.verify(files)

        return JSONResponse({
            "status": "verified",
            "modalities_checked": list(files.keys()),
            "cross_modal_report": report.to_dict(),
        })

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(500, f"Cross-modal verification failed: {str(e)}")


# ═════════════════════════════════════════════════════════════
#  ENHANCED /register  (backward-compatible + new columns)
# ═════════════════════════════════════════════════════════════

@app.post("/register")
async def register_content(
    owner_name:    str = Form(...),
    owner_address: str = Form(""),
    content_type:  str = Form(...),
    description:   str = Form(""),
    ai_tool:       str = Form(""),
    file: UploadFile   = File(...),
):
    """
    Register content with multi-layer verification.

    Now additionally:
    - Runs full forensic analysis and stores localization map
    - Computes and stores Authenticity Score + Trust Score
    - Stores risk level on-chain fingerprint
    """
    try:
        file_bytes = await file.read()
        actual_ct  = file.content_type or content_type
        print(f"[Register] {actual_ct}, {len(file_bytes)} bytes")

        sha256_hash = compute_sha256(file_bytes)
        hashes      = compute_multi_hashes(file_bytes, actual_ct)

        conn   = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Layer 1: exact duplicate
        cursor.execute("SELECT id, owner_name FROM content_registry WHERE sha256 = ?", (sha256_hash,))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return JSONResponse({
                "status": "already_registered",
                "message": f"Content already registered by {existing[1]}",
                "existing_record": {"id": existing[0], "owner": existing[1]},
            }, status_code=409)

        # ── Journal AuthX forensic analysis ──────────────────
        forensic_report  = None
        auth_report_dict = {}
        loc_json         = "[]"
        artifacts_str    = ""
        auth_score       = None
        trust_score_val  = None
        risk_level       = None

        if forensics_engine and authenticity_scorer:
            try:
                forensic_report = forensics_engine.analyze(file_bytes, actual_ct)
                auth_report     = authenticity_scorer.score(
                    forensic_report,
                    blockchain_verified=False,  # Not yet registered
                    exact_hash_match=False,
                )
                auth_report_dict = auth_report.to_dict()
                auth_score      = auth_report.authenticity_score
                trust_score_val = auth_report.trust_score
                risk_level      = auth_report.risk_level
                loc_json        = json.dumps([r.to_dict() for r in forensic_report.localization])
                artifacts_str   = ",".join(forensic_report.artifacts)
                print(f"[Forensics] Auth={auth_score:.1f} Trust={trust_score_val:.1f} Risk={risk_level}")
            except Exception as e:
                print(f"[Forensics] Non-fatal error: {e}")

        # Legacy AI detection (kept for backward compat)
        tampering_result = {"tamper_probability": 0.0, "confidence": 0.0, "detected_artifacts": []}
        has_tampering    = False
        try:
            if ai_detector:
                tampering_result = ai_detector.analyze(file_bytes, actual_ct)
                has_tampering    = tampering_result.get("tamper_probability", 0) > 0.3
        except Exception as e:
            print(f"[Legacy AI] Non-fatal: {e}")

        # Layer 2: similarity check
        content_modality = actual_ct.split('/')[0]
        if content_modality == "image":
            q = "SELECT id,owner_name,owner_address,registered_at,phash,dhash,ahash,tamper_score,content_type FROM content_registry WHERE content_type LIKE 'image%'"
        elif content_modality == "audio":
            q = "SELECT id,owner_name,owner_address,registered_at,phash,dhash,ahash,tamper_score,content_type,audio_fingerprint FROM content_registry WHERE content_type LIKE 'audio%'"
        elif content_modality == "video":
            q = "SELECT id,owner_name,owner_address,registered_at,phash,dhash,ahash,tamper_score,content_type,video_fingerprint FROM content_registry WHERE content_type LIKE 'video%'"
        else:
            q = "SELECT id,owner_name,owner_address,registered_at,phash,dhash,ahash,tamper_score,content_type,text_fingerprint FROM content_registry WHERE content_type LIKE 'text%' OR content_type LIKE '%pdf%'"

        cursor.execute(q)
        MAX_DISTANCE = get_threshold(actual_ct, has_tampering)

        for row in cursor.fetchall():
            stored = {
                "phash": row[4] if len(row) > 4 else None,
                "dhash": row[5] if len(row) > 5 else None,
                "ahash": row[6] if len(row) > 6 else None,
                "audio_fingerprint": row[9] if len(row) > 9 and content_modality == "audio" else None,
                "video_fingerprint": row[9] if len(row) > 9 and content_modality == "video" else None,
                "text_fingerprint":  row[9] if len(row) > 9 and content_modality not in ("image", "audio", "video") else None,
            }
            sim      = calculate_multi_similarity(hashes, stored, actual_ct)
            print(f"[Similarity] min_distance={sim['min_distance']} threshold={MAX_DISTANCE} best={sim['best_match_type']}")
            min_dist = sim["min_distance"]

            if min_dist <= MAX_DISTANCE:
                sim_pct  = max(0, round((1 - min_dist / 64) * 100))
                conn.close()
                ct_name = actual_ct.split('/')[0].title()
                verdict  = "🚫 AI-modified" if has_tampering else "⚠️ Similar"
                msg      = (f"{verdict} {ct_name.lower()} detected! "
                             f"Similar to content registered by {row[1]}")
                return JSONResponse({
                    "status": "similar_content_exists",
                    "message": msg,
                    "similarity": f"{sim_pct}%",
                    "hash_distance": min_dist,
                    "ai_tampering_detected": has_tampering,
                    "tampering_score": round(tampering_result.get("tamper_probability", 0), 3),
                    "authenticity_report": auth_report_dict,
                    "original_record": {
                        "id": row[0], "owner_name": row[1],
                        "owner_address": row[2], "registered_at": row[3],
                    },
                }, status_code=409)

        # Layer 3: block extremely high tampering
        if tampering_result.get("tamper_probability", 0) > 0.8:
            conn.close()
            return JSONResponse({
                "status": "high_tampering_detected",
                "message": "⚠️ Content shows signs of heavy AI modification.",
                "tampering_analysis": tampering_result,
                "authenticity_report": auth_report_dict,
            }, status_code=400)

        # Save file
        ext       = Path(file.filename).suffix
        file_path = UPLOAD_DIR / f"{sha256_hash}{ext}"
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Blockchain
        try:
            bc_result = blockchain_manager.register(sha256_hash, owner_name, actual_ct)
        except Exception as e:
            print(f"[Blockchain] Non-fatal: {e}")
            bc_result = {"tx_hash": None, "block_number": None}

        # Insert with new columns
        try:
            cursor.execute("""
                INSERT INTO content_registry
                (owner_name, owner_address, content_type, description, ai_tool,
                 sha256, phash, dhash, ahash, audio_fingerprint, video_fingerprint,
                 text_fingerprint, file_path, tx_hash, block_number,
                 tamper_score, tamper_confidence, detected_artifacts,
                 authenticity_score, trust_score, risk_level,
                 forensic_localization, forensic_artifacts)
                VALUES (?,?,?,?,?, ?,?,?,?,?,?,?,?,?,?, ?,?,?, ?,?,?,?,?)
            """, (
                owner_name, owner_address, actual_ct, description, ai_tool,
                sha256_hash, hashes["phash"], hashes["dhash"], hashes["ahash"],
                hashes["audio_fingerprint"], hashes["video_fingerprint"],
                hashes["text_fingerprint"], str(file_path),
                bc_result.get("tx_hash"), bc_result.get("block_number"),
                tampering_result.get("tamper_probability", 0.0),
                tampering_result.get("confidence", 0.0),
                ",".join(tampering_result.get("detected_artifacts", [])),
                auth_score, trust_score_val, risk_level,
                loc_json, artifacts_str,
            ))
            content_id = cursor.lastrowid
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(500, f"Database error: {str(e)}")
        finally:
            conn.close()

        return JSONResponse({
            "status": "ok",
            "message": "Content registered successfully.",
            "proof": {
                "id":           content_id,
                "sha256":       sha256_hash,
                "tx_hash":      bc_result.get("tx_hash"),
                "block_number": bc_result.get("block_number"),
                "proof_url":    f"http://127.0.0.1:8000/proof/{content_id}",
            },
            "authenticity_report": auth_report_dict,
            "legacy_tampering": tampering_result,
        })

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(500, f"Registration failed: {str(e)}")


# ═════════════════════════════════════════════════════════════
#  ENHANCED /verify
# ═════════════════════════════════════════════════════════════

@app.post("/verify")
async def verify_content(file: UploadFile = File(...)):
    """
    Verify content authenticity.

    Now returns unified Authenticity + Trust Score alongside traditional
    similarity/hash matching. If a match is found, blockchain_verified=True
    is passed to the scorer for a more accurate authenticity score.
    """
    try:
        file_bytes   = await file.read()
        content_type = file.content_type or "application/octet-stream"

        sha256_hash  = compute_sha256(file_bytes)
        hashes       = compute_multi_hashes(file_bytes, content_type)

        conn   = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Layer 1: exact match
        cursor.execute("""
            SELECT id, owner_name, owner_address, registered_at, tx_hash,
                   tamper_score, content_type, authenticity_score, trust_score, risk_level
            FROM content_registry WHERE sha256 = ?
        """, (sha256_hash,))
        exact = cursor.fetchone()

        # Full forensic analysis regardless of match
        forensic_report = None
        auth_report_dict = {}
        if forensics_engine and authenticity_scorer:
            try:
                forensic_report = forensics_engine.analyze(file_bytes, content_type)
                auth_report     = authenticity_scorer.score(
                    forensic_report,
                    blockchain_verified=bool(exact),
                    exact_hash_match=bool(exact),
                )
                auth_report_dict = auth_report.to_dict()
            except Exception as e:
                print(f"[Verify Forensics] {e}")

        if exact:
            conn.close()
            return JSONResponse({
                "result":    "exact_match",
                "confidence": 1.0,
                "verification_type": "sha256_exact",
                "match_details": {
                    "id":            exact[0],
                    "owner_name":    exact[1],
                    "owner_address": exact[2],
                    "registered_at": exact[3],
                    "tx_hash":       exact[4],
                    "content_type":  exact[6],
                },
                "authenticity_report": auth_report_dict,
                "message": "✅ Exact match — Content is authentic original.",
            })

        # Layer 2: similarity search
        cursor.execute("""
            SELECT id, owner_name, owner_address, registered_at, tx_hash,
                   phash, dhash, ahash, tamper_score, content_type,
                   audio_fingerprint, video_fingerprint, text_fingerprint
            FROM content_registry
        """)

        best_match = None
        best_dist  = float('inf')

        for row in cursor.fetchall():
            if content_type.split('/')[0] != row[9].split('/')[0]:
                continue
            stored = {
                "phash": row[5], "dhash": row[6], "ahash": row[7],
                "audio_fingerprint": row[10],
                "video_fingerprint": row[11],
                "text_fingerprint":  row[12],
            }
            sim = calculate_multi_similarity(hashes, stored, content_type)
            vt = 28 if content_type.startswith("video") else (
    38 if ("text" in content_type or "pdf" in content_type) else 35
)
            if sim["min_distance"] <= vt and sim["min_distance"] < best_dist:
                best_dist  = sim["min_distance"]
                best_match = {
                    "id":            row[0],
                    "owner_name":    row[1],
                    "owner_address": row[2],
                    "registered_at": row[3],
                    "tx_hash":       row[4],
                    "hash_distance": sim["min_distance"],
                    "match_type":    sim["best_match_type"],
                    "content_type":  row[9],
                }

        # Legacy AI detection
        tampering_result = {}
        try:
            if ai_detector:
                tampering_result = ai_detector.analyze(file_bytes, content_type)
        except Exception: pass

        conn.close()

        if best_match:
            conf         = max(0.0, 1.0 - (best_match["hash_distance"] / 64.0))
            is_tampered  = tampering_result.get("tamper_probability", 0) > 0.3
            return JSONResponse({
                "result":            "near_duplicate",
                "confidence":        conf,
                "verification_type": f"similarity_{best_match['match_type']}",
                "match_details":     best_match,
                "tampering_analysis": tampering_result,
                "potential_theft":   is_tampered,
                "authenticity_report": auth_report_dict,
                "message": (
                    f"⚠️ Similar content found — AI modification detected. "
                    f"Original by {best_match['owner_name']}"
                    if is_tampered else
                    f"ℹ️ Near-duplicate found. Original by {best_match['owner_name']}"
                ),
            })

        return JSONResponse({
            "result":            "not_found",
            "confidence":        0.0,
            "tampering_analysis": tampering_result,
            "authenticity_report": auth_report_dict,
            "message": "❌ Content not found in database.",
            "suggestions": [
                "This content may be original and not yet registered.",
                "Try registering it to establish ownership.",
            ],
        })

    except Exception as e:
        raise HTTPException(500, str(e))


# ═════════════════════════════════════════════════════════════
#  ENHANCED /proof/{content_id}
# ═════════════════════════════════════════════════════════════

@app.get("/proof/{content_id}")
async def get_proof(content_id: int):
    """
    Retrieve full forensic evidence certificate.

    Now includes:
    - Authenticity Score + Trust Score + Risk Level
    - Tampering localization map (JSON)
    - Forensic artifacts list
    """
    try:
        conn   = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, owner_name, owner_address, content_type, description,
                   ai_tool, sha256, phash, registered_at, tx_hash, block_number,
                   tamper_score, tamper_confidence, detected_artifacts,
                   authenticity_score, trust_score, risk_level,
                   forensic_localization, forensic_artifacts
            FROM content_registry WHERE id = ?
        """, (content_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(404, "Proof not found.")

        loc_map = []
        try:
            if row[17]:
                loc_map = json.loads(row[17])
        except Exception:
            pass

        return JSONResponse({
            "id":            row[0],
            "owner_name":    row[1],
            "owner_address": row[2],
            "content_type":  row[3],
            "description":   row[4],
            "ai_tool":       row[5],
            "sha256":        row[6],
            "phash":         row[7],
            "registered_at": row[8],
            "tx_hash":       row[9],
            "block_number":  row[10],
            # Legacy tampering
            "tampering_analysis": {
                "tamper_probability": row[11] or 0.0,
                "confidence":        row[12] or 0.0,
                "detected_artifacts": (row[13] or "").split(",") if row[13] else [],
            },
            # Journal AuthX unified scores
            "authenticity_score":  row[14],
            "trust_score":         row[15],
            "risk_level":          row[16],
            "forensic_localization": loc_map,
            "forensic_artifacts":  (row[18] or "").split(",") if row[18] else [],
            "verification_url":    "http://127.0.0.1:8000/verify",
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ═════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ═════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    return {
        "status":  "healthy",
        "version": "2.0.0 (Journal AuthX)",
        "services": {
            "blockchain":          blockchain_manager  is not None,
            "ai_detector_legacy":  ai_detector         is not None,
            "multimodal_forensics": forensics_engine   is not None,
            "authenticity_scorer": authenticity_scorer is not None,
            "cross_modal_verifier": cross_modal_verifier is not None,
        },
        "endpoints": {
            "analyze":              "POST /analyze",
            "authenticity_score":   "POST /authenticity-score",
            "cross_modal_verify":   "POST /cross-modal-verify",
            "register":             "POST /register",
            "verify":               "POST /verify",
            "proof":                "GET  /proof/{id}",
        },
    }


# ═════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  Journal AuthX Backend  —  v2.0.0")
    print("=" * 60)
    print("  http://127.0.0.1:8000")
    print("  http://127.0.0.1:8000/docs")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")