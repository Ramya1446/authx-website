"""
multimodal_forensics.py — Journal AuthX Contribution 1
=======================================================
Complete Multimodal Forensics with Tampering Localization.

Modules
-------
ImageForensics   — pixel-level localization (ELA, gradient maps, noise residuals)
AudioForensics   — segment-level localization (spectrogram anomalies, splicing detection)
VideoForensics   — frame-level localization (temporal inconsistencies, face-region anomalies)
TextForensics    — sentence-level localization (AI-generated sentence detection, style shifts)

Each module returns a standardized ForensicReport with:
  - tamper_probability   : float [0, 1]
  - confidence           : float [0, 1]
  - localization         : list of TamperRegion (where exactly the tampering was found)
  - artifacts            : list[str] (what was found)
  - analysis_details     : dict (per-method scores)
  - modality             : str
"""

from __future__ import annotations

import io
import os
import re
import math
import wave
import struct
import tempfile
import hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

import numpy as np
from PIL import Image
import cv2


# ─────────────────────────────────────────────────────────────
#  DATA STRUCTURES
# ─────────────────────────────────────────────────────────────

@dataclass
class TamperRegion:
    """Describes a localised area of suspected tampering."""
    region_type: str          # "spatial", "temporal", "spectral", "textual"
    description: str          # human-readable
    severity: float           # 0–1
    location: Dict[str, Any]  # modality-specific coords / indices

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ForensicReport:
    modality: str
    tamper_probability: float
    confidence: float
    artifacts: List[str] = field(default_factory=list)
    localization: List[TamperRegion] = field(default_factory=list)
    analysis_details: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "modality": self.modality,
            "tamper_probability": round(self.tamper_probability, 4),
            "confidence": round(self.confidence, 4),
            "artifacts": self.artifacts,
            "localization": [r.to_dict() for r in self.localization],
            "analysis_details": {k: round(v, 4) for k, v in self.analysis_details.items()},
        }


# ─────────────────────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────────────────────

def _safe(fn, default=0.0):
    try:
        return fn()
    except Exception:
        return default


# ═════════════════════════════════════════════════════════════
#  1.  IMAGE FORENSICS
# ═════════════════════════════════════════════════════════════

