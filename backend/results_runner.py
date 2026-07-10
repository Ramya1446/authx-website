"""
results_runner.py
==================
Generates Tables 1-4 for the AuthX journal paper by running real test
cases against your live backend (must be running on http://127.0.0.1:8000).

SETUP — before running:
------------------------
Create this folder structure next to this script:

dataset/
  image/
    originals/        <- put 15-20+ original images here
    trimmed/           <- crop/resize versions of the SAME originals
    ai_modified/        <- AI-filtered/generated versions
  video/
    originals/
    trimmed/
    ai_modified/        <- Runway/Pika/CapCut-AI-effect versions
  text/
    originals/          <- PDFs or .txt files
    trimmed/            <- minor edits, paraphrased
    ai_modified/        <- ChatGPT full rewrites

IMPORTANT: trimmed/ and ai_modified/ files should share a base filename
with their original, e.g.:
  originals/photo1.jpg  ->  trimmed/photo1.jpg  ->  ai_modified/photo1.jpg
This script matches them by filename stem.

Run:
    pip install requests --break-system-packages
    python results_runner.py
"""

import requests
import time
import csv
import os
from pathlib import Path
from collections import defaultdict

BASE_URL = "http://127.0.0.1:8000"
DATASET_DIR = Path("dataset")
OUTPUT_DIR = Path("results")
OUTPUT_DIR.mkdir(exist_ok=True)

MODALITIES = ["image", "video", "text"]
CONTENT_TYPE_MAP = {
    "image": "image",
    "video": "video",
    "text": "text",
}

MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".mp4": "video/mp4", ".mov": "video/quicktime",
    ".pdf": "application/pdf", ".txt": "text/plain",
}


def guess_mime(path: Path) -> str:
    return MIME_MAP.get(path.suffix.lower(), "application/octet-stream")


def register(path: Path, owner="TestRunner") -> dict:
    """POST /register and return the parsed JSON + timing."""
    with open(path, "rb") as f:
        files = {"file": (path.name, f, guess_mime(path))}
        data = {
            "owner_name": owner,
            "owner_address": "",
            "content_type": CONTENT_TYPE_MAP.get(path.parent.parent.name, "text"),
            "description": "",
            "ai_tool": "",
        }
        t0 = time.time()
        try:
            r = requests.post(f"{BASE_URL}/register", files=files, data=data, timeout=120)
            elapsed = time.time() - t0
            return {"status_code": r.status_code, "json": r.json(), "time": elapsed}
        except Exception as e:
            return {"status_code": 0, "json": {"status": "error", "message": str(e)}, "time": 0}


def verify(path: Path) -> dict:
    """POST /verify and return the parsed JSON + timing."""
    with open(path, "rb") as f:
        files = {"file": (path.name, f, guess_mime(path))}
        t0 = time.time()
        try:
            r = requests.post(f"{BASE_URL}/verify", files=files, timeout=120)
            elapsed = time.time() - t0
            return {"status_code": r.status_code, "json": r.json(), "time": elapsed}
        except Exception as e:
            return {"status_code": 0, "json": {"result": "error", "message": str(e)}, "time": 0}


