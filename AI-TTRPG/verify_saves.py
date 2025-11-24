import logging
import uuid
from monolith.modules import save_api
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
        
        # Minimal rules data
        rules_data = {
            "base_stats_by_kingdom": {"ironclad": {"Strength": 10}},
            "derived_stats": {}
        }
        
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
    save_api.save_game(slot_id, active_character_id=f"player_{char_a_id}")
    logger.info(f"Saved game to slot {slot_id} with Active Character A")
    
    # 3. Verify Metadata via list_save_games
    saves = save_api.list_save_games()
    target_save = next((s for s in saves if s["name"] == slot_name_to_filename(slot_id)), None)
    
    # list_save_games returns 'char' field which maps to active_character_name
    # We need to verify the ID or at least the name if ID isn't exposed in list
    # The list_save_games only exposes name.
    # Let's check the file directly for ID if needed, or trust the name if unique.
    # Actually, let's just check the name for now as a proxy, or read the file.
    
    # Wait, list_save_games uses 'save_name' from the file, which is the slot name usually?
    # No, save_name in file is the slot name.
    
    # Let's read the file directly to be sure about the ID
    import json
    import os
    from monolith.modules.save_manager import SAVE_DIR
    
    filepath = os.path.join(SAVE_DIR, f"{slot_id}.json")
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    if data.get("active_character_id") == f"player_{char_a_id}":
        logger.info("SUCCESS: Metadata shows Character A is active.")
    else:
        logger.error(f"FAILURE: Metadata shows {data.get('active_character_id')}, expected player_{char_a_id}")
        return

    # 4. Create Character B
    char_b_id = create_test_character("Bob")
    logger.info(f"Created Character B: {char_b_id}")
    
    # 5. Save Game with Character B active (same slot)
    save_api.save_game(slot_id, active_character_id=f"player_{char_b_id}")
    logger.info(f"Saved game to slot {slot_id} with Active Character B")
    
    # 6. Verify Metadata Updated
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    if data.get("active_character_id") == f"player_{char_b_id}":
        logger.info("SUCCESS: Metadata updated to Character B.")
    else:
        logger.error(f"FAILURE: Metadata shows {data.get('active_character_id')}, expected player_{char_b_id}")
        return

    logger.info("--- Verification Complete ---")

def slot_name_to_filename(slot_name):
    return "".join(c for c in slot_name if c.isalnum() or c in ('_','-'))
