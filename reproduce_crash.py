import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'AI-TTRPG')))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reproduce_crash")

try:
    from monolith.modules.character_pkg import crud as char_crud
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
    from monolith.modules.world_pkg import crud as world_crud
    from monolith.modules.world_pkg.database import SessionLocal as WorldSession
    from monolith.modules.character_pkg import schemas as char_schemas
except ImportError as e:
    logger.error(f"Import failed: {e}")
    sys.exit(1)

def reproduce():
    logger.info("Starting crash reproduction script...")

    # 1. Get a character to load
    char_name = None
    try:
        with CharSession() as db:
            chars = char_crud.list_characters(db)
            if chars:
                char_name = chars[0].name
                logger.info(f"Found character to test: {char_name}")
            else:
                logger.error("No characters found in DB. Cannot test loading.")
                return
    except Exception as e:
        logger.exception(f"Failed to list characters: {e}")
        return

    # 2. Simulate MainInterfaceScreen.on_enter loading logic
    logger.info("Simulating MainInterfaceScreen loading...")
    
    party_contexts = []
    active_character_context = None
    
    # Load Party
    try:
        with CharSession() as char_db:
            logger.info(f"Loading character: {char_name}")
            db_char = char_crud.get_character_by_name(char_db, char_name)
            if not db_char:
                raise Exception(f"Character '{char_name}' not found in database.")

            logger.info("Calling get_character_context...")
            context = char_services.get_character_context(db_char)
            party_contexts.append(context)
            active_character_context = context
            logger.info(f"Character Context Loaded. ID: {context.id}, Location: {context.current_location_id}")

    except Exception as e:
        logger.exception(f"Failed to load party: {e}")
        return

    # Load Location
    try:
        if active_character_context:
            loc_id = active_character_context.current_location_id
            logger.info(f"Loading location context for ID: {loc_id}")
            
            with WorldSession() as world_db:
                location_context = world_crud.get_location_context(world_db, loc_id)
                if not location_context:
                    raise Exception(f"Location ID '{loc_id}' not found in database.")
                
                logger.info(f"Location Context Loaded: {location_context.get('name')}")
                logger.info(f"Map Data Length: {len(location_context.get('generated_map_data', []))}")

    except Exception as e:
        logger.exception(f"Failed to load location context: {e}")
        return

    logger.info("Reproduction script finished successfully (No crash found).")

if __name__ == "__main__":
    reproduce()
