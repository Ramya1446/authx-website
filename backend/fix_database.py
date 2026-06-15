import hashlib
import numpy as np
import wave
import struct
from typing import Optional
from collections import Counter
import re

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


def compute_video_fingerprint(file_bytes: bytes) -> Optional[str]:
    """
    Improved video fingerprinting using structural and temporal features
    More robust to edits like brightness, trimming, compression
    """
    try:
        fingerprint_parts = []
        
        # 1. File structure signature (robust to minor edits)
        file_size = len(file_bytes)
        
        # Sample strategic points (beginning, middle, end)
        sample_points = [
            0,
            file_size // 4,
            file_size // 2,
            3 * file_size // 4,
            max(0, file_size - 10000)
        ]
        
        # 2. Byte distribution histogram (robust to compression)
        byte_hist = Counter(file_bytes[::max(1, len(file_bytes)//10000)])
        
        # Get top 10 most common byte values
        top_bytes = [b for b, _ in byte_hist.most_common(10)]
        fingerprint_parts.extend([f'{b:02x}' for b in top_bytes])
        
        # 3. Structural patterns at key points
        for point in sample_points:
            chunk = file_bytes[point:point+4096]
            
            # Compute entropy (information density)
            if len(chunk) > 0:
                byte_counts = Counter(chunk)
                entropy = -sum((count/len(chunk)) * np.log2(count/len(chunk) + 1e-9) 
                              for count in byte_counts.values())
                fingerprint_parts.append(f'{int(entropy * 100):04x}')
            
            # Pattern hash
            if len(chunk) >= 1024:
                pattern_hash = hashlib.md5(chunk[::4]).hexdigest()[:4]
                fingerprint_parts.append(pattern_hash)
        
        # 4. Byte sequence patterns (n-grams)
        stride = max(1, len(file_bytes) // 1000)
        bigrams = []
        for i in range(0, len(file_bytes) - stride, len(file_bytes) // 100):
            bigram = (file_bytes[i], file_bytes[i + stride])
            bigrams.append(bigram)
        
        # Hash most common patterns
        bigram_counts = Counter(bigrams)
        for bigram, _ in bigram_counts.most_common(5):
            fingerprint_parts.append(f'{bigram[0]:02x}{bigram[1]:02x}')
        
        return ''.join(fingerprint_parts[:96])  # Fixed length
        
    except Exception as e:
        print(f"Error computing video fingerprint: {e}")
        return None


def compute_text_fingerprint(file_bytes: bytes) -> Optional[str]:
    """
    Improved text fingerprinting using semantic shingling
    More robust to formatting, minor edits, reordering
    """
    try:
        # Try to decode as text
        text = file_bytes.decode('utf-8', errors='ignore')
        
        # Remove all whitespace and normalize
        text = ' '.join(text.split()).lower()
        
        # Remove punctuation but keep structure
        text_no_punct = re.sub(r'[^\w\s]', '', text)
        
        fingerprint_parts = []
        
        # 1. Word-level n-grams (robust to minor edits)
        words = text_no_punct.split()
        
        # 3-grams of words
        word_trigrams = set()
        for i in range(len(words) - 2):
            trigram = ' '.join(words[i:i+3])
            word_trigrams.add(trigram)
        
        # Hash most common trigrams
        trigram_hashes = sorted([hash(t) % (2**32) for t in word_trigrams])[:32]
        fingerprint_parts.extend([f'{h:08x}' for h in trigram_hashes])
        
        # 2. Character n-grams (robust to word changes)
        char_4grams = set()
        for i in range(len(text_no_punct) - 3):
            fourgram = text_no_punct[i:i+4]
            if fourgram.strip():  # Skip whitespace-only
                char_4grams.add(fourgram)
        
        char_hashes = sorted([hash(c) % (2**32) for c in char_4grams])[:32]
        fingerprint_parts.extend([f'{h:08x}' for h in char_hashes])
        
        # 3. Word frequency signature (robust to reordering)
        word_freq = Counter(words)
        top_words = [w for w, _ in word_freq.most_common(20)]
        word_sig = ''.join(sorted(top_words))
        word_sig_hash = hashlib.md5(word_sig.encode()).hexdigest()[:16]
        fingerprint_parts.append(word_sig_hash)
        
        # 4. Sentence structure pattern (robust to minor edits)
        sentences = re.split(r'[.!?]+', text)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        
        # Quantize lengths into bins
        length_pattern = [min(l // 5, 15) for l in sentence_lengths[:20]]
        length_hash = hashlib.md5(str(length_pattern).encode()).hexdigest()[:8]
        fingerprint_parts.append(length_hash)
        
        return ''.join(fingerprint_parts[:128])  # Longer for text
        
    except Exception as e:
        print(f"Error computing text fingerprint: {e}")
        return None


def fuzzy_string_similarity(str1: str, str2: str, window_size: int = 8) -> float:
    """
    Improved similarity using sliding window comparison
    More robust than character-by-character comparison
    """
    if not str1 or not str2:
        return 0.0
    
    if len(str1) < window_size or len(str2) < window_size:
        # Fall back to simple similarity for short strings
        matches = sum(c1 == c2 for c1, c2 in zip(str1, str2))
        return matches / max(len(str1), len(str2))
    
    # Extract sliding windows
    windows1 = set(str1[i:i+window_size] for i in range(len(str1) - window_size + 1))
    windows2 = set(str2[i:i+window_size] for i in range(len(str2) - window_size + 1))
    
    # Jaccard similarity
    intersection = len(windows1 & windows2)
    union = len(windows1 | windows2)
    
    return intersection / union if union > 0 else 0.0


def calculate_multi_similarity(new_hashes: dict, stored_hashes: dict, content_type: str) -> dict:
    """
    IMPROVED similarity calculation with better thresholds
    """
    distances = {}
    
    if content_type.startswith("image"):
        # Use perceptual hashing for images (existing code is good)
        if new_hashes["phash"] and stored_hashes["phash"]:
            distances["phash"] = hamming_distance(new_hashes["phash"], stored_hashes["phash"])
        
        if new_hashes["dhash"] and stored_hashes["dhash"]:
            distances["dhash"] = hamming_distance(new_hashes["dhash"], stored_hashes["dhash"])
        
        if new_hashes["ahash"] and stored_hashes["ahash"]:
            distances["ahash"] = hamming_distance(new_hashes["ahash"], stored_hashes["ahash"])
    
    elif content_type.startswith("audio"):
        # Use IMPROVED fuzzy matching
        if new_hashes["audio_fingerprint"] and stored_hashes["audio_fingerprint"]:
            similarity = fuzzy_string_similarity(
                new_hashes["audio_fingerprint"], 
                stored_hashes["audio_fingerprint"],
                window_size=8
            )
            # Convert to distance (0-64 scale)
            distances["audio"] = int((1.0 - similarity) * 64)
    
    elif content_type.startswith("video"):
        # Use IMPROVED fuzzy matching
        if new_hashes["video_fingerprint"] and stored_hashes["video_fingerprint"]:
            similarity = fuzzy_string_similarity(
                new_hashes["video_fingerprint"], 
                stored_hashes["video_fingerprint"],
                window_size=12
            )
            distances["video"] = int((1.0 - similarity) * 64)
    
    elif content_type.startswith("text") or "pdf" in content_type.lower():
        # Use IMPROVED fuzzy matching
        if new_hashes["text_fingerprint"] and stored_hashes["text_fingerprint"]:
            similarity = fuzzy_string_similarity(
                new_hashes["text_fingerprint"], 
                stored_hashes["text_fingerprint"],
                window_size=16
            )
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