class ImageForensics:
    """
    Pixel-level tampering localization for images.

    Methods
    -------
    ela          — Error Level Analysis (JPEG re-compression artifacts)
    noise_map    — Noise residual inconsistency map
    gradient_map — Edge gradient anomaly detection
    copy_move    — Block-matching copy-move forgery detection
    """

    PATCH = 32  # spatial patch size

    def analyze(self, file_bytes: bytes) -> ForensicReport:
        try:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            arr = np.array(img)
        except Exception as e:
            return ForensicReport("image", 0.0, 0.0, [f"load_error:{e}"])

        scores: Dict[str, float] = {}
        regions: List[TamperRegion] = []
        artifacts: List[str] = []

        # ── ELA ──────────────────────────────────────────────
        ela_score, ela_regions = self._ela(file_bytes, arr)
        scores["ela"] = ela_score
        regions.extend(ela_regions)
        if ela_score > 0.5:
            artifacts.append("ela_inconsistency")

        # ── Noise map ────────────────────────────────────────
        noise_score, noise_regions = self._noise_map(arr)
        scores["noise_map"] = noise_score
        regions.extend(noise_regions)
        if noise_score > 0.5:
            artifacts.append("noise_pattern_mismatch")

        # ── Gradient map ─────────────────────────────────────
        grad_score, grad_regions = self._gradient_map(arr)
        scores["gradient_map"] = grad_score
        regions.extend(grad_regions)
        if grad_score > 0.5:
            artifacts.append("gradient_boundary_artifact")

        # ── Copy-move ────────────────────────────────────────
        cm_score, cm_regions = self._copy_move(arr)
        scores["copy_move"] = cm_score
        regions.extend(cm_regions)
        if cm_score > 0.4:
            artifacts.append("copy_move_region_detected")

        # ── GAN frequency check ──────────────────────────────
        gan_score = self._gan_frequency(arr)
        scores["gan_frequency"] = gan_score
        if gan_score > 0.5:
            artifacts.append("gan_frequency_signature")

        tamper_prob = (
            scores["ela"]           * 0.30 +
            scores["noise_map"]     * 0.20 +
            scores["gradient_map"]  * 0.15 +
            scores["copy_move"]     * 0.20 +
            scores["gan_frequency"] * 0.15
        )
        confidence = self._confidence(scores)

        return ForensicReport(
            modality="image",
            tamper_probability=float(min(tamper_prob, 1.0)),
            confidence=float(confidence),
            artifacts=artifacts,
            localization=regions,
            analysis_details=scores,
        )

    # ── ELA ──────────────────────────────────────────────────
    def _ela(self, file_bytes: bytes, arr: np.ndarray):
        try:
            orig = Image.fromarray(arr)
            buf = io.BytesIO()
            orig.save(buf, format="JPEG", quality=75)
            buf.seek(0)
            recomp = np.array(Image.open(buf).convert("RGB"))

            diff = np.abs(arr.astype(np.float32) - recomp.astype(np.float32))
            ela_map = diff.mean(axis=2)          # H × W
            global_mean = ela_map.mean()
            global_std  = ela_map.std()

            regions = []
            h, w = ela_map.shape
            patch = self.PATCH
            anomaly_patches = []

            for y in range(0, h - patch, patch):
                for x in range(0, w - patch, patch):
                    block = ela_map[y:y+patch, x:x+patch]
                    bm = block.mean()
                    if bm > global_mean + 2.5 * global_std:
                        anomaly_patches.append((x, y, float(bm)))

            if anomaly_patches:
                top = sorted(anomaly_patches, key=lambda t: -t[2])[:5]
                for ax, ay, sev in top:
                    regions.append(TamperRegion(
                        region_type="spatial",
                        description="ELA high-error region — possible splicing or inpainting",
                        severity=min(sev / (global_mean + global_std * 3 + 1e-6), 1.0),
                        location={"x": ax, "y": ay, "w": patch, "h": patch},
                    ))

            score = min(len(anomaly_patches) / max(1, (h // patch) * (w // patch)) * 6, 1.0)
            return float(score), regions
        except Exception:
            return 0.0, []

    # ── Noise map ────────────────────────────────────────────
    def _noise_map(self, arr: np.ndarray):
        try:
            gray    = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY).astype(np.float32)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            residual = np.abs(gray - blurred)

            h, w = residual.shape
            patch = self.PATCH
            means = []

            for y in range(0, h - patch, patch):
                for x in range(0, w - patch, patch):
                    means.append(residual[y:y+patch, x:x+patch].mean())

            if not means:
                return 0.0, []

            gm = np.mean(means)
            gs = np.std(means)
            regions = []

            for i, (y, x) in enumerate(
                [(y, x) for y in range(0, h - patch, patch) for x in range(0, w - patch, patch)]
            ):
                if i >= len(means):
                    break
                if means[i] > gm + 2.5 * gs or means[i] < gm - 2.5 * gs:
                    regions.append(TamperRegion(
                        region_type="spatial",
                        description="Noise floor inconsistency — possible compositing boundary",
                        severity=min(abs(means[i] - gm) / (gs + 1e-6) / 4, 1.0),
                        location={"x": x, "y": y, "w": patch, "h": patch},
                    ))

            score = min(len(regions) / max(1, len(means)) * 4, 1.0)
            return float(score), regions[:5]
        except Exception:
            return 0.0, []

    # ── Gradient map ─────────────────────────────────────────
    def _gradient_map(self, arr: np.ndarray):
        try:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            mag = np.sqrt(sx**2 + sy**2)

            h, w = mag.shape
            patch = self.PATCH
            regions = []
            vals = []

            for y in range(0, h - patch, patch):
                for x in range(0, w - patch, patch):
                    vals.append(mag[y:y+patch, x:x+patch].mean())

            if not vals:
                return 0.0, []

            gm, gs = np.mean(vals), np.std(vals)

            for i, (y, x) in enumerate(
                [(y, x) for y in range(0, h - patch, patch) for x in range(0, w - patch, patch)]
            ):
                if i >= len(vals):
                    break
                if vals[i] > gm + 4 * gs:   # Raised to 4 sigma
                    regions.append(TamperRegion(
                        region_type="spatial",
                        description="Abrupt gradient boundary — possible splice edge",
                        severity=min((vals[i] - gm) / (gs + 1e-6) / 5, 1.0),
                        location={"x": x, "y": y, "w": patch, "h": patch},
                    ))

            score = min(len(regions) / max(1, len(vals)) * 5, 1.0)
            return float(score), regions[:5]
        except Exception:
            return 0.0, []

    # ── Copy-move ────────────────────────────────────────────
    def _copy_move(self, arr: np.ndarray):
        try:
            gray  = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            small = cv2.resize(gray, (128, 128))
            patch = 16
            h, w  = small.shape
            blocks: Dict[bytes, list] = {}

            for y in range(0, h - patch, patch):
                for x in range(0, w - patch, patch):
                    blk = small[y:y+patch, x:x+patch]
                    key = hashlib.md5(blk.tobytes()).digest()
                    blocks.setdefault(key, []).append((x, y))

            duplicates = [(locs, key) for key, locs in blocks.items() if len(locs) > 1]
            regions = []

            for locs, _ in duplicates[:3]:
                sx_c = int(locs[0][0] * arr.shape[1] / 128)
                sy_c = int(locs[0][1] * arr.shape[0] / 128)
                regions.append(TamperRegion(
                    region_type="spatial",
                    description="Copy-move duplicate region detected",
                    severity=min(len(locs) / 5, 1.0),
                    location={"x": sx_c, "y": sy_c, "w": patch * 4, "h": patch * 4,
                               "duplicate_count": len(locs)},
                ))

            score = min(len(duplicates) / 10, 1.0)
            return float(score), regions
        except Exception:
            return 0.0, []

    # ── GAN frequency signature ───────────────────────────────
    def _gan_frequency(self, arr: np.ndarray) -> float:
        try:
            gray    = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            resized = cv2.resize(gray, (256, 256))
            dct     = cv2.dct(np.float32(resized))
            hi_energy = np.sum(np.abs(dct[128:, 128:]))
            total     = np.sum(np.abs(dct)) + 1e-10
            ratio = hi_energy / total
            if ratio < 0.06: return 0.9
            if ratio < 0.10: return 0.6
            if ratio < 0.13: return 0.3
            return 0.0
        except Exception:
            return 0.0

    def _confidence(self, scores: dict) -> float:
        vals = list(scores.values())
        std  = np.std(vals)
        if std < 0.15: return 0.90
        if std < 0.25: return 0.75
        if std < 0.35: return 0.60
        return 0.45


# ═════════════════════════════════════════════════════════════
#  2.  AUDIO FORENSICS
# ═════════════════════════════════════════════════════════════

class AudioForensics:
    """
    Segment-level tampering localization for audio.

    Methods
    -------
    spectral_splice   — Detect abrupt spectral changes (edit points)
    noise_consistency — Noise floor consistency across segments
    phase_continuity  — Phase discontinuity at splice boundaries
    deepfake_band     — Frequency band signature of TTS/voice-cloner
    """

    SEGMENT_SECS = 0.5   # segment length for analysis

    def analyze(self, file_bytes: bytes) -> ForensicReport:
        audio, sr = self._load(file_bytes)
        if audio is None:
            return ForensicReport("audio", 0.0, 0.3, ["wav_parse_failed"])

        scores: Dict[str, float] = {}
        regions: List[TamperRegion] = []
        artifacts: List[str] = []

        splice_score, splice_regions = self._spectral_splice(audio, sr)
        scores["spectral_splice"] = splice_score
        regions.extend(splice_regions)
        if splice_score > 0.4:
            artifacts.append("audio_splice_detected")

        noise_score, noise_regions = self._noise_consistency(audio, sr)
        scores["noise_consistency"] = noise_score
        regions.extend(noise_regions)
        if noise_score > 0.4:
            artifacts.append("noise_floor_inconsistency")

        phase_score, phase_regions = self._phase_continuity(audio, sr)
        scores["phase_continuity"] = phase_score
        regions.extend(phase_regions)
        if phase_score > 0.4:
            artifacts.append("phase_discontinuity")

        deepfake_score = self._deepfake_band(audio, sr)
        scores["deepfake_band"] = deepfake_score
        if deepfake_score > 0.5:
            artifacts.append("tts_voice_clone_signature")

        dynamic_score = self._dynamic_range(audio)
        scores["dynamic_range"] = dynamic_score
        if dynamic_score > 0.5:
            artifacts.append("low_dynamic_range")

        tamper_prob = (
            scores["spectral_splice"]   * 0.30 +
            scores["noise_consistency"] * 0.25 +
            scores["phase_continuity"]  * 0.20 +
            scores["deepfake_band"]     * 0.15 +
            scores["dynamic_range"]     * 0.10
        )
        confidence = self._confidence(scores)

        return ForensicReport(
            modality="audio",
            tamper_probability=float(min(tamper_prob, 1.0)),
            confidence=float(confidence),
            artifacts=artifacts,
            localization=regions,
            analysis_details=scores,
        )

    def _load(self, file_bytes: bytes):
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(file_bytes)
                path = f.name
            try:
                with wave.open(path, "rb") as wf:
                    raw = wf.readframes(wf.getnframes())
                    sr  = wf.getframerate()
                    sw  = wf.getsampwidth()
                dtype = {1: np.uint8, 2: np.int16, 4: np.int32}.get(sw, np.int16)
                audio = np.frombuffer(raw, dtype=dtype).astype(np.float32)
                peak  = np.max(np.abs(audio)) + 1e-9
                return audio / peak, sr
            finally:
                os.unlink(path)
        except Exception:
            return None, None

    def _spectral_splice(self, audio: np.ndarray, sr: int):
        """Detect abrupt spectral centroid jumps between segments."""
        try:
            seg = int(sr * self.SEGMENT_SECS)
            centroids = []
            times = []

            for i in range(0, len(audio) - seg, seg):
                chunk = audio[i:i+seg]
                fft   = np.abs(np.fft.rfft(chunk)) + 1e-9
                freqs = np.fft.rfftfreq(len(chunk), 1 / sr)
                c     = np.sum(freqs * fft) / np.sum(fft)
                centroids.append(c)
                times.append(i / sr)

            if len(centroids) < 3:
                return 0.0, []

            c_arr = np.array(centroids)
            diffs = np.abs(np.diff(c_arr))
            mean_d, std_d = diffs.mean(), diffs.std()
            regions = []

            for i, d in enumerate(diffs):
                if d > mean_d + 2.5 * std_d:
                    t = times[i + 1]
                    regions.append(TamperRegion(
                        region_type="temporal",
                        description=f"Spectral centroid jump at {t:.2f}s — probable splice point",
                        severity=min((d - mean_d) / (std_d + 1e-6) / 4, 1.0),
                        location={"time_sec": round(t, 3), "delta_hz": round(float(d), 1)},
                    ))

            score = min(len(regions) / max(1, len(centroids)) * 5, 1.0)
            return float(score), regions[:6]
        except Exception:
            return 0.0, []

    def _noise_consistency(self, audio: np.ndarray, sr: int):
        """Inconsistent noise floor between segments."""
        try:
            seg  = int(sr * self.SEGMENT_SECS)
            rms_vals = []
            times    = []

            for i in range(0, len(audio) - seg, seg):
                chunk = audio[i:i+seg]
                rms   = np.sqrt(np.mean(chunk**2))
                rms_vals.append(rms)
                times.append(i / sr)

            if len(rms_vals) < 3:
                return 0.0, []

            rms_arr = np.array(rms_vals)
            # Focus on quiet segments only
            quiet_thresh = np.percentile(rms_arr, 25)
            quiet_idxs   = np.where(rms_arr < quiet_thresh * 2)[0]

            if len(quiet_idxs) < 2:
                return 0.0, []

            quiet_rms = rms_arr[quiet_idxs]
            std_q = quiet_rms.std()
            mean_q = quiet_rms.mean()
            regions = []

            for idx in quiet_idxs:
                if abs(rms_arr[idx] - mean_q) > 2.5 * std_q:
                    regions.append(TamperRegion(
                        region_type="temporal",
                        description=f"Noise floor shift at {times[idx]:.2f}s — possible edit",
                        severity=min(abs(rms_arr[idx] - mean_q) / (mean_q + 1e-9), 1.0),
                        location={"time_sec": round(times[idx], 3)},
                    ))

            score = min(std_q / (mean_q + 1e-9) * 3, 1.0)
            return float(score), regions[:4]
        except Exception:
            return 0.0, []

    def _phase_continuity(self, audio: np.ndarray, sr: int):
        """Phase discontinuity at segment boundaries."""
        try:
            seg  = int(sr * 0.1)   # 100 ms windows
            phases = []
            times  = []

            for i in range(0, len(audio) - seg, seg):
                chunk = audio[i:i+seg]
                fft   = np.fft.rfft(chunk)
                dominant = np.argmax(np.abs(fft))
                phase = np.angle(fft[dominant])
                phases.append(phase)
                times.append(i / sr)

            if len(phases) < 4:
                return 0.0, []

            diffs = np.abs(np.diff(phases))
            # Wrap to [0, π]
            diffs = np.where(diffs > np.pi, 2 * np.pi - diffs, diffs)

            mean_d, std_d = diffs.mean(), diffs.std()
            regions = []

            for i, d in enumerate(diffs):
                if d > mean_d + 3 * std_d and d > np.pi * 0.7:
                    regions.append(TamperRegion(
                        region_type="temporal",
                        description=f"Phase discontinuity at {times[i]:.2f}s",
                        severity=float(d / np.pi),
                        location={"time_sec": round(times[i], 3), "phase_jump_rad": round(float(d), 3)},
                    ))

            score = min(len(regions) / max(len(phases), 1) * 8, 1.0)
            return float(score), regions[:5]
        except Exception:
            return 0.0, []

    def _deepfake_band(self, audio: np.ndarray, sr: int) -> float:
        """TTS / voice-cloner frequency band signature."""
        try:
            fft  = np.abs(np.fft.rfft(audio)) + 1e-9
            freq = np.fft.rfftfreq(len(audio), 1 / sr)

            def band(lo, hi):
                m = (freq >= lo) & (freq < hi)
                return np.sum(fft[m]**2)

            total = band(20, min(sr // 2, 20000)) + 1e-12
            ratios = {
                "presence": band(8000, min(sr // 2, 20000)) / total,
                "mid":      band(300, 3000) / total,
                "sub_bass": band(20, 80) / total,
            }

            score = 0.0
            if ratios["presence"] < 0.01: score += 0.5  # TTS cuts off here
            if ratios["mid"] > 0.92:      score += 0.3
            if ratios["sub_bass"] < 0.001: score += 0.2
            return min(score, 1.0)
        except Exception:
            return 0.0

    def _dynamic_range(self, audio: np.ndarray) -> float:
        try:
            chunk = 4096
            rms = [np.sqrt(np.mean(audio[i:i+chunk]**2))
                   for i in range(0, len(audio) - chunk, chunk)]
            if not rms: return 0.0
            rms = np.array(rms)
            crest = np.max(np.abs(audio)) / (np.max(rms) + 1e-9)
            dr    = np.max(rms) / (np.min(rms) + 1e-9)
            score = 0.0
            if crest < 2.0: score += 0.5
            if dr < 2.0:    score += 0.4
            return min(score, 1.0)
        except Exception:
            return 0.0

    def _confidence(self, scores: dict) -> float:
        std = np.std(list(scores.values()))
        if std < 0.15: return 0.85
        if std < 0.25: return 0.70
        if std < 0.35: return 0.55
        return 0.40


# ═════════════════════════════════════════════════════════════
#  3.  VIDEO FORENSICS
# ═════════════════════════════════════════════════════════════

class VideoForensics:
    """
    Frame-level tampering localization for video.

    Methods
    -------
    temporal_consistency — Inter-frame difference anomalies
    face_region_anomaly  — Face region deepfake signature
    compression_ghost    — Double-compression artifact detection
    scene_cut_analysis   — Unnatural scene cuts / loop detection
    """

    def analyze(self, file_bytes: bytes) -> ForensicReport:
        frames, fps, meta = self._extract_frames(file_bytes)
        if not frames:
            return ForensicReport("video", 0.0, 0.2, ["frame_extraction_failed"])

        scores: Dict[str, float] = {}
        regions: List[TamperRegion] = []
        artifacts: List[str] = []

        temp_score, temp_regions = self._temporal_consistency(frames, fps)
        scores["temporal_consistency"] = temp_score
        regions.extend(temp_regions)
        if temp_score > 0.4: artifacts.append("temporal_inconsistency")

        face_score, face_regions = self._face_region_anomaly(frames, fps)
        scores["face_anomaly"] = face_score
        regions.extend(face_regions)
        if face_score > 0.4: artifacts.append("face_region_deepfake")

        compress_score = self._compression_ghost(frames)
        scores["compression_ghost"] = compress_score
        if compress_score > 0.5: artifacts.append("double_compression")

        loop_score, loop_regions = self._loop_detection(frames, fps)
        scores["loop_detection"] = loop_score
        regions.extend(loop_regions)
        if loop_score > 0.5: artifacts.append("video_loop_detected")

        tamper_prob = (
            scores["temporal_consistency"] * 0.30 +
            scores["face_anomaly"]         * 0.35 +
            scores["compression_ghost"]    * 0.20 +
            scores["loop_detection"]       * 0.15
        )
        confidence = self._confidence(scores)

        return ForensicReport(
            modality="video",
            tamper_probability=float(min(tamper_prob, 1.0)),
            confidence=float(confidence),
            artifacts=artifacts,
            localization=regions,
            analysis_details=scores,
        )

    def _extract_frames(self, file_bytes: bytes):
        tmp = None
        cap = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(file_bytes)
                tmp = f.name

            cap = cv2.VideoCapture(tmp)
            if not cap.isOpened():
                return [], 25.0, {}

            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps   = cap.get(cv2.CAP_PROP_FPS) or 25.0
            meta  = {"total_frames": total, "fps": fps,
                     "width":  int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                     "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}

            n_samples = min(32, max(8, total // 10))
            idxs = [int(i * total / n_samples) for i in range(n_samples)]
            frames = []

            for idx in idxs:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    frames.append((idx, frame))

            return frames, fps, meta
        except Exception:
            return [], 25.0, {}
        finally:
            if cap: cap.release()
            if tmp and os.path.exists(tmp):
                try: os.unlink(tmp)
                except Exception: pass

    def _temporal_consistency(self, frames, fps):
        try:
            grays = [(idx, cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)) for idx, f in frames]
            diffs = []

            for i in range(1, len(grays)):
                d = np.mean(np.abs(
                    grays[i][1].astype(np.float32) - grays[i-1][1].astype(np.float32)
                ))
                diffs.append((grays[i][0], d))

            if not diffs:
                return 0.0, []

            d_vals = [d for _, d in diffs]
            mean_d, std_d = np.mean(d_vals), np.std(d_vals)
            regions = []

            for frame_idx, d in diffs:
                t = frame_idx / fps
                if d < 0.3:      # Nearly static
                    regions.append(TamperRegion(
                        region_type="temporal",
                        description=f"Near-static frame at {t:.2f}s — possible loop/freeze",
                        severity=0.7,
                        location={"frame": frame_idx, "time_sec": round(t, 3), "diff": round(float(d), 4)},
                    ))
                elif d > mean_d + 3 * std_d:
                    regions.append(TamperRegion(
                        region_type="temporal",
                        description=f"Abrupt scene change at {t:.2f}s — possible splice",
                        severity=min((d - mean_d) / (std_d + 1e-6) / 5, 1.0),
                        location={"frame": frame_idx, "time_sec": round(t, 3), "diff": round(float(d), 2)},
                    ))

            if std_d < 1.0 and mean_d < 1.0:
                score = 0.8
            elif std_d < 2.0:
                score = 0.4
            else:
                score = min(len(regions) / max(len(diffs), 1) * 3, 1.0)

            return float(score), regions[:6]
        except Exception:
            return 0.0, []

    def _face_region_anomaly(self, frames, fps):
        """Use OpenCV face detector to find face regions and check for deepfake signatures."""
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            face_scores = []
            regions = []

            for frame_idx, frame in frames:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(50, 50))

                for (x, y, w, h) in faces:
                    face_roi = frame[y:y+h, x:x+w]
                    if face_roi.size == 0:
                        continue

                    # Check frequency signature of face region
                    face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                    resized   = cv2.resize(face_gray, (64, 64))
                    dct       = cv2.dct(np.float32(resized))
                    hi_energy = np.sum(np.abs(dct[32:, 32:]))
                    total     = np.sum(np.abs(dct)) + 1e-10
                    ratio     = hi_energy / total

                    # Check noise pattern in face
                    blur = cv2.GaussianBlur(face_gray, (5, 5), 0)
                    noise_std = np.std(face_gray.astype(np.float32) - blur.astype(np.float32))

                    deepfake_score = 0.0
                    if ratio < 0.02:      deepfake_score += 0.5   # Extremely smooth (GAN)
                    if noise_std < 0.3:   deepfake_score += 0.4   # Near-zero noise (synthetic)

                    face_scores.append(deepfake_score)

                    if deepfake_score > 0.6:   # Raised threshold — less false positives
                        t = frame_idx / fps
                        regions.append(TamperRegion(
                            region_type="spatial",
                            description=f"Face region deepfake signature at frame {frame_idx} ({t:.2f}s)",
                            severity=deepfake_score,
                            location={"frame": frame_idx, "time_sec": round(t, 3),
                                       "face_box": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}},
                        ))

            if not face_scores:
                return 0.0, []

            return float(np.mean(face_scores)), regions[:6]
        except Exception:
            return 0.0, []

    def _compression_ghost(self, frames) -> float:
        """Double-compression artifact: compare JPEG quality levels of sampled frames."""
        try:
            scores = []
            for _, frame in frames[:8]:
                buf1 = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])[1].tobytes()
                buf2 = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tobytes()

                arr1 = np.frombuffer(buf1, dtype=np.uint8)
                arr2 = np.frombuffer(buf2, dtype=np.uint8)

                min_len = min(len(arr1), len(arr2))
                diff = np.abs(arr1[:min_len].astype(np.float32) - arr2[:min_len].astype(np.float32))
                scores.append(diff.mean())

            if not scores:
                return 0.0

            mean_s = np.mean(scores)
            # Very low diff = already heavily compressed (double compression)
            if mean_s < 5.0:  return 0.7
            if mean_s < 10.0: return 0.4
            return 0.0
        except Exception:
            return 0.0

    def _loop_detection(self, frames, fps):
        """Detect repeated frame sequences (AI video loops)."""
        try:
            if len(frames) < 6:
                return 0.0, []

            hashes = []
            for idx, frame in frames:
                small = cv2.resize(
                    cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (16, 16)
                )
                h = int(np.mean(small > small.mean()))
                hashes.append((idx, small.tobytes()))

            # Check for near-duplicate frames far apart in time
            regions = []
            seen: Dict[bytes, int] = {}

            for idx, h in hashes:
                if h in seen:
                    t1 = seen[h] / fps
                    t2 = idx / fps
                    if t2 - t1 > 1.0:   # At least 1 second apart
                        regions.append(TamperRegion(
                            region_type="temporal",
                            description=f"Repeated frame pattern at {t2:.2f}s (matches {t1:.2f}s)",
                            severity=0.8,
                            location={"time_sec": round(t2, 3), "original_time_sec": round(t1, 3)},
                        ))
                else:
                    seen[h] = idx

            score = min(len(regions) / max(len(frames) // 4, 1), 1.0)
            return float(score), regions[:4]
        except Exception:
            return 0.0, []

    def _confidence(self, scores: dict) -> float:
        std = np.std(list(scores.values()))
        if std < 0.15: return 0.85
        if std < 0.25: return 0.70
        return 0.55


# ═════════════════════════════════════════════════════════════
#  4.  TEXT FORENSICS
# ═════════════════════════════════════════════════════════════

class TextForensics:
    """
    Sentence-level tampering localization for text documents.

    Methods
    -------
    sentence_anomaly     — Per-sentence AI-generation score
    style_shift_detector — Detect writing style changes mid-document
    perplexity_proxy     — Sentence-length burstiness (human proxy)
    vocabulary_shift     — Vocabulary density shifts
    """

    def analyze(self, file_bytes: bytes) -> ForensicReport:
        text = self._decode(file_bytes)
        if not text or len(text.strip()) < 50:
            return ForensicReport("text", 0.0, 0.2, ["text_too_short"])

        sentences = self._split_sentences(text)
        if len(sentences) < 3:
            return ForensicReport("text", 0.0, 0.3, ["too_few_sentences"])

        scores: Dict[str, float] = {}
        regions: List[TamperRegion] = []
        artifacts: List[str] = []

        sent_score, sent_regions = self._sentence_anomaly(sentences)
        scores["sentence_anomaly"] = sent_score
        regions.extend(sent_regions)
        if sent_score > 0.4: artifacts.append("ai_generated_sentences")

        style_score, style_regions = self._style_shift(sentences)
        scores["style_shift"] = style_score
        regions.extend(style_regions)
        if style_score > 0.4: artifacts.append("writing_style_shift")

        burst_score = self._burstiness(sentences)
        scores["burstiness"] = burst_score
        if burst_score > 0.5: artifacts.append("low_text_burstiness")

        vocab_score, vocab_regions = self._vocabulary_shift(sentences)
        scores["vocabulary_shift"] = vocab_score
        regions.extend(vocab_regions)
        if vocab_score > 0.4: artifacts.append("vocabulary_density_shift")

        ngram_score = self._ngram_repetition(text)
        scores["ngram_repetition"] = ngram_score
        if ngram_score > 0.5: artifacts.append("high_phrase_repetition")

        tamper_prob = (
            scores["sentence_anomaly"]   * 0.30 +
            scores["style_shift"]        * 0.25 +
            scores["burstiness"]         * 0.20 +
            scores["vocabulary_shift"]   * 0.15 +
            scores["ngram_repetition"]   * 0.10
        )
        confidence = self._confidence(scores)

        return ForensicReport(
            modality="text",
            tamper_probability=float(min(tamper_prob, 1.0)),
            confidence=float(confidence),
            artifacts=artifacts,
            localization=regions,
            analysis_details=scores,
        )

    def _decode(self, file_bytes: bytes) -> str:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                text = file_bytes.decode(enc, errors="ignore")
                text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]', ' ', text)
                return re.sub(r'\s+', ' ', text).strip()
            except Exception:
                continue
        return ""

    def _split_sentences(self, text: str) -> List[str]:
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text)
                if len(s.split()) >= 3]

    def _sentence_anomaly(self, sentences: List[str]):
        """Score each sentence for AI-generation signals."""
        try:
            scores = []
            regions = []

            for i, sent in enumerate(sentences):
                words = sent.lower().split()
                if not words:
                    scores.append(0.0)
                    continue

                score = 0.0

                # AI filler phrases
                ai_fillers = [
                    "it is important to note", "it is worth noting",
                    "in conclusion", "furthermore", "moreover",
                    "it should be noted", "notably", "in summary",
                    "to summarize", "as mentioned", "as stated",
                    "delve into", "it is crucial", "in the realm of",
                ]
                text_lower = sent.lower()
                filler_hits = sum(1 for f in ai_fillers if f in text_lower)
                score += min(filler_hits * 0.25, 0.5)

                # Unnaturally long sentences
                if len(words) > 40:
                    score += 0.3
                elif len(words) > 30:
                    score += 0.15

                # Suspiciously balanced punctuation
                if sent.count(",") > len(words) // 6:
                    score += 0.2

                score = min(score, 1.0)
                scores.append(score)

                if score > 0.4:
                    regions.append(TamperRegion(
                        region_type="textual",
                        description=f"Sentence {i+1} shows AI-generation signals",
                        severity=score,
                        location={"sentence_index": i, "preview": sent[:80]},
                    ))

            mean_score = float(np.mean(scores)) if scores else 0.0
            return mean_score, regions[:8]
        except Exception:
            return 0.0, []

    def _style_shift(self, sentences: List[str]):
        """Detect shifts in average word length (proxy for vocabulary level)."""
        try:
            if len(sentences) < 4:
                return 0.0, []

            def avg_word_len(sent):
                words = re.findall(r'\b\w+\b', sent)
                return np.mean([len(w) for w in words]) if words else 0.0

            awl = [avg_word_len(s) for s in sentences]
            half = len(awl) // 2
            mu1, mu2 = np.mean(awl[:half]), np.mean(awl[half:])
            std1, std2 = np.std(awl[:half]), np.std(awl[half:])

            shift = abs(mu2 - mu1)
            regions = []

            if shift > 1.2:    # Noticeable vocabulary shift
                mid = len(sentences) // 2
                regions.append(TamperRegion(
                    region_type="textual",
                    description=f"Writing style shift detected around sentence {mid}: avg word length changed by {shift:.2f} chars",
                    severity=min(shift / 3, 1.0),
                    location={"sentence_index": mid, "avg_word_len_before": round(float(mu1), 2),
                               "avg_word_len_after": round(float(mu2), 2)},
                ))

            score = min(shift / 3, 1.0)
            return float(score), regions
        except Exception:
            return 0.0, []

    def _burstiness(self, sentences: List[str]) -> float:
        try:
            lengths = [len(s.split()) for s in sentences]
            if len(lengths) < 4: return 0.0
            cv = np.std(lengths) / (np.mean(lengths) + 1e-6)
            if cv < 0.20: return 0.8
            if cv < 0.35: return 0.5
            if cv < 0.50: return 0.2
            return 0.0
        except Exception:
            return 0.0

    def _vocabulary_shift(self, sentences: List[str]):
        """TTR (type-token ratio) per half."""
        try:
            if len(sentences) < 4:
                return 0.0, []

            def ttr(sents):
                words = re.findall(r'\b[a-z]{2,}\b', " ".join(sents).lower())
                return len(set(words)) / max(len(words), 1)

            half = len(sentences) // 2
            t1 = ttr(sentences[:half])
            t2 = ttr(sentences[half:])
            diff = abs(t1 - t2)

            regions = []
            if diff > 0.15:
                mid = half
                regions.append(TamperRegion(
                    region_type="textual",
                    description=f"Vocabulary density shift at sentence {mid}: TTR {t1:.2f}→{t2:.2f}",
                    severity=min(diff * 3, 1.0),
                    location={"sentence_index": mid, "ttr_before": round(t1, 3), "ttr_after": round(t2, 3)},
                ))

            return float(min(diff * 3, 1.0)), regions
        except Exception:
            return 0.0, []

    def _ngram_repetition(self, text: str) -> float:
        try:
            words = re.findall(r'\b\w+\b', text.lower())
            if len(words) < 20: return 0.0
            n = 4
            ngrams = [tuple(words[i:i+n]) for i in range(len(words) - n + 1)]
            ratio = 1.0 - len(set(ngrams)) / max(len(ngrams), 1)
            if ratio > 0.40: return 0.8
            if ratio > 0.25: return 0.5
            if ratio > 0.15: return 0.2
            return 0.0
        except Exception:
            return 0.0

    def _confidence(self, scores: dict) -> float:
        std = np.std(list(scores.values()))
        if std < 0.15: return 0.85
        if std < 0.25: return 0.70
        return 0.55


# ═════════════════════════════════════════════════════════════
#  UNIFIED DISPATCHER
# ═════════════════════════════════════════════════════════════

class MultimodalForensics:
    """Single entry point for all modality forensic analysis."""

    def __init__(self):
        self.image = ImageForensics()
        self.audio = AudioForensics()
        self.video = VideoForensics()
        self.text  = TextForensics()

    def analyze(self, file_bytes: bytes, content_type: str) -> ForensicReport:
        ct = content_type.lower()
        if ct.startswith("image"):
            return self.image.analyze(file_bytes)
        elif ct.startswith("audio"):
            return self.audio.analyze(file_bytes)
        elif ct.startswith("video"):
            return self.video.analyze(file_bytes)
        elif ct.startswith("text") or "pdf" in ct or "document" in ct:
            return self.text.analyze(file_bytes)
        else:
            return ForensicReport("unknown", 0.05, 0.5, ["unsupported_modality"])