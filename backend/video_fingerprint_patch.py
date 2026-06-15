"""
video_fingerprint_patch.py  -  drop this file into your backend/ folder.
"""

import cv2
import numpy as np
import tempfile
import os
from typing import Optional, List


def compute_video_fingerprint(file_bytes: bytes) -> Optional[str]:
    tmp_path = None
    cap = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            print("[Video FP] Could not open video - using fallback")
            return _fallback_video_fingerprint(file_bytes)

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[Video FP] total_frames={total_frames} fps={fps} size={width}x{height}")

        if total_frames <= 0:
            print("[Video FP] No frames detected - using fallback")
            return _fallback_video_fingerprint(file_bytes)

        # Sample more frames to survive partial zero-frame dropout
        n_samples = min(48, max(16, total_frames // 8))
        sample_idxs = [int(i * total_frames / n_samples) for i in range(n_samples)]

        frame_hashes: List[int] = []
        zero_count = 0

        for idx in sample_idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            h = _phash_frame(frame)
            if h == 0:
                zero_count += 1
                continue
            frame_hashes.append(h)

        print(f"[Video FP] Got {len(frame_hashes)} valid hashes, {zero_count} zero hashes skipped")

        if len(frame_hashes) < 4:
            print("[Video FP] Too few valid frames - codec issue, using fallback")
            return _fallback_video_fingerprint(file_bytes)

        fp = "|".join(f"{h:016x}" for h in frame_hashes)
        return fp

    except Exception as e:
        print(f"[Video FP] Error: {e}")
        return _fallback_video_fingerprint(file_bytes)
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def _phash_frame(frame_bgr: np.ndarray) -> int:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(np.float32(resized))
    dct_low = dct[:8, :8]
    mean_val = np.mean(dct_low[1:])
    bits = (dct_low.flatten() > mean_val).astype(np.uint8)
    result = 0
    for b in bits:
        result = (result << 1) | int(b)
    return result


def _fallback_video_fingerprint(file_bytes: bytes) -> Optional[str]:
    import hashlib
    parts = []
    size = len(file_bytes)
    if size < 1024:
        return None
    for frac in [0.0, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95]:
        start = int(frac * size)
        chunk = file_bytes[start: start + 512]
        parts.append(hashlib.md5(chunk).hexdigest()[:8])
    return "fallback|" + "|".join(parts)


def compare_video_fingerprints(fp_new: str, fp_stored: str) -> int:
    """
    Compare two video fingerprints -> integer distance in [0, 64].
    Uses two strategies and picks the best (lowest distance):
      1. Sliding window  - good for simple trims (same codec, contiguous cut)
      2. Best-N matching - good for re-encoded trims (different resolution/codec)
    Threshold guidance: flag if dist <= 30 (clean) or <= 32 (tampered)
    """
    if not fp_new or not fp_stored:
        return 64

    if fp_new.startswith("fallback|") or fp_stored.startswith("fallback|"):
        if fp_new.startswith("fallback|") != fp_stored.startswith("fallback|"):
            return 64
        matches = sum(c1 == c2 for c1, c2 in zip(fp_new, fp_stored))
        sim = matches / max(len(fp_new), len(fp_stored), 1)
        return int((1.0 - sim) * 64)

    hashes_new = [h for h in _parse_frame_hashes(fp_new) if h != 0]
    hashes_stored = [h for h in _parse_frame_hashes(fp_stored) if h != 0]

    print(f"[Video Compare] new={len(hashes_new)} frames, stored={len(hashes_stored)} frames")

    if not hashes_new or not hashes_stored:
        return 64

    dist_window = _sliding_window_best_match(hashes_new, hashes_stored)
    dist_cross = _best_n_cross_match(hashes_new, hashes_stored)

    result = int(round(min(dist_window, dist_cross)))
    print(f"[Video Compare] window={dist_window:.2f} cross={dist_cross:.2f} -> final={result}")
    return result


def _parse_frame_hashes(fp: str) -> List[int]:
    try:
        return [int(h, 16) for h in fp.split("|") if h and len(h) == 16]
    except Exception:
        return []


def _hamming64(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def _sliding_window_best_match(hashes_a: List[int], hashes_b: List[int]) -> float:
    if len(hashes_a) <= len(hashes_b):
        shorter, longer = hashes_a, hashes_b
    else:
        shorter, longer = hashes_b, hashes_a

    n = len(shorter)
    if n == 0:
        return 64.0

    best = 64.0
    for offset in range(len(longer) - n + 1):
        window = longer[offset: offset + n]
        avg = sum(_hamming64(a, b) for a, b in zip(shorter, window)) / n
        if avg < best:
            best = avg
            if best < 1.0:
                break
    return best


def _best_n_cross_match(hashes_a: List[int], hashes_b: List[int]) -> float:
    """
    For each frame in the shorter list, find its best matching frame anywhere
    in the longer list. Average the top 50% of those matches.

    Handles re-encoded trims where frame timestamps shift (different fps,
    resolution change) so a contiguous window won't align cleanly.
    """
    if len(hashes_a) <= len(hashes_b):
        shorter, longer = hashes_a, hashes_b
    else:
        shorter, longer = hashes_b, hashes_a

    if not shorter or not longer:
        return 64.0

    best_matches = []
    for h in shorter:
        min_dist = min(_hamming64(h, candidate) for candidate in longer)
        best_matches.append(min_dist)

    # Average only the best 50% - robust against genuinely different scenes
    best_matches.sort()
    top_half = best_matches[:max(1, len(best_matches) // 2)]
    return sum(top_half) / len(top_half)