def list_files(folder: Path):
    if not folder.exists():
        return []
    return sorted([p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")])


# ════════════════════════════════════════════════════════════
#  TABLE 1 — Ownership Verification Accuracy
# ════════════════════════════════════════════════════════════
def run_table1():
    print("\n" + "=" * 60)
    print("TABLE 1 — Ownership Verification")
    print("=" * 60)

    rows = []
    for modality in MODALITIES:
        originals = list_files(DATASET_DIR / modality / "originals")
        if not originals:
            print(f"  [{modality}] no originals found, skipping")
            rows.append({"content_type": modality, "accuracy": "N/A", "n": 0})
            continue

        correct = 0
        total = 0

        for path in originals:
            # Step 1: register (should succeed first time)
            reg = register(path)
            total += 1
            if reg["json"].get("status") == "ok":
                correct += 1
            print(f"  [{modality}] register {path.name}: {reg['json'].get('status')}")

            # Step 2: verify the SAME file (should return exact_match)
            ver = verify(path)
            total += 1
            if ver["json"].get("result") == "exact_match":
                correct += 1
            print(f"  [{modality}] verify {path.name}: {ver['json'].get('result')}")

        accuracy = round(100 * correct / total, 2) if total else 0
        rows.append({"content_type": modality, "accuracy": accuracy, "n": total})
        print(f"  >> {modality}: {accuracy}% ({correct}/{total})")

    with open(OUTPUT_DIR / "table1_ownership_verification.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["content_type", "accuracy", "n"])
        w.writeheader()
        w.writerows(rows)

    return rows


# ════════════════════════════════════════════════════════════
#  TABLE 2 — Tampering Detection (Precision / Recall / F1)
# ════════════════════════════════════════════════════════════
def run_table2():
    print("\n" + "=" * 60)
    print("TABLE 2 — Tampering Detection")
    print("=" * 60)

    rows = []
    for modality in MODALITIES:
        originals   = {p.stem: p for p in list_files(DATASET_DIR / modality / "originals")}
        ai_modified = {p.stem: p for p in list_files(DATASET_DIR / modality / "ai_modified")}

        if not originals or not ai_modified:
            print(f"  [{modality}] missing originals or ai_modified, skipping")
            rows.append({"content_type": modality, "precision": "N/A", "recall": "N/A", "f1": "N/A"})
            continue

        tp = fp = fn = tn = 0

        # Positive cases: AI-modified files. Should be flagged as tampered.
        for stem, path in ai_modified.items():
            ver = verify(path)
            tampering = ver["json"].get("tampering_analysis", {})
            prob = tampering.get("tamper_probability", 0)
            flagged = prob > 0.3 or ver["json"].get("potential_theft", False)
            if flagged:
                tp += 1
            else:
                fn += 1
            print(f"  [{modality}] AI-modified {path.name}: prob={prob:.2f} flagged={flagged}")

        # Negative cases: originals. Should NOT be flagged as tampered
        # (use a fresh copy not yet registered, or check /analyze directly)
        for stem, path in originals.items():
            with open(path, "rb") as fobj:
                files = {"file": (path.name, fobj, guess_mime(path))}
                try:
                    r = requests.post(f"{BASE_URL}/analyze", files=files, timeout=60)
                    report = r.json().get("forensic_report", {})
                    prob = report.get("tamper_probability", 0)
                except Exception:
                    prob = 0
            flagged = prob > 0.3
            if flagged:
                fp += 1
            else:
                tn += 1
            print(f"  [{modality}] original {path.name}: prob={prob:.2f} flagged={flagged}")

        precision = round(tp / (tp + fp), 4) if (tp + fp) else 0
        recall    = round(tp / (tp + fn), 4) if (tp + fn) else 0
        f1        = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) else 0

        rows.append({
            "content_type": modality,
            "precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        })
        print(f"  >> {modality}: P={precision} R={recall} F1={f1}  (TP={tp} FP={fp} FN={fn} TN={tn})")

    with open(OUTPUT_DIR / "table2_tampering_detection.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["content_type", "precision", "recall", "f1", "tp", "fp", "fn", "tn"])
        w.writeheader()
        w.writerows(rows)

    return rows


# ════════════════════════════════════════════════════════════
#  TABLE 3 — Deepfake / AI-Generation Detection Accuracy
# ════════════════════════════════════════════════════════════
def run_table3():
    print("\n" + "=" * 60)
    print("TABLE 3 — Deepfake Detection")
    print("=" * 60)

    rows = []
    label_map = {
        "video": "Video Deepfake",
        "text":  "AI Text",
    }

    for modality in ["video", "text"]:
        ai_modified = list_files(DATASET_DIR / modality / "ai_modified")
        if not ai_modified:
            rows.append({"content_type": label_map[modality], "accuracy": "N/A", "n": 0})
            continue

        correct = 0
        for path in ai_modified:
            with open(path, "rb") as fobj:
                files = {"file": (path.name, fobj, guess_mime(path))}
                try:
                    r = requests.post(f"{BASE_URL}/analyze", files=files, timeout=60)
                    report = r.json().get("forensic_report", {})
                    prob = report.get("tamper_probability", 0)
                    artifacts = report.get("artifacts", [])
                except Exception:
                    prob, artifacts = 0, []

            deepfake_signals = [
                "tts_voice_clone_signature", "face_region_deepfake",
                "unnatural_optical_flow", "gan_frequency_signature",
                "ai_generated_sentences", "ai_transition_phrase_overuse",
            ]
            detected = prob > 0.4 or any(a in artifacts for a in deepfake_signals)
            if detected:
                correct += 1
            print(f"  [{modality}] {path.name}: prob={prob:.2f} detected={detected}")

        accuracy = round(100 * correct / len(ai_modified), 2)
        rows.append({"content_type": label_map[modality], "accuracy": accuracy, "n": len(ai_modified)})
        print(f"  >> {label_map[modality]}: {accuracy}% ({correct}/{len(ai_modified)})")

    with open(OUTPUT_DIR / "table3_deepfake_detection.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["content_type", "accuracy", "n"])
        w.writeheader()
        w.writerows(rows)

    return rows


# ════════════════════════════════════════════════════════════
#  TABLE 4 — Blockchain Performance
# ════════════════════════════════════════════════════════════
def run_table4():
    print("\n" + "=" * 60)
    print("TABLE 4 — Blockchain Performance")
    print("=" * 60)

    reg_times = []
    ver_times = []

    # Use whatever files are available across modalities, up to 15 total
    sample_files = []
    for modality in MODALITIES:
        sample_files.extend(list_files(DATASET_DIR / modality / "originals")[:4])

    for path in sample_files:
        reg = register(path, owner=f"PerfTest_{path.stem}")
        reg_times.append(reg["time"])
        ver = verify(path)
        ver_times.append(ver["time"])
        print(f"  {path.name}: register={reg['time']:.2f}s verify={ver['time']:.2f}s")

    avg_reg = round(sum(reg_times) / len(reg_times), 3) if reg_times else 0
    avg_ver = round(sum(ver_times) / len(ver_times), 3) if ver_times else 0

    rows = [
        {"metric": "Registration Time (avg, s)", "value": avg_reg},
        {"metric": "Verification Time (avg, s)",  "value": avg_ver},
        {"metric": "Gas Cost",                    "value": "See Ganache gasUsed field per tx (check blockchain.py logs)"},
        {"metric": "Storage Cost",                "value": "SQLite local — no per-record fee; on-chain stores only hash+metadata"},
    ]

    with open(OUTPUT_DIR / "table4_blockchain_performance.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(rows)

    print(f"  >> avg registration: {avg_reg}s | avg verification: {avg_ver}s")
    return rows


# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("AuthX Journal Results Runner")
    print(f"Backend: {BASE_URL}")
    print(f"Dataset: {DATASET_DIR.resolve()}")

    # Health check
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Backend health: {r.json().get('status')}")
    except Exception as e:
        print(f"ERROR: cannot reach backend at {BASE_URL} — {e}")
        print("Make sure uvicorn is running first.")
        exit(1)

    t1 = run_table1()
    t2 = run_table2()
    t3 = run_table3()
    t4 = run_table4()

    print("\n" + "=" * 60)
    print("DONE — CSVs written to ./results/")
    print("=" * 60)
    print("table1_ownership_verification.csv")
    print("table2_tampering_detection.csv")
    print("table3_deepfake_detection.csv")
    print("table4_blockchain_performance.csv")
    print("\nTable 5 (comparison with existing methods) is NOT generated")
    print("here — it's drawn from your literature survey, not test runs.")
    print("Use the checkmarks already in your conference paper Table II.")