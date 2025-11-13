# AI-TTRPG/monolith/modules/character.py
"""
Adapter module for character_engine.

This module exposes a set of async functions that mirror the
original HTTP API. It operates in-process by calling
into its own internal `crud` and `services` functions
with a local DB session.
"""
from typing import Any, Dict, Optional, List
import logging

# Import from this module's own internal package
from .character_pkg import crud as char_crud
from .character_pkg import services as char_services
from .character_pkg import database as char_db
from .character_pkg import schemas as char_schemas
from .character_pkg.models import Character

logger = logging.getLogger("monolith.character")

# --- Helper to get a character model ---
def _get_character_db(db: char_db.SessionLocal, char_id: str) -> Character:
    """Internal helper to get a character model, raising a standard exception."""
    # Note: char_id in story_engine is "player_UUID"
    # We must strip the "player_" prefix
    if not isinstance(char_id, str) or not char_id.startswith("player_"):
        raise ValueError(f"Invalid char_id format: {char_id}")

    uuid_part = char_id.split("_", 1)[1]

    db_character = char_crud.get_character(db, char_id=uuid_part)
    if not db_character:
        raise Exception(f"Character {char_id} (UUID: {uuid_part}) not found in database")
    return db_character

# --- Public API functions for other modules ---
async def get_character_context(_client: Any, char_id: str) -> Dict[str, Any]:
    """Gets the full data for a single character."""
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        # Use the service function to map the DB model to the Pydantic schema
        schema_char = char_services.get_character_context(db_char)
        return schema_char.model_dump() # Use .model_dump() for Pydantic v2
    except Exception as e:
        logger.exception(f"[character.get_character_context] Error: {e}")
        raise
    finally:
        db.close()

async def apply_damage_to_character(_client: Any, char_id: str, damage_amount: int) -> Dict[str, Any]:
    """Applies HP damage to a character."""
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.apply_damage_to_character(db, db_char, damage_amount)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.apply_damage_to_character] Error: {e}")
        raise
    finally:
        db.close()

async def apply_status_to_character(_client: Any, char_id: str, status_id: str) -> Dict[str, Any]:
    """Applies a status effect to a character."""
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.apply_status_to_character(db, db_char, status_id)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.apply_status_to_character] Error: {e}")
        raise
    finally:
        db.close()

async def add_item_to_character(_client: Any, char_id: str, item_id: str, quantity: int) -> Dict[str, Any]:
    """Adds an item to a character's inventory."""
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        # This function *exists* in crud.py but was not exposed via an endpoint
        updated_char = char_crud.add_item_to_inventory(db, db_char, item_id, quantity)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.add_item_to_character] Error: {e}")
        raise
    finally:
        db.close()

async def remove_item_from_character(_client: Any, char_id: str, item_id: str, quantity: int) -> Dict[str, Any]:
    """Removes an item from a character's inventory."""
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        # This function *exists* in crud.py but was not exposed via an endpoint
        updated_char = char_crud.remove_item_from_inventory(db, db_char, item_id, quantity)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.remove_item_from_character] Error: {e}")
        raise
    finally:
        db.close()

async def update_character_location(_client: Any, char_id: str, location_id: int, coordinates: List[int]) -> Dict[str, Any]:
    """Updates a character's location and coordinates."""
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.update_character_location_and_coords(db, db_char, location_id, coordinates)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.update_character_location] Error: {e}")
        raise
    finally:
        db.close()

def register(orchestrator) -> None:
    # This module is called directly by other modules (like story.py)
    # and does not currently subscribe to any event bus commands.
    logger.info("[character] module registered (direct-call adapter)")
