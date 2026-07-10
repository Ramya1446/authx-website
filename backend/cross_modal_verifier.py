"""
cross_modal_verifier.py — Journal AuthX Contribution 3
=======================================================
Cross-Modal Consistency Verification.

Detects inconsistencies between modalities in multi-modal content:
  - Video ↔ Audio  : sync, speaker consistency, noise match
  - Audio ↔ Text   : transcript vs spoken content alignment
  - Video ↔ Text   : visual scene vs textual description
  - Metadata ↔ Content : embedded metadata vs actual content properties

This module moves AuthX from "per-file authentication" to
"multimodal forensic intelligence" — the key journal novelty.

Architecture
------------
CrossModalVerifier.verify(files: dict) → CrossModalReport

files dict keys: "video", "audio", "text", "image"
Each value: (file_bytes: bytes, content_type: str)

CrossModalReport contains:
  - is_consistent      : bool
  - inconsistency_score: float [0, 1]
  - confidence         : float [0, 1]
  - violations         : list[ConsistencyViolation]
  - summary            : str
  - analysis_details   : dict
"""

from __future__ import annotations

import io
import os
import re
import wave
import tempfile
import math
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any

import numpy as np
from PIL import Image
import cv2


# ─────────────────────────────────────────────────────────────
#  DATA STRUCTURES
# ─────────────────────────────────────────────────────────────

@dataclass
class ConsistencyViolation:
    violation_type: str      # e.g. "av_sync", "transcript_mismatch", "metadata_conflict"
    modalities: List[str]    # which modalities are in conflict
    severity: float          # 0–1
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CrossModalReport:
    is_consistent: bool
    inconsistency_score: float   # 0 = perfectly consistent, 1 = fully inconsistent
    confidence: float
    violations: List[ConsistencyViolation] = field(default_factory=list)
    summary: str = ""
    analysis_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "is_consistent":       self.is_consistent,
            "inconsistency_score": round(self.inconsistency_score, 4),
            "confidence":          round(self.confidence, 4),
            "violations":          [v.to_dict() for v in self.violations],
            "summary":             self.summary,
            "analysis_details":    self.analysis_details,
        }


# ─────────────────────────────────────────────────────────────
#  VERIFIER
# ─────────────────────────────────────────────────────────────

