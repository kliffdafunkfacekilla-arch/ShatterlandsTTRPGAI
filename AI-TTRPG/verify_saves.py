import logging
import uuid
from monolith.modules.save_manager import save_game, load_game, get_save_metadata
from monolith.modules.character_pkg import services as char_services
from monolith.modules.character_pkg import schemas as char_schemas
from monolith.modules.character_pkg import database as char_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_saves")

def create_test_character(name: str):
    db = char_db.SessionLocal()
    try:
        # Create a simple character
        char_create = char_schemas.CharacterCreate(
            name=name,
            kingdom="Ironclad",
            stats={"Strength": 10, "Agility": 10, "Mind": 10}, # Simplified stats
            background={"origin": "Test"}
        )
        # We need rules data, but let's try to use the default test character creator if available
        # or just mock it.
        # Actually, let's use create_default_test_character if possible, but it hardcodes name.
        # So we'll just use the service directly if we can mock rules_data.
        
        # Minimal rules data
        rules_data = {
            "base_stats_by_kingdom": {"ironclad": {"Strength": 10}},
            "derived_stats": {}
        }
        
        # We'll just create a character manually in DB to avoid service complexity if needed
        # But let's try the service first.
        # Actually, let's use create_default_test_character and rename it.
        char = char_services.create_default_test_character(db, rules_data)
        char.name = name
        db.commit()
        db.refresh(char)
        return char.id
    finally:
        db.close()

def verify_multi_character_save():
    logger.info("--- Starting Multi-Character Save Verification ---")
    
    # 1. Create Character A
    char_a_id = create_test_character("Alice")
    logger.info(f"Created Character A: {char_a_id}")
    
    # 2. Save Game with Character A active
    slot_id = "test_slot_multi"
    save_game(slot_id, active_character_id=f"player_{char_a_id}")
    logger.info(f"Saved game to slot {slot_id} with Active Character A")
    
    # 3. Verify Metadata
    meta = get_save_metadata(slot_id)
    if meta.active_character_id == f"player_{char_a_id}":
        logger.info("SUCCESS: Metadata shows Character A is active.")
    else:
        logger.error(f"FAILURE: Metadata shows {meta.active_character_id}, expected player_{char_a_id}")
        return

    # 4. Create Character B
    char_b_id = create_test_character("Bob")
    logger.info(f"Created Character B: {char_b_id}")
    
    # 5. Save Game with Character B active (same slot)
    save_game(slot_id, active_character_id=f"player_{char_b_id}")
    logger.info(f"Saved game to slot {slot_id} with Active Character B")
    
    # 6. Verify Metadata Updated
    meta = get_save_metadata(slot_id)
    if meta.active_character_id == f"player_{char_b_id}":
        logger.info("SUCCESS: Metadata updated to Character B.")
    else:
        logger.error(f"FAILURE: Metadata shows {meta.active_character_id}, expected player_{char_b_id}")
        return

    logger.info("--- Verification Complete ---")

if __name__ == "__main__":
    verify_multi_character_save()
