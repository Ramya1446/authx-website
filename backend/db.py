"""
db.py - Database schema management for Authx
"""

import sqlite3
import os

DATABASE_PATH = "authx.db"

def fix_database():
    print("="*60)
    print("Fixing Authx Database Schema")
    print("="*60)
    
    # Backup database first
    if os.path.exists(DATABASE_PATH):
        import shutil
        backup_path = DATABASE_PATH + ".backup"
        shutil.copy2(DATABASE_PATH, backup_path)
        print(f"\n✓ Backup created: {backup_path}")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check current schema
    print("\n1. Checking current schema...")
    cursor.execute("PRAGMA table_info(content_registry)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    print(f"   Current columns: {column_names}")
    
    # Add missing columns
    print("\n2. Adding missing columns...")
    
    columns_to_add = [
        ("tamper_score", "REAL"),
        ("tamper_confidence", "REAL"),
        ("detected_artifacts", "TEXT")
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in column_names:
            try:
                cursor.execute(f"ALTER TABLE content_registry ADD COLUMN {col_name} {col_type}")
                print(f"   ✓ Added column: {col_name} ({col_type})")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"   ⚠ Column {col_name} already exists")
                else:
                    print(f"   ✗ Error adding {col_name}: {e}")
        else:
            print(f"   ⚠ Column {col_name} already exists")
    
    conn.commit()
    
    # Verify new schema
    print("\n3. Verifying updated schema...")
    cursor.execute("PRAGMA table_info(content_registry)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    print(f"   Updated columns: {column_names}")
    
    # Check if all required columns exist
    required_columns = [
        'id', 'owner_name', 'owner_address', 'content_type', 'description',
        'ai_tool', 'sha256', 'phash', 'file_path', 'registered_at',
        'tx_hash', 'block_number', 'tamper_score', 'tamper_confidence',
        'detected_artifacts'
    ]
    
    missing = [col for col in required_columns if col not in column_names]
    if missing:
        print(f"\n   ⚠ Still missing columns: {missing}")
    else:
        print(f"\n   ✓ All required columns present!")
    
    conn.close()
    
    print("\n" + "="*60)
    print("Database schema updated successfully!")
    print("You can now run: python app.py")
    print("="*60)

if __name__ == "__main__":
    try:
        fix_database()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()