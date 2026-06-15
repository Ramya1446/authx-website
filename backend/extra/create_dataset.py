"""
Helper script to create benchmark dataset from original images
Automatically generates theft scenarios with various modifications
"""

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
import os
from pathlib import Path
import shutil

class DatasetCreator:
    """
    Creates benchmark dataset from original images
    Simulates various theft/modification scenarios
    """
    
    def __init__(self, originals_path: str, output_path: str):
        self.originals_path = Path(originals_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
    
    def create_full_dataset(self):
        """Generate complete benchmark dataset"""
        print("="*60)
        print("Creating Benchmark Dataset for Authx")
        print("="*60)
        
        # Create directory structure
        self._create_directories()
        
        # Copy originals
        print("\n[1/6] Copying original images...")
        self._copy_originals()
        
        # Generate theft attempts
        print("[2/6] Generating exact copies (theft attempt)...")
        self._generate_exact_copies()
        
        print("[3/6] Generating minor edits (brightness, crop)...")
        self._generate_minor_edits()
        
        print("[4/6] Generating moderate edits (filters, resize)...")
        self._generate_moderate_edits()
        
        print("[5/6] Generating heavy AI-style edits...")
        self._generate_heavy_edits()
        
        print("[6/6] Generating extreme edits...")
        self._generate_extreme_edits()
        
        print("\n✅ Dataset creation complete!")
        print(f"📁 Output: {self.output_path}")
        print("\nRun benchmark with:")
        print(f"  python benchmark_theft.py {self.output_path}")
    
    def _create_directories(self):
        """Create directory structure"""
        dirs = [
            'originals',
            'theft_attempts/exact_copies',
            'theft_attempts/minor_edits',
            'theft_attempts/moderate_edits',
            'theft_attempts/heavy_ai_edits',
            'theft_attempts/extreme_edits',
            'legitimate_different_content',
            'edge_cases/collages',
            'edge_cases/partial_crops',
            'edge_cases/watermark_removed'
        ]
        
        for dir_name in dirs:
            (self.output_path / dir_name).mkdir(parents=True, exist_ok=True)
    
    def _copy_originals(self):
        """Copy original images"""
        count = 0
        for img_file in self.originals_path.glob('*'):
            if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                shutil.copy(img_file, self.output_path / 'originals' / img_file.name)
                count += 1
        print(f"  ✓ Copied {count} original images")
    
    def _generate_exact_copies(self):
        """Generate exact duplicates (thief's lazy attempt)"""
        count = 0
        for img_file in (self.output_path / 'originals').glob('*'):
            try:
                shutil.copy(
                    img_file,
                    self.output_path / 'theft_attempts' / 'exact_copies' / f"{img_file.stem}_stolen{img_file.suffix}"
                )
                count += 1
            except Exception as e:
                print(f"  Error: {e}")
        print(f"  ✓ Created {count} exact copies")
    
    def _generate_minor_edits(self):
        """Minor edits: brightness, contrast, slight crop"""
        count = 0
        for img_file in (self.output_path / 'originals').glob('*'):
            try:
                img = Image.open(img_file)
                
                # Version 1: Brightness adjustment
                enhancer = ImageEnhance.Brightness(img)
                img_bright = enhancer.enhance(1.2)
                img_bright.save(
                    self.output_path / 'theft_attempts' / 'minor_edits' / f"{img_file.stem}_brightness{img_file.suffix}",
                    quality=95
                )
                
                # Version 2: Contrast adjustment
                enhancer = ImageEnhance.Contrast(img)
                img_contrast = enhancer.enhance(1.15)
                img_contrast.save(
                    self.output_path / 'theft_attempts' / 'minor_edits' / f"{img_file.stem}_contrast{img_file.suffix}",
                    quality=95
                )
                
                # Version 3: Slight crop (5%)
                width, height = img.size
                crop_margin = int(width * 0.05)
                img_crop = img.crop((crop_margin, crop_margin, width-crop_margin, height-crop_margin))
                img_crop = img_crop.resize((width, height), Image.LANCZOS)
                img_crop.save(
                    self.output_path / 'theft_attempts' / 'minor_edits' / f"{img_file.stem}_crop{img_file.suffix}",
                    quality=95
                )
                
                count += 3
            except Exception as e:
                print(f"  Error processing {img_file}: {e}")
        
        print(f"  ✓ Created {count} minor edits")
    
    def _generate_moderate_edits(self):
        """Moderate edits: filters, resize, rotation, text overlay"""
        count = 0
        for img_file in (self.output_path / 'originals').glob('*'):
            try:
                img = Image.open(img_file)
                
                # Version 1: Blur filter
                img_blur = img.filter(ImageFilter.GaussianBlur(radius=2))
                img_blur.save(
                    self.output_path / 'theft_attempts' / 'moderate_edits' / f"{img_file.stem}_blur{img_file.suffix}",
                    quality=90
                )
                
                # Version 2: Sharpen
                img_sharp = img.filter(ImageFilter.SHARPEN)
                img_sharp.save(
                    self.output_path / 'theft_attempts' / 'moderate_edits' / f"{img_file.stem}_sharpen{img_file.suffix}",
                    quality=90
                )
                
                # Version 3: Resize then back
                width, height = img.size
                img_resize = img.resize((width//2, height//2), Image.LANCZOS)
                img_resize = img_resize.resize((width, height), Image.LANCZOS)
                img_resize.save(
                    self.output_path / 'theft_attempts' / 'moderate_edits' / f"{img_file.stem}_resize{img_file.suffix}",
                    quality=85
                )
                
                # Version 4: Add small text watermark (thief's mark)
                img_text = img.copy()
                draw = ImageDraw.Draw(img_text)
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    font = ImageFont.load_default()
                draw.text((10, 10), "Stolen", fill=(255, 255, 255, 128), font=font)
                img_text.save(
                    self.output_path / 'theft_attempts' / 'moderate_edits' / f"{img_file.stem}_watermark{img_file.suffix}",
                    quality=90
                )
                
                # Version 5: Saturation change
                enhancer = ImageEnhance.Color(img)
                img_sat = enhancer.enhance(1.3)
                img_sat.save(
                    self.output_path / 'theft_attempts' / 'moderate_edits' / f"{img_file.stem}_saturation{img_file.suffix}",
                    quality=90
                )
                
                count += 5
            except Exception as e:
                print(f"  Error processing {img_file}: {e}")
        
        print(f"  ✓ Created {count} moderate edits")
    
    def _generate_heavy_edits(self):
        """Heavy edits: aggressive filters, heavy compression, format change"""
        count = 0
        for img_file in (self.output_path / 'originals').glob('*'):
            try:
                img = Image.open(img_file)
                
                # Version 1: Heavy JPEG compression
                img.save(
                    self.output_path / 'theft_attempts' / 'heavy_ai_edits' / f"{img_file.stem}_compressed.jpg",
                    quality=60
                )
                
                # Version 2: Edge enhance (simulate AI filter)
                img_edge = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
                img_edge.save(
                    self.output_path / 'theft_attempts' / 'heavy_ai_edits' / f"{img_file.stem}_edges{img_file.suffix}",
                    quality=85
                )
                
                # Version 3: Posterize (color reduction)
                # Convert to RGB if not already
                if img.mode != 'RGB':
                    img_rgb = img.convert('RGB')
                else:
                    img_rgb = img
                
                # Posterize using PIL
                from PIL import ImageOps
                img_poster = ImageOps.posterize(img_rgb, 4)
                img_poster.save(
                    self.output_path / 'theft_attempts' / 'heavy_ai_edits' / f"{img_file.stem}_posterize{img_file.suffix}",
                    quality=85
                )
                
                # Version 4: Gaussian noise (simulate AI artifact)
                img_array = np.array(img_rgb)
                noise = np.random.normal(0, 10, img_array.shape).astype(np.uint8)
                img_noisy = Image.fromarray(np.clip(img_array + noise, 0, 255).astype(np.uint8))
                img_noisy.save(
                    self.output_path / 'theft_attempts' / 'heavy_ai_edits' / f"{img_file.stem}_noise{img_file.suffix}",
                    quality=85
                )
                
                count += 4
            except Exception as e:
                print(f"  Error processing {img_file}: {e}")
        
        print(f"  ✓ Created {count} heavy edits")
    
    def _generate_extreme_edits(self):
        """Extreme edits: may or may not be detected"""
        count = 0
        for img_file in (self.output_path / 'originals').glob('*'):
            try:
                img = Image.open(img_file)
                
                # Version 1: Flip horizontal
                img_flip = img.transpose(Image.FLIP_LEFT_RIGHT)
                img_flip.save(
                    self.output_path / 'theft_attempts' / 'extreme_edits' / f"{img_file.stem}_flip{img_file.suffix}",
                    quality=90
                )
                
                # Version 2: Rotate 90 degrees
                img_rotate = img.rotate(90, expand=True)
                img_rotate.save(
                    self.output_path / 'theft_attempts' / 'extreme_edits' / f"{img_file.stem}_rotate{img_file.suffix}",
                    quality=90
                )
                
                # Version 3: Grayscale conversion
                img_gray = img.convert('L').convert('RGB')
                img_gray.save(
                    self.output_path / 'theft_attempts' / 'extreme_edits' / f"{img_file.stem}_grayscale{img_file.suffix}",
                    quality=90
                )
                
                count += 3
            except Exception as e:
                print(f"  Error processing {img_file}: {e}")
        
        print(f"  ✓ Created {count} extreme edits")
    
    def add_legitimate_content(self, legitimate_images_path: str):
        """
        Add unrelated legitimate content (for false positive testing)
        These are completely different images that should NOT be blocked
        """
        legitimate_path = Path(legitimate_images_path)
        count = 0
        
        for img_file in legitimate_path.glob('*'):
            if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                shutil.copy(
                    img_file,
                    self.output_path / 'legitimate_different_content' / img_file.name
                )
                count += 1
        
        print(f"\n✓ Added {count} legitimate different images")


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("="*60)
        print("Authx Dataset Creator")
        print("="*60)
        print("\nUsage:")
        print("  python create_dataset.py <originals_folder> <output_folder>")
        print("\nExample:")
        print("  python create_dataset.py ./my_images ./benchmark_dataset")
        print("\nOptional: Add legitimate content for false positive testing:")
        print("  python create_dataset.py ./my_images ./benchmark_dataset --legitimate ./other_images")
        print("\n" + "="*60)
        sys.exit(1)
    
    originals_path = sys.argv[1]
    output_path = sys.argv[2]
    
    creator = DatasetCreator(originals_path, output_path)
    creator.create_full_dataset()
    
    # Add legitimate content if provided
    if len(sys.argv) > 4 and sys.argv[3] == '--legitimate':
        legitimate_path = sys.argv[4]
        creator.add_legitimate_content(legitimate_path)
    
    print("\n" + "="*60)
    print("Next Steps:")
    print("="*60)
    print(f"1. Review dataset at: {output_path}")
    print(f"2. Run benchmark: python benchmark_theft.py {output_path}")
    print("3. Results will be saved as:")
    print("   - theft_detection_results.json")
    print("   - detection_rates.png")
    print("   - processing_times.png")
    print("   - performance_summary.png")
    print("   - table_detection_performance.tex")
    print("   - table_performance.tex")