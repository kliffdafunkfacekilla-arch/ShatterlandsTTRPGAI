import sqlite3
import os

DB_PATH = "c:/Users/krazy/Documents/GitHub/ShatterlandsTTRPGAI/world.db"

if not os.path.exists(DB_PATH):
    print(f"Could not find DB at {DB_PATH}")
    exit(1)

print(f"Updating DB at: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Check if columns exist before adding them to avoid errors if run multiple times
    cursor.execute("PRAGMA table_info(locations)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "flavor_context" not in columns:
        print("Adding flavor_context column...")
        cursor.execute("ALTER TABLE locations ADD COLUMN flavor_context JSON")
    else:
        print("flavor_context column already exists.")

    if "player_reputation" not in columns:
        print("Adding player_reputation column...")
        cursor.execute("ALTER TABLE locations ADD COLUMN player_reputation INTEGER DEFAULT 0")
    else:
        print("player_reputation column already exists.")

    if "last_combat_outcome" not in columns:
        print("Adding last_combat_outcome column...")
        cursor.execute("ALTER TABLE locations ADD COLUMN last_combat_outcome VARCHAR")
    else:
        print("last_combat_outcome column already exists.")

    conn.commit()
    print("Schema update complete.")

except Exception as e:
    print(f"Error updating schema: {e}")
    conn.rollback()
finally:
    conn.close()
