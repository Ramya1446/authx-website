"""
Multi-Modal Dataset Generator for Authx Benchmark
Creates theft scenarios for video, audio, and text content
"""

import os
import shutil
from pathlib import Path
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range
import numpy as np
from moviepy.editor import VideoFileClip, vfx
from PIL import Image
import io

class MultiModalDatasetGenerator:
    """Generate benchmark datasets for video, audio, and text"""
    
    def __init__(self, originals_path: str, output_path: str, modality: str):
        self.originals_path = Path(originals_path)
        self.output_path = Path(output_path) / modality
        self.modality = modality
        self.output_path.mkdir(parents=True, exist_ok=True)
    
    def create_full_dataset(self):
        """Generate complete dataset for the modality"""
        print("="*60)
        print(f"Creating {self.modality.upper()} Benchmark Dataset")
        print("="*60)
        
        self._create_directories()
        
        print("\n[1/5] Copying originals...")
        self._copy_originals()
        
        print("[2/5] Generating exact copies...")
        self._generate_exact_copies()
        
        print("[3/5] Generating minor edits...")
        self._generate_minor_edits()
        
        print("[4/5] Generating moderate edits...")
        self._generate_moderate_edits()
        
        print("[5/5] Generating heavy edits...")
        self._generate_heavy_edits()
        
        print(f"\n✅ {self.modality.title()} dataset creation complete!")
    
    def _create_directories(self):
        """Create directory structure"""
        dirs = [
            'originals',
            'theft_attempts/exact_copies',
            'theft_attempts/minor_edits',
            'theft_attempts/moderate_edits',
            'theft_attempts/heavy_edits',
            'legitimate_different'
        ]
        
        for dir_name in dirs:
            (self.output_path / dir_name).mkdir(parents=True, exist_ok=True)
    
    def _copy_originals(self):
        """Copy original files"""
        count = 0
        extensions = self._get_extensions()
        
        print(f"  Looking for files with extensions: {extensions}")
        print(f"  In directory: {self.originals_path}")
        
        for file_path in self.originals_path.glob('*'):
            print(f"  Found file: {file_path.name} (extension: {file_path.suffix.lower()})")
            if file_path.suffix.lower() in extensions:
                dest = self.output_path / 'originals' / file_path.name
                shutil.copy(file_path, dest)
                print(f"    ✓ Copied to {dest}")
                count += 1
            else:
                print(f"    ✗ Skipped (not in allowed extensions)")
        
        print(f"  ✓ Copied {count} originals")
    
    def _generate_exact_copies(self):
        """Generate exact duplicates"""
        count = 0
        for file_path in (self.output_path / 'originals').glob('*'):
            try:
                shutil.copy(
                    file_path,
                    self.output_path / 'theft_attempts' / 'exact_copies' / 
                    f"{file_path.stem}_stolen{file_path.suffix}"
                )
                count += 1
            except Exception as e:
                print(f"  Error: {e}")
        print(f"  ✓ Created {count} exact copies")
    
    def _generate_minor_edits(self):
        """Generate minor edits based on modality"""
        if self.modality == 'video':
            self._generate_video_minor_edits()
        elif self.modality == 'audio':
            self._generate_audio_minor_edits()
        elif self.modality == 'text':
            self._generate_text_minor_edits()
    
    def _generate_moderate_edits(self):
        """Generate moderate edits based on modality"""
        if self.modality == 'video':
            self._generate_video_moderate_edits()
        elif self.modality == 'audio':
            self._generate_audio_moderate_edits()
        elif self.modality == 'text':
            self._generate_text_moderate_edits()
    
    def _generate_heavy_edits(self):
        """Generate heavy edits based on modality"""
        if self.modality == 'video':
            self._generate_video_heavy_edits()
        elif self.modality == 'audio':
            self._generate_audio_heavy_edits()
        elif self.modality == 'text':
            self._generate_text_heavy_edits()
    
    # ==================== VIDEO MODIFICATIONS ====================
    
    def _generate_video_minor_edits(self):
        """Minor video edits: trim, brightness, speed"""
        count = 0
        
        video_files = list((self.output_path / 'originals').glob('*'))
        total = len(video_files)
        
        print(f"  Processing {total} videos (3 versions each)...")
        
        for idx, video_file in enumerate(video_files, 1):
            try:
                print(f"    [{idx}/{total}] Processing {video_file.name[:30]}...")
                
                clip = VideoFileClip(str(video_file))
                duration = clip.duration
                
                # Version 1: Trim 5% from start and end
                print(f"      - Creating trimmed version...")
                trimmed = clip.subclip(duration * 0.05, duration * 0.95)
                trimmed.write_videofile(
                    str(self.output_path / 'theft_attempts' / 'minor_edits' / 
                        f"{video_file.stem}_trimmed.mp4"),
                    logger=None,
                    verbose=False,
                    preset='ultrafast'
                )
                trimmed.close()
                print(f"      ✓ Trimmed")
                
                # Version 2: Brightness adjustment
                print(f"      - Creating brightness version...")
                bright = clip.fx(vfx.colorx, 1.2)
                bright.write_videofile(
                    str(self.output_path / 'theft_attempts' / 'minor_edits' / 
                        f"{video_file.stem}_bright.mp4"),
                    logger=None,
                    verbose=False,
                    preset='ultrafast'
                )
                bright.close()
                print(f"      ✓ Brightness adjusted")
                
                # Version 3: Speed change (1.1x)
                print(f"      - Creating speed version...")
                speed = clip.fx(vfx.speedx, 1.1)
                speed.write_videofile(
                    str(self.output_path / 'theft_attempts' / 'minor_edits' / 
                        f"{video_file.stem}_speed.mp4"),
                    logger=None,
                    verbose=False,
                    preset='ultrafast'
                )
                speed.close()
                print(f"      ✓ Speed changed")
                
                clip.close()
                count += 3
                print(f"    ✓ Completed {video_file.name[:30]} ({count}/{total*3} total)")
                
            except Exception as e:
                print(f"    ❌ Error processing {video_file.name}: {e}")
        
        print(f"  ✓ Created {count} minor video edits")
    
    def _generate_video_moderate_edits(self):
        """Moderate video edits: resize, crop, rotate"""
        count = 0
        
        video_files = list((self.output_path / 'originals').glob('*'))
        total = len(video_files)
        
        print(f"  Processing {total} videos (3 versions each)...")
        
        for idx, video_file in enumerate(video_files, 1):
            try:
                print(f"    [{idx}/{total}] Processing {video_file.name[:30]}...")
                
                clip = VideoFileClip(str(video_file))
                
                # Version 1: Resize to 720p
                print(f"      - Resizing...")
                resized = clip.resize(height=720)
                resized.write_videofile(
                    str(self.output_path / 'theft_attempts' / 'moderate_edits' / 
                        f"{video_file.stem}_resized.mp4"),
                    logger=None,
                    verbose=False,
                    preset='ultrafast'
                )
                resized.close()
                print(f"      ✓ Resized")
                
                # Version 2: Crop 10% from edges
                print(f"      - Cropping...")
                w, h = clip.size
                cropped = clip.crop(
                    x1=int(w*0.1), y1=int(h*0.1),
                    x2=int(w*0.9), y2=int(h*0.9)
                )
                cropped.write_videofile(
                    str(self.output_path / 'theft_attempts' / 'moderate_edits' / 
                        f"{video_file.stem}_cropped.mp4"),
                    logger=None,
                    verbose=False,
                    preset='ultrafast'
                )
                cropped.close()
                print(f"      ✓ Cropped")
                
                # Version 3: Mirror horizontally
                print(f"      - Mirroring...")
                mirrored = clip.fx(vfx.mirror_x)
                mirrored.write_videofile(
                    str(self.output_path / 'theft_attempts' / 'moderate_edits' / 
                        f"{video_file.stem}_mirrored.mp4"),
                    logger=None,
                    verbose=False,
                    preset='ultrafast'
                )
                mirrored.close()
                print(f"      ✓ Mirrored")
                
                clip.close()
                count += 3
                print(f"    ✓ Completed {video_file.name[:30]} ({count}/{total*3} total)")
                
            except Exception as e:
                print(f"    ❌ Error processing {video_file.name}: {e}")
        
        print(f"  ✓ Created {count} moderate video edits")
    
    def _generate_video_heavy_edits(self):
        """Heavy video edits: compression, effects"""
        count = 0
        
        video_files = list((self.output_path / 'originals').glob('*'))
        total = len(video_files)
        
        print(f"  Processing {total} videos (2 versions each)...")
        
        for idx, video_file in enumerate(video_files, 1):
            try:
                print(f"    [{idx}/{total}] Processing {video_file.name[:30]}...")
                
                clip = VideoFileClip(str(video_file))
                
                # Version 1: Heavy compression (low bitrate)
                print(f"      - Compressing (low bitrate)...")
                clip.write_videofile(
                    str(self.output_path / 'theft_attempts' / 'heavy_edits' / 
                        f"{video_file.stem}_compressed.mp4"),
                    bitrate="500k",
                    logger=None,
                    verbose=False,
                    preset='ultrafast'
                )
                print(f"      ✓ Compressed")
                
                # Version 2: Black & white
                print(f"      - Converting to B&W...")
                bw = clip.fx(vfx.blackwhite)
                bw.write_videofile(
                    str(self.output_path / 'theft_attempts' / 'heavy_edits' / 
                        f"{video_file.stem}_bw.mp4"),
                    logger=None,
                    verbose=False,
                    preset='ultrafast'
                )
                bw.close()
                print(f"      ✓ B&W converted")
                
                clip.close()
                count += 2
                print(f"    ✓ Completed {video_file.name[:30]} ({count}/{total*2} total)")
                
            except Exception as e:
                print(f"    ❌ Error processing {video_file.name}: {e}")
        
        print(f"  ✓ Created {count} heavy video edits")
    
    # ==================== AUDIO MODIFICATIONS ====================
    
    def _generate_audio_minor_edits(self):
        """Minor audio edits: trim, volume, pitch"""
        count = 0
        
        for audio_file in (self.output_path / 'originals').glob('*'):
            try:
                audio = AudioSegment.from_file(str(audio_file))
                duration = len(audio)
                
                # Version 1: Trim 5% from start and end
                trimmed = audio[int(duration*0.05):int(duration*0.95)]
                trimmed.export(
                    self.output_path / 'theft_attempts' / 'minor_edits' / 
                    f"{audio_file.stem}_trimmed.mp3",
                    format="mp3"
                )
                
                # Version 2: Volume adjustment (+3dB)
                louder = audio + 3
                louder.export(
                    self.output_path / 'theft_attempts' / 'minor_edits' / 
                    f"{audio_file.stem}_louder.mp3",
                    format="mp3"
                )
                
                # Version 3: Fade in/out
                faded = audio.fade_in(1000).fade_out(1000)
                faded.export(
                    self.output_path / 'theft_attempts' / 'minor_edits' / 
                    f"{audio_file.stem}_faded.mp3",
                    format="mp3"
                )
                
                count += 3
                
            except Exception as e:
                print(f"  Error processing {audio_file.name}: {e}")
        
        print(f"  ✓ Created {count} minor audio edits")
    
    def _generate_audio_moderate_edits(self):
        """Moderate audio edits: speed, effects"""
        count = 0
        
        for audio_file in (self.output_path / 'originals').glob('*'):
            try:
                audio = AudioSegment.from_file(str(audio_file))
                
                # Version 1: Speed up 1.1x (pitch change)
                faster = audio.speedup(playback_speed=1.1)
                faster.export(
                    self.output_path / 'theft_attempts' / 'moderate_edits' / 
                    f"{audio_file.stem}_faster.mp3",
                    format="mp3"
                )
                
                # Version 2: Normalize
                normalized = normalize(audio)
                normalized.export(
                    self.output_path / 'theft_attempts' / 'moderate_edits' / 
                    f"{audio_file.stem}_normalized.mp3",
                    format="mp3"
                )
                
                # Version 3: Compression
                compressed = compress_dynamic_range(audio)
                compressed.export(
                    self.output_path / 'theft_attempts' / 'moderate_edits' / 
                    f"{audio_file.stem}_compressed.mp3",
                    format="mp3"
                )
                
                count += 3
                
            except Exception as e:
                print(f"  Error processing {audio_file.name}: {e}")
        
        print(f"  ✓ Created {count} moderate audio edits")
    
    def _generate_audio_heavy_edits(self):
        """Heavy audio edits: extreme compression, format change"""
        count = 0
        
        for audio_file in (self.output_path / 'originals').glob('*'):
            try:
                audio = AudioSegment.from_file(str(audio_file))
                
                # Version 1: Low bitrate compression
                audio.export(
                    self.output_path / 'theft_attempts' / 'heavy_edits' / 
                    f"{audio_file.stem}_lowquality.mp3",
                    format="mp3",
                    bitrate="64k"
                )
                
                # Version 2: Reverse
                reversed_audio = audio.reverse()
                reversed_audio.export(
                    self.output_path / 'theft_attempts' / 'heavy_edits' / 
                    f"{audio_file.stem}_reversed.mp3",
                    format="mp3"
                )
                
                count += 2
                
            except Exception as e:
                print(f"  Error processing {audio_file.name}: {e}")
        
        print(f"  ✓ Created {count} heavy audio edits")
    
    # ==================== TEXT MODIFICATIONS ====================
    
    def _read_text_file(self, file_path: Path) -> str:
        """Read text from file (supports txt, md, pdf)"""
        if file_path.suffix.lower() == '.pdf':
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ''
                    for page in reader.pages:
                        text += page.extract_text()
                    return text
            except Exception as e:
                print(f"  Error reading PDF {file_path.name}: {e}")
                return ''
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    
    def _write_text_file(self, file_path: Path, text: str):
        """Write text to file (always as .txt for modified versions)"""
        # Convert output to .txt for simplicity
        output_path = file_path.with_suffix('.txt')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
    
    def _generate_text_minor_edits(self):
        """Minor text edits: punctuation, whitespace"""
        count = 0
        
        for text_file in (self.output_path / 'originals').glob('*'):
            try:
                text = self._read_text_file(text_file)
                if not text:
                    continue
                
                # Version 1: Add extra spaces
                spaced = text.replace('.', ' . ').replace(',', ' , ')
                self._write_text_file(
                    self.output_path / 'theft_attempts' / 'minor_edits' / 
                    f"{text_file.stem}_spaced.txt",
                    spaced
                )
                
                # Version 2: Change line endings
                with open(
                    self.output_path / 'theft_attempts' / 'minor_edits' / 
                    f"{text_file.stem}_lineends.txt", 'w', encoding='utf-8', newline='\r\n'
                ) as f:
                    f.write(text)
                
                # Version 3: Add/remove trailing whitespace
                whitespaced = '\n'.join([line.rstrip() + '  ' for line in text.split('\n')])
                self._write_text_file(
                    self.output_path / 'theft_attempts' / 'minor_edits' / 
                    f"{text_file.stem}_whitespace.txt",
                    whitespaced
                )
                
                count += 3
                
            except Exception as e:
                print(f"  Error processing {text_file.name}: {e}")
        
        print(f"  ✓ Created {count} minor text edits")
    
    def _generate_text_moderate_edits(self):
        """Moderate text edits: synonyms, sentence reordering"""
        count = 0
        
        # Simple synonym replacement dict
        synonyms = {
            'good': 'great', 'bad': 'poor', 'big': 'large', 'small': 'tiny',
            'fast': 'quick', 'slow': 'sluggish', 'happy': 'joyful', 'sad': 'unhappy',
            'important': 'significant', 'easy': 'simple', 'hard': 'difficult'
        }
        
        for text_file in (self.output_path / 'originals').glob('*'):
            try:
                text = self._read_text_file(text_file)
                if not text:
                    continue
                
                # Version 1: Synonym replacement (10% of words)
                words = text.split()
                modified_words = []
                for word in words:
                    word_lower = word.lower().strip('.,!?')
                    if word_lower in synonyms and np.random.random() < 0.1:
                        modified_words.append(word.replace(word_lower, synonyms[word_lower]))
                    else:
                        modified_words.append(word)
                
                synonym_text = ' '.join(modified_words)
                self._write_text_file(
                    self.output_path / 'theft_attempts' / 'moderate_edits' / 
                    f"{text_file.stem}_synonyms.txt",
                    synonym_text
                )
                
                # Version 2: Remove every 10th word
                every_10th_removed = ' '.join([w for i, w in enumerate(words) if i % 10 != 0])
                self._write_text_file(
                    self.output_path / 'theft_attempts' / 'moderate_edits' / 
                    f"{text_file.stem}_removed.txt",
                    every_10th_removed
                )
                
                # Version 3: Shuffle sentences
                sentences = text.split('. ')
                if len(sentences) > 3:
                    np.random.shuffle(sentences)
                    shuffled = '. '.join(sentences)
                    self._write_text_file(
                        self.output_path / 'theft_attempts' / 'moderate_edits' / 
                        f"{text_file.stem}_shuffled.txt",
                        shuffled
                    )
                
                count += 3
                
            except Exception as e:
                print(f"  Error processing {text_file.name}: {e}")
        
        print(f"  ✓ Created {count} moderate text edits")
    
    def _generate_text_heavy_edits(self):
        """Heavy text edits: paraphrasing, format change"""
        count = 0
        
        for text_file in (self.output_path / 'originals').glob('*'):
            try:
                text = self._read_text_file(text_file)
                if not text:
                    continue
                
                # Version 1: Remove all punctuation
                import string
                no_punct = text.translate(str.maketrans('', '', string.punctuation))
                self._write_text_file(
                    self.output_path / 'theft_attempts' / 'heavy_edits' / 
                    f"{text_file.stem}_nopunct.txt",
                    no_punct
                )
                
                # Version 2: All lowercase
                lowercase = text.lower()
                self._write_text_file(
                    self.output_path / 'theft_attempts' / 'heavy_edits' / 
                    f"{text_file.stem}_lowercase.txt",
                    lowercase
                )
                
                # Version 3: Extract first 50% of content
                half = text[:len(text)//2]
                self._write_text_file(
                    self.output_path / 'theft_attempts' / 'heavy_edits' / 
                    f"{text_file.stem}_half.txt",
                    half
                )
                
                count += 3
                
            except Exception as e:
                print(f"  Error processing {text_file.name}: {e}")
        
        print(f"  ✓ Created {count} heavy text edits")
    
    def _get_extensions(self):
        """Get file extensions for modality"""
        extensions = {
            'video': ['.mp4', '.mov', '.avi', '.mkv'],
            'audio': ['.mp3', '.wav', '.m4a', '.flac'],
            'text': ['.txt', '.md', '.pdf']  # Added .pdf
        }
        return extensions.get(self.modality, [])


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("="*60)
        print("Multi-Modal Dataset Generator")
        print("="*60)
        print("\nUsage:")
        print("  python multimodal_dataset_gen.py <modality> <originals_folder> <output_folder>")
        print("\nModalities: video, audio, text")
        print("\nExample:")
        print("  python multimodal_dataset_gen.py video ./my_videos ./benchmark_dataset")
        print("  python multimodal_dataset_gen.py audio ./my_audio ./benchmark_dataset")
        print("  python multimodal_dataset_gen.py text ./my_documents ./benchmark_dataset")
        print("\nNote: Text modality supports .txt, .md, and .pdf files")
        print("\n" + "="*60)
        sys.exit(1)
    
    modality = sys.argv[1]
    originals_path = sys.argv[2]
    output_path = sys.argv[3]
    
    if modality not in ['video', 'audio', 'text']:
        print(f"❌ Invalid modality: {modality}")
        print("   Must be: video, audio, or text")
        sys.exit(1)
    
    generator = MultiModalDatasetGenerator(originals_path, output_path, modality)
    generator.create_full_dataset()
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    print(f"1. Review dataset at: {Path(output_path) / modality}")
    print(f"2. Add legitimate different content to: {Path(output_path) / modality / 'legitimate_different'}")
    print(f"3. Run benchmark: python multimodal_benchmark.py {output_path}")