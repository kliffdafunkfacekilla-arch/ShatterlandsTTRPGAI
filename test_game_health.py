import sys
import os
import logging
import sqlite3

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'AI-TTRPG')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("health_check")

def check_database_schema():
    logger.info("--- Checking Database Schema ---")
    db_path = os.path.join(os.path.dirname(__file__), 'world.db')
    
    if not os.path.exists(db_path):
        logger.error(f"world.db not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for factions table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='factions';")
        if cursor.fetchone():
            logger.info("✅ Table 'factions' exists.")
        else:
            logger.error("❌ Table 'factions' MISSING.")

        # Check for other critical tables
        critical_tables = ['locations', 'regions', 'game_state', 'npc_instances', 'item_instances']
        for table in critical_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
            if cursor.fetchone():
                logger.info(f"✅ Table '{table}' exists.")
            else:
                logger.error(f"❌ Table '{table}' MISSING.")
        
        conn.close()
    except Exception as e:
        logger.error(f"Database check failed: {e}")

def test_backend_services():
    logger.info("\n--- Testing Backend Services ---")
    try:
        from monolith.modules import save_api
        from monolith.modules import story as story_api
        from monolith.modules import debug_api # Assuming this exists or logic is in debug_utils
        from monolith.modules.world_pkg import crud as world_crud
        from monolith.modules.world_pkg.database import SessionLocal as WorldSession
        
        # Test 1: Save Game (Simulated)
        logger.info("Testing Save API...")
        try:
            # We won't actually save to avoid clutter, but we'll check if the function exists and imports
            if hasattr(save_api, 'save_game'):
                logger.info("✅ save_api.save_game function exists.")
            else:
                logger.error("❌ save_api.save_game function MISSING.")
        except Exception as e:
            logger.error(f"Save API check failed: {e}")

        # Test 2: Story API (Narration)
        logger.info("Testing Story API...")
        try:
            if hasattr(story_api, 'handle_narrative_prompt'):
                logger.info("✅ story_api.handle_narrative_prompt function exists.")
            else:
                logger.error("❌ story_api.handle_narrative_prompt function MISSING.")
        except Exception as e:
            logger.error(f"Story API check failed: {e}")

    except ImportError as e:
        logger.error(f"Failed to import monolith modules: {e}")

if __name__ == "__main__":
    check_database_schema()
    test_backend_services()
