"""
Script to fix high false positive rate by adding diverse legitimate content
"""

import requests
from pathlib import Path
import time

def download_diverse_images(output_folder: Path, count: int = 50):
    """
    Download diverse legitimate images from free sources
    These should be completely different from your originals
    """
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Unsplash API - Random photos (completely different)
    print(f"Downloading {count} diverse images from Unsplash...")
    
    categories = [
        'nature', 'technology', 'food', 'architecture', 'abstract',
        'animals', 'business', 'fashion', 'health', 'music',
        'sports', 'travel', 'art', 'cars', 'flowers'
    ]
    
    downloaded = 0
    for i in range(count):
        category = categories[i % len(categories)]
        
        try:
            # Unsplash Source API (no API key needed)
            url = f"https://source.unsplash.com/800x600/?{category},{i}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                filename = output_folder / f"legitimate_{category}_{i:03d}.jpg"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                downloaded += 1
                print(f"  [{downloaded}/{count}] Downloaded: {filename.name}")
            
            time.sleep(0.5)  # Be nice to the API
            
        except Exception as e:
            print(f"  Error downloading image {i}: {e}")
    
    print(f"\n✅ Downloaded {downloaded} legitimate images")
    return downloaded

def analyze_current_fps(dataset_path: Path):
    """
    Analyze current false positives to understand the issue
    """
    print("\n" + "="*60)
    print("FALSE POSITIVE ANALYSIS")
    print("="*60)
    
    legitimate_folder = dataset_path / 'legitimate_different_content'
    
    if not legitimate_folder.exists():
        print("❌ No legitimate_different_content folder found!")
        print("   This is likely why you have high false positives.")
        return 0
    
    files = list(legitimate_folder.glob('*'))
    image_files = [f for f in files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']]
    
    print(f"\nCurrent legitimate content: {len(image_files)} images")
    
    if len(image_files) < 30:
        print("⚠️  WARNING: Too few legitimate images!")
        print("   Recommended: At least 30-50 diverse images")
        print("   Your dataset has:", len(image_files))
    
    return len(image_files)

def check_image_diversity(dataset_path: Path):
    """
    Check if legitimate images are too similar to originals
    """
    from PIL import Image
    import imagehash
    
    print("\n" + "="*60)
    print("IMAGE DIVERSITY CHECK")
    print("="*60)
    
    originals_folder = dataset_path / 'originals'
    legitimate_folder = dataset_path / 'legitimate_different_content'
    
    if not legitimate_folder.exists():
        return
    
    # Sample a few images from each
    original_hashes = []
    for img_file in list(originals_folder.glob('*'))[:10]:
        try:
            img = Image.open(img_file)
            phash = str(imagehash.phash(img, hash_size=8))
            original_hashes.append(phash)
        except:
            pass
    
    legitimate_hashes = []
    similar_count = 0
    
    for img_file in legitimate_folder.glob('*'):
        if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
            continue
        
        try:
            img = Image.open(img_file)
            leg_phash = str(imagehash.phash(img, hash_size=8))
            legitimate_hashes.append(leg_phash)
            
            # Check similarity to originals
            for orig_hash in original_hashes:
                distance = bin(int(leg_phash, 16) ^ int(orig_hash, 16)).count('1')
                if distance < 18:  # Similar!
                    similar_count += 1
                    print(f"⚠️  {img_file.name} is similar to originals (distance: {distance})")
                    break
        except:
            pass
    
    if similar_count > 0:
        print(f"\n⚠️  Found {similar_count} legitimate images similar to originals!")
        print("   This explains the high false positive rate.")
        print("   Solution: Replace with more diverse images")
    else:
        print("✅ Legitimate images appear diverse from originals")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fix_false_positives.py <dataset_path>")
        sys.exit(1)
    
    dataset_path = Path(sys.argv[1])
    
    # Analyze current situation
    current_count = analyze_current_fps(dataset_path)
    check_image_diversity(dataset_path)
    
    # Suggest solution
    print("\n" + "="*60)
    print("RECOMMENDED ACTIONS")
    print("="*60)
    
    if current_count < 30:
        print("\n1. Add more diverse legitimate content:")
        print(f"   Current: {current_count} images")
        print(f"   Needed: 30-50 images")
        print(f"   Missing: {30 - current_count} images")
        
        response = input("\n   Download diverse images automatically? (y/n): ")
        if response.lower() == 'y':
            legitimate_folder = dataset_path / 'legitimate_different_content'
            count_to_download = 50 - current_count
            download_diverse_images(legitimate_folder, count_to_download)
            
            print("\n✅ Dataset updated!")
            print("   Now re-run the benchmark:")
            print(f"   python benchmark_theft.py {dataset_path} --fast")
    else:
        print("\n✅ You have enough legitimate images")
        print("   The issue might be image similarity")
        print("   Consider replacing similar images with more diverse ones")
    
    print("\n" + "="*60)