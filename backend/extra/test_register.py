"""
Test the registration process step by step to identify the issue
"""

import io
from PIL import Image
import hashlib
import imagehash
from pathlib import Path
import sqlite3

print("="*60)
print("Testing Registration Process Step by Step")
print("="*60)

# Step 1: Create test image
print("\n1. Creating test image...")
try:
    img = Image.new('RGB', (200, 200), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes = img_bytes.getvalue()
    print(f"  ✓ Test image created ({len(img_bytes)} bytes)")
except Exception as e:
    print(f"  ✗ Error: {e}")
    exit(1)

# Step 2: Compute SHA-256
print("\n2. Computing SHA-256 hash...")
try:
    sha256_hash = hashlib.sha256(img_bytes).hexdigest()
    print(f"  ✓ SHA-256: {sha256_hash[:32]}...")
except Exception as e:
    print(f"  ✗ Error: {e}")
    exit(1)

# Step 3: Compute pHash
print("\n3. Computing perceptual hash...")
try:
    image = Image.open(io.BytesIO(img_bytes))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    phash = imagehash.phash(image)
    phash_str = str(phash)
    print(f"  ✓ pHash: {phash_str}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 4: Test AI detector
print("\n4. Testing AI tampering detector...")
try:
    from ai_detector import AITamperingDetector
    detector = AITamperingDetector()
    result = detector.analyze(img_bytes, "image/jpeg")
    print(f"  ✓ AI analysis complete")
    print(f"    Tamper probability: {result['tamper_probability']:.2f}")
    print(f"    Confidence: {result['confidence']:.2f}")
    print(f"    Artifacts: {result.get('detected_artifacts', [])}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 5: Test blockchain
print("\n5. Testing blockchain registration...")
try:
    from blockchain import BlockchainManager
    blockchain = BlockchainManager()
    blockchain_result = blockchain.register(
        sha256_hash=sha256_hash,
        owner_name="Test User",
        content_type="image"
    )
    print(f"  ✓ Blockchain registration complete")
    print(f"    TX Hash: {blockchain_result.get('tx_hash', 'N/A')[:32]}...")
    print(f"    Block: {blockchain_result.get('block_number', 'N/A')}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 6: Test database insertion
print("\n6. Testing database insertion...")
try:
    conn = sqlite3.connect("authx.db")
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='content_registry';")
    if not cursor.fetchone():
        print("  ⚠ Table 'content_registry' doesn't exist, creating it...")
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
                file_path TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tx_hash TEXT,
                block_number INTEGER,
                tamper_score REAL,
                tamper_confidence REAL,
                detected_artifacts TEXT
            )
        """)
        conn.commit()
    
    # Try to insert
    cursor.execute("""
        INSERT INTO content_registry 
        (owner_name, owner_address, content_type, description, ai_tool, 
         sha256, phash, file_path, tx_hash, block_number, 
         tamper_score, tamper_confidence, detected_artifacts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Test User",
        "test@example.com",
        "image",
        "Test description",
        "None",
        sha256_hash,
        phash_str,
        f"uploads/{sha256_hash}.jpg",
        blockchain_result.get("tx_hash"),
        blockchain_result.get("block_number"),
        result.get("tamper_probability", 0.0),
        result.get("confidence", 0.0),
        ",".join(result.get("detected_artifacts", []))
    ))
    
    content_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"  ✓ Database insertion successful")
    print(f"    Content ID: {content_id}")
    
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
    conn.close()
    exit(1)

# Step 7: Save file
print("\n7. Testing file save...")
try:
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / f"{sha256_hash}.jpg"
    
    with open(file_path, "wb") as f:
        f.write(img_bytes)
    
    print(f"  ✓ File saved: {file_path}")
    
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("✓ All steps completed successfully!")
print("The registration process should work.")
print("="*60)

print("\nNow try running: python app.py")
print("Then test registration from the frontend.")