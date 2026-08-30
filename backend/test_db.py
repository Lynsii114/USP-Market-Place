import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from app.db import engine, Base
    from app import models
    import sqlite3
    
    # Test connection
    print("🔍 Testing Database Connection...")
    print("-" * 50)
    
    # Check SQLAlchemy connection
    with engine.connect() as connection:
        print("✅ SQLAlchemy connection successful")
    
    # Direct SQLite check
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    if tables:
        print(f"✅ Database contains {len(tables)} table(s):")
        for table in tables:
            print(f"   • {table[0]}")
            
            # Get column info for each table
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"      - {col[1]} ({col[2]})")
    else:
        print("❌ No tables found in database")
    
    # Count records
    print("\n📊 Record Counts:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"   • {table[0]}: {count} records")
    
    conn.close()
    print("\n✅ Database verification complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
