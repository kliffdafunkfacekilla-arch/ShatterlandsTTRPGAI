import sqlite3
import os

DB_PATH = "c:/Users/krazy/Documents/GitHub/ShatterlandsTTRPGAI/AI-TTRPG/monolith/world.db" # Assuming this is the path, need to verify

# Try to find the DB file
if not os.path.exists(DB_PATH):
    # Try relative path from where I usually run commands
    DB_PATH = "monolith/world.db"

if not os.path.exists(DB_PATH):
    print(f"Could not find DB at {DB_PATH}")
    # Try to find it via os.walk or just assume it's in the root of monolith?
    # Let's try the standard location
    DB_PATH = "c:/Users/krazy/Documents/GitHub/ShatterlandsTTRPGAI/world.db"

if not os.path.exists(DB_PATH):
    print(f"Could not find DB at {DB_PATH}")
    exit(1)

print(f"Inspecting DB at: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute("PRAGMA table_info(locations)")
    columns = cursor.fetchall()
    print("Columns in 'locations' table:")
    for col in columns:
        print(col)
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
