import sqlite3
import os

db_path = 'test.db'

if not os.path.exists(db_path):
    print(f"❌ Database file not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔧 Running Database Migration...")
    print("-" * 50)
    
    # Check current schema
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {col[1] for col in cursor.fetchall()}
    print(f"Existing columns: {existing_columns}")
    
    # Add missing columns if they don't exist
    if 'confirmation_code' not in existing_columns:
        print("Adding confirmation_code column...")
        cursor.execute("ALTER TABLE users ADD COLUMN confirmation_code VARCHAR(6);")
        print("✅ confirmation_code added")
    
    if 'is_verified' not in existing_columns:
        print("Adding is_verified column...")
        cursor.execute("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0;")
        print("✅ is_verified added")
    
    conn.commit()
    
    # Verify schema
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    print("\n📋 Updated Schema:")
    for col in columns:
        print(f"   - {col[1]} ({col[2]})")
    
    conn.close()
    print("\n✅ Migration complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
