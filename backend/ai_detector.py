"""
ai_detector.py -
Enhanced AI-based tampering detection system for Authx
Multi-modal: images, audio, video, and text documents
"""

import io
import re
import math
import struct
import wave
import tempfile
import os
import numpy as np
from PIL import Image
import cv2
from typing import Dict, List, Optional
from collections import Counter


# ─────────────────────────────────────────────
#  IMAGE DETECTOR (unchanged from your original)
# ─────────────────────────────────────────────

class EnhancedAITamperingDetector:
    """
    Multi-modal AI tampering detection system.
    Handles images, audio, video, and text documents.
    """

    def __init__(self):
        self.detection_methods = [
            "statistical_analysis",
            "frequency_domain",
            "noise_pattern",
            "metadata_analysis",
            "texture_analysis",
            "color_distribution",
        ]

    # ─── PUBLIC ENTRY POINT ───────────────────

    def analyze(self, file_bytes: bytes, content_type: str) -> Dict:
        """
        Dispatch analysis based on content type.
        Returns a unified result dict regardless of modality.
        """
        ct = content_type.lower()

        if ct.startswith("image"):
            return self._analyze_image(file_bytes)
        elif ct.startswith("audio"):
            return self._analyze_audio(file_bytes, ct)
        elif ct.startswith("video"):
            return self._analyze_video(file_bytes, ct)
        elif ct.startswith("text") or "pdf" in ct or "document" in ct or "msword" in ct:
            return self._analyze_text(file_bytes)
        else:
            return self._analyze_generic(file_bytes)

    # ═══════════════════════════════════════════
    #  IMAGE ANALYSIS
    # ═══════════════════════════════════════════

    def _analyze_image(self, file_bytes: bytes) -> Dict:
        try:
            image = Image.open(io.BytesIO(file_bytes))
            img_array = np.array(image.convert("RGB"))
            is_camera_photo = self._is_camera_photo(image)

            statistical_score = self._statistical_analysis(img_array, is_camera_photo)
            frequency_score   = self._frequency_domain_analysis(img_array, is_camera_photo)
            noise_score       = self._noise_pattern_analysis(img_array, is_camera_photo)
            metadata_score    = self._metadata_analysis(image)
            texture_score     = self._texture_analysis(img_array)
            color_score       = self._color_distribution_analysis(img_array)

            scores = {
                "statistical_score": statistical_score,
                "frequency_score":   frequency_score,
                "noise_score":       noise_score,
                "metadata_score":    metadata_score,
                "texture_score":     texture_score,
                "color_score":       color_score,
            }

            if is_camera_photo:
                tamper_probability = (
                    statistical_score * 0.15
                    + frequency_score * 0.15
                    + noise_score     * 0.10
                    + metadata_score  * 0.05
                    + texture_score   * 0.30
                    + color_score     * 0.25
                )
            else:
                tamper_probability = (
                    statistical_score * 0.20
                    + frequency_score * 0.25
                    + noise_score     * 0.20
                    + metadata_score  * 0.15
                    + texture_score   * 0.10
                    + color_score     * 0.10
                )

            confidence         = self._calculate_confidence(scores, is_camera_photo)
            detected_artifacts = self._identify_artifacts(scores, img_array, is_camera_photo)

            return {
                "tamper_probability":  float(min(tamper_probability, 1.0)),
                "confidence":          float(confidence),
                "detected_artifacts":  detected_artifacts,
                "is_camera_photo":     is_camera_photo,
                "modality":            "image",
                "analysis_details": {
                    "statistical_score": float(statistical_score),
                    "frequency_score":   float(frequency_score),
                    "noise_score":       float(noise_score),
                    "metadata_score":    float(metadata_score),
                    "texture_score":     float(texture_score),
                    "color_score":       float(color_score),
                },
            }
        except Exception as e:
            print(f"⚠️  Image analysis error: {e}")
            return self._default_analysis("image")

    def _is_camera_photo(self, image: Image.Image) -> bool:
        try:
            exif_data  = image.getexif() if hasattr(image, "getexif") else {}
            camera_tags = [271, 272, 274, 282, 283, 36867, 36868,
                           37377, 37378, 37380, 37381, 37383, 37385, 37386]
            return sum(1 for t in camera_tags if t in exif_data) >= 3
        except Exception:
            return False

    def _statistical_analysis(self, img_array: np.ndarray, is_camera: bool) -> float:
        try:
            gray  = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            std   = np.std(gray)
            score = 0.0
            if std < 25:
                score += 0.4
            elif std < 35:
                score += 0.2

            patch_size = 32
            h, w = gray.shape
            patch_stds = [
                np.std(gray[i:i+patch_size, j:j+patch_size])
                for i in range(0, h - patch_size, patch_size)
                for j in range(0, w - patch_size, patch_size)
            ]
            if patch_stds and np.std(patch_stds) < 5:
                score += 0.3
            if is_camera:
                score *= 0.5
            return min(score, 1.0)
        except Exception:
            return 0.0

    def _frequency_domain_analysis(self, img_array: np.ndarray, is_camera: bool) -> float:
        try:
            gray  = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            gray  = cv2.resize(gray, (256, 256))
            dct   = cv2.dct(np.float32(gray))
            high_freq_energy = np.sum(np.abs(dct[128:, 128:]))
            total_energy     = np.sum(np.abs(dct))
            ratio = high_freq_energy / (total_energy + 1e-10)

            if ratio < 0.08:   score = 0.8
            elif ratio < 0.12: score = 0.5
            elif ratio < 0.15: score = 0.2
            else:               score = 0.0

            if is_camera and ratio > 0.10:
                score *= 0.3
            return score
        except Exception:
            return 0.0

    def _noise_pattern_analysis(self, img_array: np.ndarray, is_camera: bool) -> float:
        try:
            gray      = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY).astype(np.float32)
            blurred   = cv2.GaussianBlur(gray, (5, 5), 0)
            noise_std = np.std(gray - blurred)

            if noise_std < 1.5:   score = 0.7
            elif noise_std < 2.5: score = 0.4
            elif noise_std < 3.5: score = 0.2
            else:                  score = 0.0

            if is_camera and noise_std >= 2.0:
                score = 0.0
            return score
        except Exception:
            return 0.0

    def _texture_analysis(self, img_array: np.ndarray) -> float:
        try:
            gray      = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            lap_var   = cv2.Laplacian(gray, cv2.CV_64F).var()
            sobelx    = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely    = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            grad_mean = np.mean(np.sqrt(sobelx**2 + sobely**2))

            score = 0.0
            if lap_var   < 50: score += 0.4
            if grad_mean < 10: score += 0.3
            return min(score, 1.0)
        except Exception:
            return 0.0

    def _color_distribution_analysis(self, img_array: np.ndarray) -> float:
        try:
            hsv      = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            sat      = hsv[:, :, 1]
            sat_mean = np.mean(sat)
            sat_std  = np.std(sat)

            score = 0.0
            if sat_mean > 180 or sat_mean < 30: score += 0.3
            if sat_std < 30:                     score += 0.4
            return min(score, 1.0)
        except Exception:
            return 0.0

    def _metadata_analysis(self, image: Image.Image) -> float:
        try:
            exif_data = image.getexif() if hasattr(image, "getexif") else {}
            score = 0.0
            if not exif_data or len(exif_data) < 2:
                score += 0.5
            for tag in [271, 305]:
                if tag in exif_data:
                    sw = str(exif_data[tag]).lower()
                    if any(k in sw for k in ["midjourney", "dalle", "stable diffusion",
                                              "ai", "generated", "synthetic"]):
                        return 1.0
            return min(score, 1.0)
        except Exception:
            return 0.0

    def _calculate_confidence(self, scores: Dict[str, float], is_camera: bool) -> float:
        vals       = list(scores.values())
        std_dev    = np.std(vals)
        mean_score = np.mean(vals)

        if std_dev < 0.15:   confidence = 0.90
        elif std_dev < 0.25: confidence = 0.75
        elif std_dev < 0.35: confidence = 0.60
        else:                 confidence = 0.45

        if is_camera and mean_score < 0.3:
            confidence = min(confidence + 0.15, 1.0)
        if mean_score > 0.75 or mean_score < 0.2:
            confidence = min(confidence + 0.10, 1.0)
        return confidence

    def _identify_artifacts(self, scores: Dict[str, float], img_array: np.ndarray,
                             is_camera: bool) -> List[str]:
        artifacts = []
        threshold = 0.75 if is_camera else 0.60

        if scores["statistical_score"] > threshold: artifacts.append("unusual_pixel_distribution")
        if scores["frequency_score"]   > threshold: artifacts.append("gan_frequency_signature")
        if scores["noise_score"]       > threshold: artifacts.append("synthetic_noise_pattern")
        if scores["metadata_score"]    > 0.80:      artifacts.append("ai_tool_signature")
        if scores["texture_score"]     > threshold: artifacts.append("lack_of_micro_texture")
        if scores["color_score"]       > threshold: artifacts.append("unnatural_color_distribution")
        if self._detect_grid_artifacts(img_array):  artifacts.append("grid_artifacts")
        return artifacts

    def _detect_grid_artifacts(self, img_array: np.ndarray) -> bool:
        try:
            gray      = cv2.resize(cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY), (256, 256))
            f_shift   = np.fft.fftshift(np.fft.fft2(gray))
            magnitude = np.abs(f_shift)
            threshold = np.mean(magnitude) + 4 * np.std(magnitude)
            return bool(np.sum(magnitude > threshold) > 15)
        except Exception:
            return False

    # ═══════════════════════════════════════════
    #  AUDIO ANALYSIS
    # ═══════════════════════════════════════════

    def _analyze_audio(self, file_bytes: bytes, content_type: str) -> Dict:
        """
        Detect AI-generated or tampered audio.

        Six analysis layers:
          1. Spectral flatness  – AI speech/music tends to be spectrally too uniform
          2. Noise floor        – Synthetic audio lacks natural background noise variance
          3. Silence pattern    – AI clips often have unnaturally clean silent segments
          4. Dynamic range      – AI TTS is heavily compressed; real recordings vary more
          5. Frequency band balance – over-boosted or missing frequency bands
          6. Clipping / saturation – heavy post-processing signature
        """
        try:
            audio_data, sample_rate = self._load_audio_pcm(file_bytes)
            if audio_data is None:
                return self._analyze_audio_bytes(file_bytes)

            scores = {}

            scores["spectral_flatness"]   = self._audio_spectral_flatness(audio_data, sample_rate)
            scores["noise_floor"]         = self._audio_noise_floor(audio_data)
            scores["silence_pattern"]     = self._audio_silence_pattern(audio_data, sample_rate)
            scores["dynamic_range"]       = self._audio_dynamic_range(audio_data)
            scores["frequency_balance"]   = self._audio_frequency_balance(audio_data, sample_rate)
            scores["clipping_saturation"] = self._audio_clipping(audio_data)

            tamper_probability = (
                scores["spectral_flatness"]   * 0.25
                + scores["noise_floor"]       * 0.20
                + scores["silence_pattern"]   * 0.15
                + scores["dynamic_range"]     * 0.20
                + scores["frequency_balance"] * 0.10
                + scores["clipping_saturation"] * 0.10
            )

            confidence         = self._score_confidence(scores)
            detected_artifacts = self._identify_audio_artifacts(scores)

            return {
                "tamper_probability": float(min(tamper_probability, 1.0)),
                "confidence":         float(confidence),
                "detected_artifacts": detected_artifacts,
                "is_camera_photo":    False,
                "modality":           "audio",
                "analysis_details":   {k: float(v) for k, v in scores.items()},
            }
        except Exception as e:
            print(f"⚠️  Audio analysis error: {e}")
            return self._default_analysis("audio")

    def _load_audio_pcm(self, file_bytes: bytes):
        """Try to read WAV; return (float32 array, sample_rate) or (None, None)."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            try:
                with wave.open(tmp_path, "rb") as wf:
                    n_frames    = wf.getnframes()
                    sampwidth   = wf.getsampwidth()
                    sample_rate = wf.getframerate()
                    raw         = wf.readframes(n_frames)

                dtype_map = {1: np.uint8, 2: np.int16, 4: np.int32}
                dtype = dtype_map.get(sampwidth, np.int16)
                audio = np.frombuffer(raw, dtype=dtype).astype(np.float32)
                peak  = np.max(np.abs(audio))
                if peak > 0:
                    audio /= peak
                return audio, sample_rate
            finally:
                os.unlink(tmp_path)
        except Exception:
            return None, None

    def _audio_spectral_flatness(self, audio: np.ndarray, sr: int) -> float:
        """
        Wiener entropy / spectral flatness.
        AI speech is spectrally flat (TTS) or too uniform (GAN music).
        High flatness in voiced segments → suspicious.
        """
        try:
            chunk  = 4096
            n_chunks = min(30, len(audio) // chunk)
            flatness_vals = []

            for i in range(n_chunks):
                seg = audio[i * chunk: i * chunk + chunk]
                fft = np.abs(np.fft.rfft(seg)) + 1e-9
                geo_mean = np.exp(np.mean(np.log(fft)))
                ari_mean = np.mean(fft)
                flatness_vals.append(geo_mean / ari_mean)

            if not flatness_vals:
                return 0.0

            mean_flat = np.mean(flatness_vals)
            std_flat  = np.std(flatness_vals)

            score = 0.0
            # Very high flatness throughout = TTS / AI music
            if mean_flat > 0.55:  score += 0.5
            elif mean_flat > 0.40: score += 0.25

            # Very consistent flatness = AI (lacks natural variation)
            if std_flat < 0.05:   score += 0.4
            elif std_flat < 0.10: score += 0.2

            return min(score, 1.0)
        except Exception:
            return 0.0

    def _audio_noise_floor(self, audio: np.ndarray) -> float:
        """
        Real recordings have a natural noise floor with some variance.
        AI-generated audio is often silence-padded or has a suspiciously clean floor.
        """
        try:
            chunk  = 2048
            rms_vals = [
                np.sqrt(np.mean(audio[i:i+chunk]**2))
                for i in range(0, len(audio) - chunk, chunk)
            ]
            if not rms_vals:
                return 0.0

            rms_arr = np.array(rms_vals)
            # Look only at the quietest 20 % of chunks (the noise floor)
            quiet_thresh = np.percentile(rms_arr, 20)
            quiet_chunks = rms_arr[rms_arr <= quiet_thresh + 1e-6]

            if len(quiet_chunks) == 0:
                return 0.0

            floor_std = np.std(quiet_chunks)
            floor_mean = np.mean(quiet_chunks)

            score = 0.0
            # Abnormally clean floor (near-zero variance) = synthetic
            if floor_std < 1e-4:   score += 0.6
            elif floor_std < 5e-4: score += 0.3

            # Complete silence = heavy editing / AI
            if floor_mean < 1e-5:  score += 0.3

            return min(score, 1.0)
        except Exception:
            return 0.0

    def _audio_silence_pattern(self, audio: np.ndarray, sr: int) -> float:
        """
        AI-generated audio often has perfectly abrupt silence segments.
        Real recordings have natural fade-in/out at silent regions.
        """
        try:
            frame_len  = sr // 100  # 10 ms frames
            energies   = [
                np.sum(audio[i:i+frame_len]**2)
                for i in range(0, len(audio) - frame_len, frame_len)
            ]
            if not energies:
                return 0.0

            threshold = np.mean(energies) * 0.01
            silent    = [e < threshold for e in energies]

            # Count abrupt transitions (silence→voice or voice→silence)
            transitions = sum(1 for i in range(1, len(silent)) if silent[i] != silent[i-1])
            duration_s  = len(audio) / max(sr, 1)

            trans_rate = transitions / max(duration_s, 1)

            score = 0.0
            # Very high transition rate = unnatural cuts
            if trans_rate > 20:   score += 0.5
            elif trans_rate > 10: score += 0.25

            # Check for perfectly rectangular silence blocks
            run_lengths = []
            cur_run = 1
            for i in range(1, len(silent)):
                if silent[i] == silent[i-1]:
                    cur_run += 1
                else:
                    run_lengths.append(cur_run)
                    cur_run = 1
            run_lengths.append(cur_run)

            silent_runs = [r for r, s in zip(run_lengths, silent) if s]
            if len(silent_runs) > 2:
                std_runs = np.std(silent_runs)
                if std_runs < 2:  # Very uniform silence blocks = suspicious
                    score += 0.4

            return min(score, 1.0)
        except Exception:
            return 0.0

    def _audio_dynamic_range(self, audio: np.ndarray) -> float:
        """
        AI TTS and AI music are heavily compressed → low dynamic range.
        Real recordings have significant peak-to-RMS variation.
        """
        try:
            chunk    = 4096
            rms_vals = [
                np.sqrt(np.mean(audio[i:i+chunk]**2))
                for i in range(0, len(audio) - chunk, chunk)
            ]
            if not rms_vals:
                return 0.0

            rms_arr = np.array(rms_vals)
            peak    = np.max(np.abs(audio))
            rms_max = np.max(rms_arr)

            # Crest factor: peak / RMS. Low crest → highly compressed
            crest = peak / (rms_max + 1e-9)

            score = 0.0
            if crest < 2.0:   score += 0.5   # Very compressed
            elif crest < 3.5: score += 0.25

            # Dynamic range within the track
            dr = np.max(rms_arr) / (np.min(rms_arr) + 1e-9)
            if dr < 2.0:   score += 0.4   # Almost no variation
            elif dr < 4.0: score += 0.2

            return min(score, 1.0)
        except Exception:
            return 0.0

    def _audio_frequency_balance(self, audio: np.ndarray, sr: int) -> float:
        """
        Check for unnaturally boosted / missing frequency bands.
        AI voice cloners often over-emphasise certain bands.
        """
        try:
            fft  = np.abs(np.fft.rfft(audio))
            freq = np.fft.rfftfreq(len(audio), 1 / sr)

            def band_energy(lo, hi):
                mask = (freq >= lo) & (freq < hi)
                return np.sum(fft[mask]**2)

            sub_bass  = band_energy(20,   80)
            bass      = band_energy(80,   300)
            mid       = band_energy(300,  3000)
            high_mid  = band_energy(3000, 8000)
            presence  = band_energy(8000, min(sr//2, 20000))

            total = sub_bass + bass + mid + high_mid + presence + 1e-12
            ratios = [sub_bass/total, bass/total, mid/total,
                      high_mid/total, presence/total]

            score = 0.0
            # Missing presence range = bandwidth-limited TTS
            if ratios[4] < 0.01:  score += 0.4
            # Missing sub-bass entirely = heavily filtered
            if ratios[0] < 0.001: score += 0.2
            # Mid band dominates unnaturally (telephone-quality TTS)
            if ratios[2] > 0.90:  score += 0.4

            return min(score, 1.0)
        except Exception:
            return 0.0

    def _audio_clipping(self, audio: np.ndarray) -> float:
        """
        Heavy clipping or saturation → indicates post-processing / loudness war.
        AI-generated media is often over-processed.
        """
        try:
            clipped = np.sum(np.abs(audio) > 0.99)
            ratio   = clipped / (len(audio) + 1)

            if ratio > 0.05:    return 0.8
            elif ratio > 0.01:  return 0.4
            elif ratio > 0.002: return 0.1
            return 0.0
        except Exception:
            return 0.0

    def _identify_audio_artifacts(self, scores: Dict[str, float]) -> List[str]:
        artifacts = []
        if scores.get("spectral_flatness", 0)   > 0.5: artifacts.append("unnaturally_flat_spectrum")
        if scores.get("noise_floor", 0)         > 0.5: artifacts.append("synthetic_noise_floor")
        if scores.get("silence_pattern", 0)     > 0.5: artifacts.append("abrupt_silence_transitions")
        if scores.get("dynamic_range", 0)       > 0.5: artifacts.append("low_dynamic_range")
        if scores.get("frequency_balance", 0)   > 0.5: artifacts.append("unnatural_frequency_balance")
        if scores.get("clipping_saturation", 0) > 0.5: artifacts.append("clipping_or_saturation")
        return artifacts

    def _analyze_audio_bytes(self, file_bytes: bytes) -> Dict:
        """Fallback: basic byte-level audio analysis when WAV parsing fails."""
        try:
            arr = np.frombuffer(file_bytes, dtype=np.uint8).astype(np.float32)
            entropy = self._byte_entropy(file_bytes)
            score   = 0.0
            if entropy < 4.0:  score += 0.3   # Very low entropy = synthetic
            if entropy > 7.9:  score += 0.2   # Very high entropy = compressed / processed

            return {
                "tamper_probability": float(min(score, 1.0)),
                "confidence":         0.35,
                "detected_artifacts": ["format_not_parseable"],
                "is_camera_photo":    False,
                "modality":           "audio",
                "analysis_details":   {"byte_entropy": entropy},
            }
        except Exception:
            return self._default_analysis("audio")

    # ═══════════════════════════════════════════
    #  VIDEO ANALYSIS
    # ═══════════════════════════════════════════

    def _analyze_video(self, file_bytes: bytes, content_type: str) -> Dict:
        """
        Detect AI-generated or tampered video.

        Six analysis layers:
          1. Byte entropy pattern      – container-level structure anomalies
          2. Keyframe visual analysis  – sample frames with image detector
          3. Temporal consistency      – real videos have natural inter-frame variation
          4. Codec signature           – checks for deepfake / AI generation watermarks
          5. Resolution / bitrate fit  – AI video often has unusual compression ratios
          6. Color space consistency   – AI video has atypical color distributions
        """
        try:
            scores = {}

            scores["byte_entropy"]    = self._video_byte_entropy(file_bytes)
            scores["codec_signature"] = self._video_codec_signature(file_bytes)
            scores["bitrate_fit"]     = self._video_bitrate_fit(file_bytes)

            # Try to extract and analyse frames
            frame_score, frame_artifacts, temporal_score = self._video_frame_analysis(file_bytes)
            scores["keyframe_visual"]  = frame_score
            scores["temporal_consistency"] = temporal_score

            tamper_probability = (
                scores["byte_entropy"]         * 0.10
                + scores["codec_signature"]    * 0.20
                + scores["bitrate_fit"]        * 0.15
                + scores["keyframe_visual"]    * 0.35
                + scores["temporal_consistency"] * 0.20
            )

            confidence         = self._score_confidence(scores)
            detected_artifacts = self._identify_video_artifacts(scores, frame_artifacts)

            return {
                "tamper_probability": float(min(tamper_probability, 1.0)),
                "confidence":         float(confidence),
                "detected_artifacts": detected_artifacts,
                "is_camera_photo":    False,
                "modality":           "video",
                "analysis_details":   {k: float(v) for k, v in scores.items()},
            }
        except Exception as e:
            print(f"⚠️  Video analysis error: {e}")
            return self._default_analysis("video")

    def _video_byte_entropy(self, file_bytes: bytes) -> float:
        """Low entropy = highly repetitive / synthetic; very high = over-compressed."""
        entropy = self._byte_entropy(file_bytes)
        if entropy < 4.0:  return 0.7
        if entropy < 5.5:  return 0.3
        if entropy > 7.95: return 0.2
        return 0.0

    def _video_codec_signature(self, file_bytes: bytes) -> float:
        """
        Scan for known AI generation tool signatures in container metadata.
        Also checks for deepfake-related codec anomalies.
        """
        try:
            header = file_bytes[:4096].lower()
            ai_sigs = [
                b"stable diffusion", b"midjourney", b"runway", b"sora",
                b"gen-2", b"pika", b"kling", b"synthesia", b"d-id",
                b"deepfake", b"faceswap", b"ai-generated",
            ]
            if any(sig in header for sig in ai_sigs):
                return 1.0

            # Check for unusually short moov atom (common in synthetic container)
            moov_pos = file_bytes.find(b"moov")
            if moov_pos > 0:
                # moov should be reasonably sized for a real video
                if moov_pos < 100:  # Suspiciously early
                    return 0.3

            return 0.0
        except Exception:
            return 0.0

    def _video_bitrate_fit(self, file_bytes: bytes) -> float:
        """
        Very small file size relative to duration hints at heavy AI compression.
        Very large size for short content hints at uncompressed synthetic frames.
        """
        try:
            size_mb = len(file_bytes) / (1024 * 1024)
            # Without decoding we can't get duration; use rough heuristics on size alone
            # < 0.1 MB video is suspicious (either <1s or extremely compressed)
            if size_mb < 0.1:  return 0.4
            # > 500 MB is unusual for a typical upload
            if size_mb > 500:  return 0.2
            return 0.0
        except Exception:
            return 0.0

    def _video_frame_analysis(self, file_bytes: bytes):
        """
        Extract frames with OpenCV and run image-level analysis on each.
        Returns (mean_frame_score, combined_artifacts, temporal_score).
        """
        tmp_path = None
        cap      = None
        try:
            suffix = ".mp4"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                return 0.0, [], 0.0

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps          = cap.get(cv2.CAP_PROP_FPS) or 25
            if total_frames <= 0:
                return 0.0, [], 0.0

            # Sample up to 8 evenly spaced frames
            n_samples   = min(8, total_frames)
            sample_idxs = [int(i * total_frames / n_samples) for i in range(n_samples)]

            frame_scores     = []
            all_artifacts    = []
            prev_gray        = None
            temporal_diffs   = []

            for idx in sample_idxs:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    continue

                # Run image analysis on this frame
                frame_rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_bytes = cv2.imencode(".png", frame)[1].tobytes()
                result      = self._analyze_image(frame_bytes)
                frame_scores.append(result["tamper_probability"])
                all_artifacts.extend(result.get("detected_artifacts", []))

                # Temporal consistency: diff between consecutive frames
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_gray is not None:
                    diff = np.mean(np.abs(gray.astype(np.float32) - prev_gray.astype(np.float32)))
                    temporal_diffs.append(diff)
                prev_gray = gray

            cap.release()

            mean_frame_score = float(np.mean(frame_scores)) if frame_scores else 0.0

            # Temporal: very uniform diffs = AI loop; zero diffs = static frame repeated
            temporal_score = 0.0
            if temporal_diffs:
                std_diff  = np.std(temporal_diffs)
                mean_diff = np.mean(temporal_diffs)
                if mean_diff < 0.5:    temporal_score = 0.8   # Nearly static
                elif std_diff < 1.0:   temporal_score = 0.5   # Too uniform
                elif std_diff < 3.0:   temporal_score = 0.2

            unique_artifacts = list(set(all_artifacts))
            return mean_frame_score, unique_artifacts, temporal_score

        except Exception as e:
            print(f"  Frame extraction error: {e}")
            return 0.0, [], 0.0
        finally:
            if cap is not None:
                try: cap.release()
                except Exception: pass
            if tmp_path and os.path.exists(tmp_path):
                try: os.unlink(tmp_path)
                except Exception: pass

    def _identify_video_artifacts(self, scores: Dict[str, float],
                                   frame_artifacts: List[str]) -> List[str]:
        artifacts = list(frame_artifacts)
        if scores.get("byte_entropy", 0)         > 0.5: artifacts.append("abnormal_byte_entropy")
        if scores.get("codec_signature", 0)      > 0.5: artifacts.append("ai_tool_codec_signature")
        if scores.get("bitrate_fit", 0)          > 0.3: artifacts.append("unusual_bitrate_profile")
        if scores.get("temporal_consistency", 0) > 0.5: artifacts.append("low_temporal_variation")
        return list(set(artifacts))

    # ═══════════════════════════════════════════
    #  TEXT / DOCUMENT ANALYSIS
    # ═══════════════════════════════════════════

    def _analyze_text(self, file_bytes: bytes) -> Dict:
        """
        Detect AI-generated or heavily AI-edited text documents.

        Six analysis layers:
          1. Perplexity proxy        – burstiness / sentence-length variance
          2. Vocabulary richness     – AI text is often lexically uniform
          3. Punctuation patterns    – AI overuses certain punctuation patterns
          4. Sentence structure      – AI text has unnaturally consistent sentence lengths
          5. Burstiness              – humans write in bursts; AI is temporally flat
          6. N-gram repetition       – AI models repeat phrases more than humans
        """
        try:
            text = self._decode_text(file_bytes)
            if not text or len(text.strip()) < 50:
                return self._default_analysis("text")

            scores = {}
            scores["sentence_uniformity"] = self._text_sentence_uniformity(text)
            scores["vocabulary_richness"]  = self._text_vocabulary_richness(text)
            scores["punctuation_pattern"]  = self._text_punctuation_pattern(text)
            scores["burstiness"]           = self._text_burstiness(text)
            scores["ngram_repetition"]     = self._text_ngram_repetition(text)
            scores["paragraph_uniformity"] = self._text_paragraph_uniformity(text)

            tamper_probability = (
                scores["sentence_uniformity"]  * 0.25
                + scores["vocabulary_richness"] * 0.20
                + scores["punctuation_pattern"] * 0.15
                + scores["burstiness"]          * 0.20
                + scores["ngram_repetition"]    * 0.15
                + scores["paragraph_uniformity"] * 0.05
            )

            confidence         = self._score_confidence(scores)
            detected_artifacts = self._identify_text_artifacts(scores)

            return {
                "tamper_probability": float(min(tamper_probability, 1.0)),
                "confidence":         float(confidence),
                "detected_artifacts": detected_artifacts,
                "is_camera_photo":    False,
                "modality":           "text",
                "analysis_details":   {k: float(v) for k, v in scores.items()},
            }
        except Exception as e:
            print(f"⚠️  Text analysis error: {e}")
            return self._default_analysis("text")

    def _decode_text(self, file_bytes: bytes) -> str:
        """Try common encodings; strip PDF/binary noise."""
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                text = file_bytes.decode(enc, errors="ignore")
                # Strip obvious binary / PDF header junk
                text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]', ' ', text)
                text = re.sub(r'\s+', ' ', text)
                return text.strip()
            except Exception:
                continue
        return ""

    def _text_sentence_uniformity(self, text: str) -> float:
        """
        AI text tends to have very consistent sentence lengths.
        High variance in sentence length = more human-like.
        """
        try:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            lengths   = [len(s.split()) for s in sentences if len(s.split()) >= 3]
            if len(lengths) < 5:
                return 0.0

            cv = np.std(lengths) / (np.mean(lengths) + 1e-6)  # Coefficient of variation
            # Low CV = very uniform = suspicious
            if cv < 0.15:   return 0.9
            elif cv < 0.25: return 0.6
            elif cv < 0.35: return 0.3
            return 0.0
        except Exception:
            return 0.0

    def _text_vocabulary_richness(self, text: str) -> float:
        """
        Type-token ratio (TTR). AI text tends to have a moderate but too consistent TTR.
        Very low TTR = repetitive; very high for long docs = suspicious uniformity.
        """
        try:
            words  = re.findall(r'\b[a-z]{2,}\b', text.lower())
            if len(words) < 50:
                return 0.0

            unique = len(set(words))
            total  = len(words)
            ttr    = unique / total

            # For long documents, adjust expectation
            # Humans naturally decrease TTR with length (Zipf)
            expected_ttr = 1.0 / math.log(total + 1)

            ratio = ttr / (expected_ttr + 1e-6)

            # AI text often has a suspiciously moderate TTR
            # (not too repetitive, not too rich)
            score = 0.0
            if 0.8 < ratio < 1.4:  # Very close to "expected" = potentially AI
                score = 0.4
            if ttr < 0.10:  # Very low = too repetitive
                score = 0.6
            return min(score, 1.0)
        except Exception:
            return 0.0

    def _text_punctuation_pattern(self, text: str) -> float:
        """
        AI text overuses em-dashes, semicolons, colons, and certain list patterns.
        It also tends to use unnaturally balanced comma usage.
        """
        try:
            words = len(text.split())
            if words < 20:
                return 0.0

            em_dash_rate  = text.count("—") / words
            semicolon_rate = text.count(";") / words
            colon_rate    = text.count(":") / words

            # AI characteristic: heavy em-dash and semicolon usage
            score = 0.0
            if em_dash_rate   > 0.02: score += 0.35
            if semicolon_rate > 0.01: score += 0.25
            if colon_rate     > 0.03: score += 0.20

            # Unnaturally low exclamation / question mark usage
            excl_rate = text.count("!") / words
            ques_rate = text.count("?") / words
            if excl_rate < 0.001 and ques_rate < 0.001:
                score += 0.2  # Too formal / flat

            return min(score, 1.0)
        except Exception:
            return 0.0

    def _text_burstiness(self, text: str) -> float:
        """
        Humans write in topic bursts (paragraphs with distinct styles).
        AI produces a flatter information distribution.
        Measured via entropy of paragraph lengths.
        """
        try:
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
            if len(paragraphs) < 3:
                return 0.0

            lengths = [len(p.split()) for p in paragraphs]
            mean_l  = np.mean(lengths)
            std_l   = np.std(lengths)

            # Low std relative to mean = flat / AI-like
            cv = std_l / (mean_l + 1e-6)
            if cv < 0.20:   return 0.8
            elif cv < 0.35: return 0.5
            elif cv < 0.50: return 0.2
            return 0.0
        except Exception:
            return 0.0

    def _text_ngram_repetition(self, text: str) -> float:
        """
        AI LLMs repeat phrases more than humans.
        Measure 4-gram overlap ratio.
        """
        try:
            words = re.findall(r'\b\w+\b', text.lower())
            if len(words) < 20:
                return 0.0

            n       = 4
            ngrams  = [tuple(words[i:i+n]) for i in range(len(words) - n + 1)]
            total   = len(ngrams)
            unique  = len(set(ngrams))

            repeat_ratio = 1.0 - (unique / total)

            if repeat_ratio > 0.40:   return 0.8
            elif repeat_ratio > 0.25: return 0.5
            elif repeat_ratio > 0.15: return 0.2
            return 0.0
        except Exception:
            return 0.0

    def _text_paragraph_uniformity(self, text: str) -> float:
        """
        AI text paragraphs are often very similar in length.
        Real human writing varies paragraph size more naturally.
        """
        try:
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if len(p.split()) > 5]
            if len(paragraphs) < 4:
                return 0.0

            lengths = [len(p.split()) for p in paragraphs]
            std     = np.std(lengths)
            mean    = np.mean(lengths)

            cv = std / (mean + 1e-6)
            if cv < 0.15:   return 0.9
            elif cv < 0.25: return 0.5
            return 0.0
        except Exception:
            return 0.0

    def _identify_text_artifacts(self, scores: Dict[str, float]) -> List[str]:
        artifacts = []
        if scores.get("sentence_uniformity", 0)  > 0.5: artifacts.append("uniform_sentence_lengths")
        if scores.get("vocabulary_richness", 0)  > 0.5: artifacts.append("atypical_vocabulary_distribution")
        if scores.get("punctuation_pattern", 0)  > 0.4: artifacts.append("ai_punctuation_signature")
        if scores.get("burstiness", 0)           > 0.5: artifacts.append("low_text_burstiness")
        if scores.get("ngram_repetition", 0)     > 0.5: artifacts.append("high_phrase_repetition")
        if scores.get("paragraph_uniformity", 0) > 0.5: artifacts.append("uniform_paragraph_structure")
        return artifacts

    # ═══════════════════════════════════════════
    #  SHARED UTILITIES
    # ═══════════════════════════════════════════

    def _byte_entropy(self, data: bytes) -> float:
        """Shannon entropy of raw bytes (0–8 bits)."""
        if not data:
            return 0.0
        counts = Counter(data)
        total  = len(data)
        return -sum((c / total) * math.log2(c / total) for c in counts.values())

    def _score_confidence(self, scores: Dict[str, float]) -> float:
        vals       = list(scores.values())
        std_dev    = np.std(vals)
        mean_score = np.mean(vals)

        if std_dev < 0.15:   confidence = 0.85
        elif std_dev < 0.25: confidence = 0.70
        elif std_dev < 0.35: confidence = 0.55
        else:                 confidence = 0.40

        if mean_score > 0.75 or mean_score < 0.15:
            confidence = min(confidence + 0.10, 1.0)
        return confidence

    def _analyze_generic(self, file_bytes: bytes) -> Dict:
        return {
            "tamper_probability": 0.05,
            "confidence":         0.50,
            "detected_artifacts": [],
            "is_camera_photo":    False,
            "modality":           "generic",
            "analysis_details": {
                "file_size":    len(file_bytes),
                "byte_entropy": self._byte_entropy(file_bytes),
            },
        }

    def _default_analysis(self, modality: str = "unknown") -> Dict:
        return {
            "tamper_probability": 0.0,
            "confidence":         0.0,
            "detected_artifacts": [],
            "is_camera_photo":    False,
            "modality":           modality,
            "analysis_details":   {},
        }


# Backward-compatibility alias
AITamperingDetector = EnhancedAITamperingDetector