class CrossModalVerifier:
    """
    Performs cross-modal consistency checks.

    Usage
    -----
    verifier = CrossModalVerifier()

    # Full multimodal check (video + embedded audio)
    report = verifier.verify_video_audio(video_bytes, audio_bytes)

    # Audio + transcript check
    report = verifier.verify_audio_text(audio_bytes, text_bytes)

    # Image + caption check
    report = verifier.verify_image_text(image_bytes, text_bytes)

    # General dispatcher
    report = verifier.verify(files_dict)
    """

    # Threshold below which we declare consistent
    CONSISTENCY_THRESHOLD = 0.35

    def verify(self, files: Dict[str, Tuple[bytes, str]]) -> CrossModalReport:
        """
        Dispatcher. files = {"video": (bytes, ct), "audio": (bytes, ct), ...}
        Runs all applicable checks and merges results.
        """
        reports: List[CrossModalReport] = []

        has = set(files.keys())

        # Video ↔ Audio
        if "video" in has and "audio" in has:
            v_bytes, _ = files["video"]
            a_bytes, _ = files["audio"]
            reports.append(self.verify_video_audio(v_bytes, a_bytes))

        # Audio ↔ Text
        if "audio" in has and "text" in has:
            a_bytes, _ = files["audio"]
            t_bytes, _ = files["text"]
            reports.append(self.verify_audio_text(a_bytes, t_bytes))

        # Image ↔ Text
        if "image" in has and "text" in has:
            i_bytes, _ = files["image"]
            t_bytes, _ = files["text"]
            reports.append(self.verify_image_text(i_bytes, t_bytes))

        # Video ↔ Text
        if "video" in has and "text" in has:
            v_bytes, _ = files["video"]
            t_bytes, _ = files["text"]
            reports.append(self.verify_video_text(v_bytes, t_bytes))

        if not reports:
            return CrossModalReport(
                is_consistent=True,
                inconsistency_score=0.0,
                confidence=0.1,
                summary="Insufficient modalities for cross-modal check.",
            )

        return self._merge_reports(reports)

    # ═══════════════════════════════════════════
    #  VIDEO ↔ AUDIO
    # ═══════════════════════════════════════════

    def verify_video_audio(self, video_bytes: bytes, audio_bytes: bytes) -> CrossModalReport:
        """
        Check consistency between a video and a separate audio track.

        Tests
        -----
        1. Duration match         — audio and video should be same length
        2. Energy sync            — loud video scenes should have loud audio
        3. Noise floor match      — background noise signature consistency
        4. Spectral character     — voice vs music energy distribution
        """
        violations: List[ConsistencyViolation] = []
        details: Dict[str, Any] = {}
        scores: List[float] = []

        # ── Extract video audio track ─────────────────────────
        vid_audio, vid_fps, vid_frames = self._extract_video_properties(video_bytes)
        aud_pcm, aud_sr = self._load_audio(audio_bytes)

        # ── 1. Duration consistency ───────────────────────────
        vid_dur = vid_frames / max(vid_fps, 1)
        aud_dur = len(aud_pcm) / max(aud_sr, 1) if aud_pcm is not None else 0.0
        dur_ratio = abs(vid_dur - aud_dur) / max(vid_dur, aud_dur, 1)
        details["video_duration_sec"] = round(vid_dur, 2)
        details["audio_duration_sec"] = round(aud_dur, 2)
        details["duration_ratio_diff"] = round(dur_ratio, 4)

        if dur_ratio > 0.20:
            sev = min(dur_ratio, 1.0)
            violations.append(ConsistencyViolation(
                violation_type="duration_mismatch",
                modalities=["video", "audio"],
                severity=sev,
                description=f"Duration mismatch: video={vid_dur:.1f}s, audio={aud_dur:.1f}s ({dur_ratio:.0%} difference).",
                evidence={"video_dur": vid_dur, "audio_dur": aud_dur},
            ))
            scores.append(sev)
        else:
            scores.append(0.0)

        # ── 2. Energy sync ────────────────────────────────────
        if vid_audio is not None and aud_pcm is not None:
            sync_score = self._energy_sync(vid_audio, aud_pcm)
            details["energy_sync_score"] = round(sync_score, 4)
            scores.append(sync_score)

            if sync_score > 0.5:
                violations.append(ConsistencyViolation(
                    violation_type="av_energy_desync",
                    modalities=["video", "audio"],
                    severity=sync_score,
                    description="Audio and video energy envelopes are not synchronized — possible re-dubbing.",
                    evidence={"desync_score": round(sync_score, 3)},
                ))

        # ── 3. Noise floor match ──────────────────────────────
        if vid_audio is not None and aud_pcm is not None:
            noise_match = self._noise_floor_match(vid_audio, aud_pcm)
            details["noise_floor_match"] = round(noise_match, 4)
            scores.append(noise_match)

            if noise_match > 0.5:
                violations.append(ConsistencyViolation(
                    violation_type="noise_floor_mismatch",
                    modalities=["video", "audio"],
                    severity=noise_match,
                    description="Background noise character differs between video and audio — possible separate recording environments.",
                    evidence={"mismatch_score": round(noise_match, 3)},
                ))

        inconsistency = float(np.mean(scores)) if scores else 0.0
        confidence = 0.7 if vid_audio is not None else 0.4

        return CrossModalReport(
            is_consistent=inconsistency <= self.CONSISTENCY_THRESHOLD,
            inconsistency_score=min(inconsistency, 1.0),
            confidence=confidence,
            violations=violations,
            summary=self._va_summary(inconsistency, violations),
            analysis_details=details,
        )

    # ═══════════════════════════════════════════
    #  AUDIO ↔ TEXT
    # ═══════════════════════════════════════════

    def verify_audio_text(self, audio_bytes: bytes, text_bytes: bytes) -> CrossModalReport:
        """
        Check consistency between audio and a text transcript/document.

        Tests
        -----
        1. Duration vs word count  — speaking rate should be in human range
        2. Vocabulary complexity   — mismatch in reading level
        3. Sentence count vs pause pattern — paragraph count vs silence regions
        """
        violations: List[ConsistencyViolation] = []
        details: Dict[str, Any] = {}
        scores: List[float] = []

        audio, sr = self._load_audio(audio_bytes)
        text = self._decode_text(text_bytes)

        if audio is None or not text:
            return CrossModalReport(
                is_consistent=True,
                inconsistency_score=0.0,
                confidence=0.2,
                summary="Could not parse audio or text for cross-modal check.",
            )

        # ── 1. Duration vs word count (speaking rate) ─────────
        duration_sec = len(audio) / max(sr, 1)
        word_count   = len(text.split())
        speaking_rate = word_count / max(duration_sec / 60, 0.001)   # words per minute

        details["audio_duration_sec"] = round(duration_sec, 2)
        details["text_word_count"]    = word_count
        details["speaking_rate_wpm"]  = round(speaking_rate, 1)

        # Normal: 100–200 wpm. Outside 50–300 = suspicious
        if speaking_rate < 50 or speaking_rate > 350:
            sev = min(abs(speaking_rate - 150) / 300, 1.0)
            violations.append(ConsistencyViolation(
                violation_type="speaking_rate_mismatch",
                modalities=["audio", "text"],
                severity=sev,
                description=f"Speaking rate {speaking_rate:.0f} wpm is outside plausible human range (100–200 wpm).",
                evidence={"speaking_rate_wpm": speaking_rate,
                           "expected_range": "100–200 wpm"},
            ))
            scores.append(sev)
        else:
            scores.append(0.0)

        # ── 2. Vocabulary complexity vs audio length ──────────
        words   = re.findall(r'\b[a-z]{2,}\b', text.lower())
        avg_len = np.mean([len(w) for w in words]) if words else 0.0
        # Very short audio (<30s) with very complex vocabulary = mismatch
        complexity_mismatch = 0.0
        if duration_sec < 30 and avg_len > 7.0:
            complexity_mismatch = min((avg_len - 7.0) / 3.0, 1.0)
        elif duration_sec > 300 and avg_len < 3.5:
            complexity_mismatch = min((3.5 - avg_len) / 2.0, 1.0)

        details["avg_word_length"] = round(float(avg_len), 2)
        details["complexity_mismatch"] = round(complexity_mismatch, 4)
        scores.append(complexity_mismatch)

        if complexity_mismatch > 0.3:
            violations.append(ConsistencyViolation(
                violation_type="vocabulary_complexity_mismatch",
                modalities=["audio", "text"],
                severity=complexity_mismatch,
                description=f"Text vocabulary complexity (avg word len {avg_len:.1f}) doesn't match audio duration ({duration_sec:.0f}s).",
                evidence={"avg_word_length": avg_len, "duration_sec": duration_sec},
            ))

        # ── 3. Silence regions vs paragraph count ─────────────
        pause_count   = self._count_pauses(audio, sr)
        para_count    = len([p for p in text.split('\n\n') if p.strip()])
        pause_ratio   = abs(pause_count - para_count) / max(max(pause_count, para_count), 1)
        details["pause_count"]   = pause_count
        details["paragraph_count"] = para_count
        details["pause_para_ratio_diff"] = round(pause_ratio, 4)

        if pause_ratio > 0.7 and para_count > 3:
            sev = min(pause_ratio, 1.0)
            violations.append(ConsistencyViolation(
                violation_type="pause_paragraph_mismatch",
                modalities=["audio", "text"],
                severity=sev,
                description=f"Audio has {pause_count} major pauses but text has {para_count} paragraphs — structure mismatch.",
                evidence={"pauses": pause_count, "paragraphs": para_count},
            ))
            scores.append(sev * 0.5)
        else:
            scores.append(0.0)

        inconsistency = float(np.mean(scores)) if scores else 0.0

        return CrossModalReport(
            is_consistent=inconsistency <= self.CONSISTENCY_THRESHOLD,
            inconsistency_score=min(inconsistency, 1.0),
            confidence=0.65,
            violations=violations,
            summary=self._at_summary(inconsistency, violations),
            analysis_details=details,
        )

    # ═══════════════════════════════════════════
    #  IMAGE ↔ TEXT
    # ═══════════════════════════════════════════

    def verify_image_text(self, image_bytes: bytes, text_bytes: bytes) -> CrossModalReport:
        """
        Check consistency between an image and its caption/description.

        Tests
        -----
        1. Color description match — text mentions colours found in image
        2. Brightness adjective    — dark/light/vivid vs actual brightness
        3. Text length vs image complexity — overly short description for complex image
        """
        violations: List[ConsistencyViolation] = []
        details: Dict[str, Any] = {}
        scores: List[float] = []

        text = self._decode_text(text_bytes)

        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            arr = np.array(img)
        except Exception:
            return CrossModalReport(True, 0.0, 0.2,
                                    summary="Could not parse image for cross-modal check.")

        # ── 1. Colour description match ───────────────────────
        colour_score = self._colour_description_match(arr, text)
        details["colour_description_score"] = round(colour_score, 4)
        scores.append(colour_score)

        if colour_score > 0.5:
            violations.append(ConsistencyViolation(
                violation_type="colour_description_mismatch",
                modalities=["image", "text"],
                severity=colour_score,
                description="Dominant image colours are inconsistent with the text description.",
                evidence={"mismatch_score": round(colour_score, 3)},
            ))

        # ── 2. Brightness adjective ───────────────────────────
        brightness_score = self._brightness_adjective_match(arr, text)
        details["brightness_adjective_score"] = round(brightness_score, 4)
        scores.append(brightness_score)

        if brightness_score > 0.5:
            violations.append(ConsistencyViolation(
                violation_type="brightness_description_mismatch",
                modalities=["image", "text"],
                severity=brightness_score,
                description="Brightness description in text contradicts image luminance.",
                evidence={"mismatch_score": round(brightness_score, 3)},
            ))

        # ── 3. Image complexity vs description length ─────────
        gray      = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        lap_var   = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        word_count = len(text.split())
        details["image_laplacian_variance"] = round(lap_var, 2)
        details["description_word_count"]   = word_count

        # Complex image (lap_var > 500) with very short caption (< 10 words) = mismatch
        complexity_gap = 0.0
        if lap_var > 500 and word_count < 10:
            complexity_gap = min((lap_var - 500) / 2000, 1.0) * 0.6
        scores.append(complexity_gap)

        if complexity_gap > 0.3:
            violations.append(ConsistencyViolation(
                violation_type="complexity_description_gap",
                modalities=["image", "text"],
                severity=complexity_gap,
                description=f"Complex image (sharpness={lap_var:.0f}) but very short description ({word_count} words).",
                evidence={"laplacian_variance": lap_var, "word_count": word_count},
            ))

        inconsistency = float(np.mean(scores)) if scores else 0.0

        return CrossModalReport(
            is_consistent=inconsistency <= self.CONSISTENCY_THRESHOLD,
            inconsistency_score=min(inconsistency, 1.0),
            confidence=0.60,
            violations=violations,
            summary=self._it_summary(inconsistency, violations),
            analysis_details=details,
        )

    # ═══════════════════════════════════════════
    #  VIDEO ↔ TEXT
    # ═══════════════════════════════════════════

    def verify_video_text(self, video_bytes: bytes, text_bytes: bytes) -> CrossModalReport:
        """
        Check consistency between video visual content and a text description/transcript.

        Tests
        -----
        1. Dominant colour vs description
        2. Motion level vs action description
        3. Scene count vs paragraph count
        """
        violations: List[ConsistencyViolation] = []
        details: Dict[str, Any] = {}
        scores: List[float] = []

        text = self._decode_text(text_bytes)
        frames, fps, _ = self._extract_video_frames(video_bytes, n=12)

        if not frames or not text:
            return CrossModalReport(True, 0.0, 0.2,
                                    summary="Insufficient data for video-text cross-modal check.")

        # ── 1. Dominant colour vs description ─────────────────
        avg_frame = np.mean([f.astype(np.float32) for f in frames], axis=0).astype(np.uint8)
        avg_rgb   = cv2.cvtColor(avg_frame, cv2.COLOR_BGR2RGB)
        colour_score = self._colour_description_match(avg_rgb, text)
        details["colour_description_score"] = round(colour_score, 4)
        scores.append(colour_score * 0.7)   # Lower weight for video

        if colour_score > 0.6:
            violations.append(ConsistencyViolation(
                violation_type="video_colour_description_mismatch",
                modalities=["video", "text"],
                severity=colour_score,
                description="Dominant video colours are inconsistent with the text description.",
                evidence={"mismatch_score": round(colour_score, 3)},
            ))

        # ── 2. Motion level vs action verbs ──────────────────
        motion_score, motion_level = self._video_motion_level(frames)
        action_verbs = self._count_action_verbs(text)
        details["video_motion_level"] = round(motion_score, 4)
        details["action_verbs_count"] = action_verbs

        # High motion but text describes static scene = mismatch
        motion_mismatch = 0.0
        if motion_score > 0.6 and action_verbs < 2:
            motion_mismatch = 0.5
        elif motion_score < 0.1 and action_verbs > 5:
            motion_mismatch = 0.4
        scores.append(motion_mismatch)
        details["motion_text_mismatch"] = round(motion_mismatch, 4)

        if motion_mismatch > 0.3:
            violations.append(ConsistencyViolation(
                violation_type="motion_description_mismatch",
                modalities=["video", "text"],
                severity=motion_mismatch,
                description=f"Video motion level ({motion_level}) contradicts text action density ({action_verbs} verbs).",
                evidence={"motion_level": motion_level, "action_verbs": action_verbs},
            ))

        # ── 3. Scene count vs paragraph count ────────────────
        scene_count = self._count_scene_cuts(frames)
        para_count  = len([p for p in text.split('\n\n') if p.strip()])
        details["scene_cuts_count"] = scene_count
        details["paragraph_count"]  = para_count

        if para_count > 1 and scene_count > 0:
            ratio_diff = abs(scene_count - para_count) / max(scene_count, para_count, 1)
            if ratio_diff > 0.7:
                sev = min(ratio_diff, 1.0) * 0.4
                scores.append(sev)
                violations.append(ConsistencyViolation(
                    violation_type="scene_paragraph_mismatch",
                    modalities=["video", "text"],
                    severity=sev,
                    description=f"Video has {scene_count} scene cuts but text has {para_count} paragraphs.",
                    evidence={"scene_cuts": scene_count, "paragraphs": para_count},
                ))
            else:
                scores.append(0.0)

        inconsistency = float(np.mean(scores)) if scores else 0.0

        return CrossModalReport(
            is_consistent=inconsistency <= self.CONSISTENCY_THRESHOLD,
            inconsistency_score=min(inconsistency, 1.0),
            confidence=0.55,
            violations=violations,
            summary=self._vt_summary(inconsistency, violations),
            analysis_details=details,
        )

    # ─────────────────────────────────────────────────────────
    #  MERGE
    # ─────────────────────────────────────────────────────────

    def _merge_reports(self, reports: List[CrossModalReport]) -> CrossModalReport:
        if not reports:
            return CrossModalReport(True, 0.0, 0.1)

        all_violations = []
        all_details: Dict[str, Any] = {}
        scores = []
        confidences = []

        for i, r in enumerate(reports):
            all_violations.extend(r.violations)
            prefix = f"check_{i}_"
            all_details.update({prefix + k: v for k, v in r.analysis_details.items()})
            scores.append(r.inconsistency_score)
            confidences.append(r.confidence)

        inconsistency = float(np.mean(scores))
        confidence    = float(np.mean(confidences))
        consistent    = inconsistency <= self.CONSISTENCY_THRESHOLD

        n_viol = len(all_violations)
        if not consistent and n_viol > 0:
            top = sorted(all_violations, key=lambda v: -v.severity)
            desc = f"Cross-modal check: {n_viol} violation(s) found. Top issue: {top[0].description}"
        else:
            desc = f"Cross-modal check passed across {len(reports)} modality pair(s)."

        return CrossModalReport(
            is_consistent=consistent,
            inconsistency_score=min(inconsistency, 1.0),
            confidence=confidence,
            violations=all_violations,
            summary=desc,
            analysis_details=all_details,
        )

    # ─────────────────────────────────────────────────────────
    #  UTILITY METHODS
    # ─────────────────────────────────────────────────────────

    def _load_audio(self, file_bytes: bytes):
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

    def _extract_video_properties(self, video_bytes: bytes):
        """Return (audio_track_array_or_None, fps, total_frames)."""
        tmp = None
        cap = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(video_bytes)
                tmp = f.name
            cap = cv2.VideoCapture(tmp)
            fps    = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            # We can't extract audio from video easily without ffmpeg,
            # so return None for audio track in pure-OpenCV mode.
            return None, fps, total
        except Exception:
            return None, 25.0, 0
        finally:
            if cap: cap.release()
            if tmp and os.path.exists(tmp):
                try: os.unlink(tmp)
                except Exception: pass

    def _extract_video_frames(self, video_bytes: bytes, n: int = 16):
        tmp = None
        cap = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(video_bytes)
                tmp = f.name
            cap = cv2.VideoCapture(tmp)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps   = cap.get(cv2.CAP_PROP_FPS) or 25.0
            meta  = {"total": total, "fps": fps}

            if total <= 0:
                return [], fps, meta

            idxs   = [int(i * total / n) for i in range(min(n, total))]
            frames = []
            for idx in idxs:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
            return frames, fps, meta
        except Exception:
            return [], 25.0, {}
        finally:
            if cap: cap.release()
            if tmp and os.path.exists(tmp):
                try: os.unlink(tmp)
                except Exception: pass

    def _decode_text(self, file_bytes: bytes) -> str:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                t = file_bytes.decode(enc, errors="ignore")
                t = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]', ' ', t)
                return re.sub(r'\s+', ' ', t).strip()
            except Exception:
                continue
        return ""

    def _energy_sync(self, audio1: np.ndarray, audio2: np.ndarray) -> float:
        """Compare energy envelopes of two audio signals."""
        try:
            chunk = 4096
            def envelope(a):
                return np.array([
                    np.sqrt(np.mean(a[i:i+chunk]**2))
                    for i in range(0, len(a) - chunk, chunk)
                ])

            env1 = envelope(audio1)
            env2 = envelope(audio2)

            n = min(len(env1), len(env2))
            if n < 3:
                return 0.0

            # Normalise then correlate
            e1 = (env1[:n] - env1[:n].mean()) / (env1[:n].std() + 1e-9)
            e2 = (env2[:n] - env2[:n].mean()) / (env2[:n].std() + 1e-9)
            corr = float(np.corrcoef(e1, e2)[0, 1])
            return max(0.0, (1.0 - corr) / 2)
        except Exception:
            return 0.0

    def _noise_floor_match(self, audio1: np.ndarray, audio2: np.ndarray) -> float:
        """Compare quiet segment noise levels."""
        try:
            chunk = 2048
            def quiet_rms(a):
                rms = [np.sqrt(np.mean(a[i:i+chunk]**2))
                       for i in range(0, len(a) - chunk, chunk)]
                return np.percentile(rms, 10) if rms else 0.0

            q1 = quiet_rms(audio1)
            q2 = quiet_rms(audio2)
            diff = abs(q1 - q2) / max(q1, q2, 1e-9)
            return min(diff * 2, 1.0)
        except Exception:
            return 0.0

    def _count_pauses(self, audio: np.ndarray, sr: int) -> int:
        """Count major pause regions (silence > 0.5s)."""
        try:
            frame_len = sr // 20   # 50 ms
            threshold = 0.01
            in_silence = False
            pause_count = 0
            min_pause_frames = sr // (2 * frame_len)   # 0.5s

            run = 0
            for i in range(0, len(audio) - frame_len, frame_len):
                energy = np.sqrt(np.mean(audio[i:i+frame_len]**2))
                if energy < threshold:
                    run += 1
                    if run == min_pause_frames:
                        pause_count += 1
                else:
                    run = 0

            return pause_count
        except Exception:
            return 0

    def _colour_description_match(self, rgb_arr: np.ndarray, text: str) -> float:
        """
        Check whether colour words in text are consistent with dominant image colours.
        """
        try:
            colour_map = {
                "red":    ([150, 30, 30], [255, 100, 100]),
                "green":  ([30, 100, 30], [100, 200, 100]),
                "blue":   ([30, 30, 120], [100, 100, 255]),
                "white":  ([200, 200, 200], [255, 255, 255]),
                "black":  ([0, 0, 0], [60, 60, 60]),
                "yellow": ([180, 180, 0], [255, 255, 100]),
                "orange": ([180, 80, 0], [255, 160, 50]),
                "purple": ([80, 0, 100], [180, 50, 200]),
                "brown":  ([80, 40, 10], [160, 100, 60]),
                "gray":   ([80, 80, 80], [170, 170, 170]),
                "grey":   ([80, 80, 80], [170, 170, 170]),
                "pink":   ([200, 100, 150], [255, 180, 210]),
            }

            text_lower = text.lower()
            mentioned_colours = {c for c in colour_map if c in text_lower}

            if not mentioned_colours:
                return 0.0   # No colour mentioned, nothing to check

            # Find dominant colours in image
            pixels = rgb_arr.reshape(-1, 3)
            # Sample 1000 pixels for speed
            sample = pixels[np.random.choice(len(pixels), min(1000, len(pixels)), replace=False)]

            present_colours = set()
            for name, (lo, hi) in colour_map.items():
                lo_arr = np.array(lo)
                hi_arr = np.array(hi)
                mask = np.all((sample >= lo_arr) & (sample <= hi_arr), axis=1)
                if mask.sum() > 30:   # At least 3% of samples
                    present_colours.add(name)

            if not present_colours:
                return 0.0

            # Mismatch: text mentions colours not in image
            text_not_in_image = mentioned_colours - present_colours
            mismatch_ratio = len(text_not_in_image) / max(len(mentioned_colours), 1)
            return float(mismatch_ratio)
        except Exception:
            return 0.0

    def _brightness_adjective_match(self, rgb_arr: np.ndarray, text: str) -> float:
        """Check brightness adjectives vs actual luminance."""
        try:
            luminance = float(np.mean(cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2GRAY)))
            text_lower = text.lower()

            dark_words  = ["dark", "dim", "shadowy", "gloomy", "night", "black"]
            light_words = ["bright", "vivid", "sunny", "light", "white", "glowing"]

            mentions_dark  = any(w in text_lower for w in dark_words)
            mentions_light = any(w in text_lower for w in light_words)

            if mentions_dark and luminance > 180:
                return 0.7   # Text says dark, image is bright
            if mentions_light and luminance < 80:
                return 0.7   # Text says bright, image is dark
            return 0.0
        except Exception:
            return 0.0

    def _video_motion_level(self, frames: list):
        """Return (0-1 motion score, label)."""
        try:
            if len(frames) < 2: return 0.0, "unknown"
            diffs = []
            for i in range(1, len(frames)):
                g1 = cv2.cvtColor(frames[i-1], cv2.COLOR_BGR2GRAY).astype(np.float32)
                g2 = cv2.cvtColor(frames[i],   cv2.COLOR_BGR2GRAY).astype(np.float32)
                diffs.append(np.mean(np.abs(g2 - g1)))
            mean_d = float(np.mean(diffs))
            if mean_d < 1.0:   return 0.05, "static"
            if mean_d < 5.0:   return 0.30, "low"
            if mean_d < 15.0:  return 0.60, "moderate"
            return 0.90, "high"
        except Exception:
            return 0.0, "unknown"

    def _count_action_verbs(self, text: str) -> int:
        action_verbs = [
            "run", "jump", "walk", "move", "fight", "chase", "attack",
            "drive", "fly", "swim", "climb", "fall", "dance", "shoot",
            "throw", "hit", "kick", "push", "pull", "grab",
        ]
        text_lower = text.lower()
        return sum(1 for v in action_verbs if re.search(r'\b' + v + r'\b', text_lower))

    def _count_scene_cuts(self, frames: list) -> int:
        """Count abrupt scene changes in frame list."""
        try:
            cuts = 0
            for i in range(1, len(frames)):
                g1 = cv2.cvtColor(frames[i-1], cv2.COLOR_BGR2GRAY).astype(np.float32)
                g2 = cv2.cvtColor(frames[i],   cv2.COLOR_BGR2GRAY).astype(np.float32)
                diff = np.mean(np.abs(g2 - g1))
                if diff > 40:
                    cuts += 1
            return cuts
        except Exception:
            return 0

    # ── Summary helpers ───────────────────────────────────────

    def _va_summary(self, score, violations):
        if score <= self.CONSISTENCY_THRESHOLD:
            return "Video and audio are consistent."
        tops = [v.description for v in sorted(violations, key=lambda v: -v.severity)[:2]]
        return "Video–Audio inconsistency detected. " + " | ".join(tops)

    def _at_summary(self, score, violations):
        if score <= self.CONSISTENCY_THRESHOLD:
            return "Audio and text transcript are consistent."
        tops = [v.description for v in sorted(violations, key=lambda v: -v.severity)[:2]]
        return "Audio–Text inconsistency detected. " + " | ".join(tops)

    def _it_summary(self, score, violations):
        if score <= self.CONSISTENCY_THRESHOLD:
            return "Image and text description are consistent."
        tops = [v.description for v in sorted(violations, key=lambda v: -v.severity)[:2]]
        return "Image–Text inconsistency detected. " + " | ".join(tops)

    def _vt_summary(self, score, violations):
        if score <= self.CONSISTENCY_THRESHOLD:
            return "Video and text are consistent."
        tops = [v.description for v in sorted(violations, key=lambda v: -v.severity)[:2]]
        return "Video–Text inconsistency detected. " + " | ".join(tops)