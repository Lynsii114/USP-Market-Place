import sqlite3
import json

conn = sqlite3.connect('test.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("\n" + "=" * 70)
print("📊 DATABASE CONTENTS - USP MARKETPLACE")
print("=" * 70)

# Users Table
print("\n👥 USERS TABLE:")
print("-" * 70)
cursor.execute("SELECT * FROM users")
users = cursor.fetchall()

if users:
    for user in users:
        print(f"\n  ID: {user['id']}")
        print(f"  Username: {user['username']}")
        print(f"  Email: {user['email']}")
        print(f"  Password Hash: {user['password_hash'][:20]}...")
        print(f"  Confirmation Code: {user['confirmation_code']}")
        print(f"  Verified: {'✅ Yes' if user['is_verified'] else '❌ No'}")
else:
    print("  (No users yet)")

# Items Table
print("\n\n📦 ITEMS TABLE:")
print("-" * 70)
cursor.execute("SELECT * FROM items")
items = cursor.fetchall()

if items:
    for item in items:
        print(f"\n  ID: {item['id']}")
        print(f"  Name: {item['name']}")
        print(f"  Price: ${item['price']}")
else:
    print("  (No items yet)")

# Statistics
print("\n\n📈 STATISTICS:")
print("-" * 70)
cursor.execute("SELECT COUNT(*) as count FROM users")
user_count = cursor.fetchone()['count']
cursor.execute("SELECT COUNT(*) as count FROM items")
item_count = cursor.fetchone()['count']

print(f"  Total Users: {user_count}")
print(f"  Total Items: {item_count}")
cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_verified = 1")
verified_count = cursor.fetchone()['count']
print(f"  Verified Users: {verified_count}")

print("\n" + "=" * 70 + "\n")

conn.close()
