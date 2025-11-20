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
    """
    Internal helper to retrieve a Character model from the database.

    Validates the character ID format (expected to start with "player_") and
    extracts the UUID to query the database. Raises an exception if the
    ID is invalid or the character is not found.

    Args:
        db (char_db.SessionLocal): The database session to use for the query.
        char_id (str): The full character ID (e.g., "player_12345").

    Returns:
        Character: The retrieved SQLAlchemy Character model instance.

    Raises:
        ValueError: If `char_id` does not start with "player_".
        Exception: If the character is not found in the database.
    """
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
def get_character_context(char_id: str) -> Dict[str, Any]:
    """
    Retrieves the full context for a character.

    This includes stats, inventory, equipment, and calculated derived values.

    Args:
        char_id (str): The unique identifier of the character.

    Returns:
        Dict[str, Any]: A dictionary representation of the character's context.
    """
    # --- REMOVED ASYNC AND _client ---
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        schema_char = char_services.get_character_context(db_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.get_character_context] Error: {e}")
        raise
    finally:
        db.close()

def unequip_item(char_id: str, slot: str) -> Dict[str, Any]:
    """
    Unequips an item from a specific slot on a character.

    Args:
        char_id (str): The unique identifier of the character.
        slot (str): The slot identifier to unequip (e.g., 'head', 'main_hand').

    Returns:
        Dict[str, Any]: The updated character context after removing the item.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.unequip_item(db, db_char, slot)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.unequip_item] Error: {e}")
        raise
    finally:
        db.close()

def equip_item(char_id: str, item_id: str, slot: str) -> Dict[str, Any]:
    """
    Equips an item to a character's slot.

    Args:
        char_id (str): The unique identifier of the character.
        item_id (str): The unique identifier of the item template to equip.
        slot (str): The target slot identifier.

    Returns:
        Dict[str, Any]: The updated character context.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.equip_item(db, db_char, item_id, slot)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    finally:
        db.close()

def update_character_resource_pool(char_id: str, pool_name: str, new_value: int) -> Dict[str, Any]:
    """
    Updates the value of a specific resource pool for a character.

    Args:
        char_id (str): The unique identifier of the character.
        pool_name (str): The name of the resource pool (e.g., 'mana', 'stamina').
        new_value (int): The new value to set for the pool (current value).

    Returns:
        Dict[str, Any]: The updated character context.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.update_resource_pool(db, db_char, pool_name, new_value)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.update_character_resource_pool] Error: {e}")
        raise
    finally:
        db.close()

def apply_damage_to_character(char_id: str, damage_amount: int) -> Dict[str, Any]:
    """
    Applies physical damage to a character.

    Args:
        char_id (str): The unique identifier of the character.
        damage_amount (int): The amount of damage to apply.

    Returns:
        Dict[str, Any]: The updated character context.
    """
    # --- REMOVED ASYNC AND _client ---
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.apply_damage_to_character(db, db_char, damage_amount)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    # ... (rest of function unchanged) ...
    except Exception as e:
        logger.exception(f"[character.apply_damage_to_character] Error: {e}")
        raise
    finally:
        db.close()

# --- (Apply same sync refactor to all other functions in this file) ---
def apply_status_to_character(char_id: str, status_id: str) -> Dict[str, Any]:
    """
    Applies a status effect to a character.

    Args:
        char_id (str): The unique identifier of the character.
        status_id (str): The identifier of the status effect.

    Returns:
        Dict[str, Any]: The updated character context.
    """
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

def add_item_to_character(char_id: str, item_id: str, quantity: int) -> Dict[str, Any]:
    """
    Adds a quantity of an item to the character's inventory.

    Args:
        char_id (str): The unique identifier of the character.
        item_id (str): The identifier of the item template.
        quantity (int): The number of items to add.

    Returns:
        Dict[str, Any]: The updated character context.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.add_item_to_inventory(db, db_char, item_id, quantity)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.add_item_to_character] Error: {e}")
        raise
    finally:
        db.close()

def remove_item_from_character(char_id: str, item_id: str, quantity: int) -> Dict[str, Any]:
    """
    Removes a quantity of an item from the character's inventory.

    Args:
        char_id (str): The unique identifier of the character.
        item_id (str): The identifier of the item template to remove.
        quantity (int): The number of items to remove.

    Returns:
        Dict[str, Any]: The updated character context.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.remove_item_from_inventory(db, db_char, item_id, quantity)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.remove_item_from_character] Error: {e}")
        raise
    finally:
        db.close()

def update_character_location(char_id: str, location_id: int, coordinates: List[int]) -> Dict[str, Any]:
    """
    Updates a character's location and coordinates in the world.

    Args:
        char_id (str): The unique identifier of the character.
        location_id (int): The ID of the location the character is entering.
        coordinates (List[int]): The [x, y] coordinates in the new location.

    Returns:
        Dict[str, Any]: The updated character context.
    """
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

def remove_status_from_character(char_id: str, status_id: str) -> Dict[str, Any]:
    """
    Removes a status effect from a character.

    Args:
        char_id (str): The unique identifier of the character.
        status_id (str): The identifier of the status effect to remove.

    Returns:
        Dict[str, Any]: The updated character context.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.remove_status_from_character(db, db_char, status_id)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.remove_status_from_character] Error: {e}")
        raise
    finally:
        db.close()


def register(orchestrator) -> None:
    """
    Registers the character module with the orchestrator.

    This module is primarily a direct-call adapter for other modules and does not
    currently subscribe to event bus commands.

    Args:
        orchestrator: The system orchestrator instance.
    """
    # This module is called directly by other modules (like story.py)
    # and does not currently subscribe to any event bus commands.
    logger.info("[character] module registered (direct-call adapter)")

def apply_composure_damage_to_character(char_id: str, damage_amount: int) -> Dict[str, Any]:
    """
    Applies composure damage to a character.

    Args:
        char_id (str): The unique identifier of the character.
        damage_amount (int): The amount of composure damage to apply.

    Returns:
        Dict[str, Any]: The updated character context.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.apply_composure_damage(db, db_char, damage_amount)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.apply_composure_damage_to_character] Error: {e}")
        raise
    finally:
        db.close()

def apply_composure_healing_to_character(char_id: str, amount: int):
    """
    Applies composure healing to a character.

    Args:
        char_id (str): The unique identifier of the character.
        amount (int): The amount of composure to restore.

    Returns:
        Dict[str, Any]: The updated character context.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.apply_composure_healing(db, db_char, amount)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.apply_composure_healing_to_character] Error: {e}")
        raise
    finally:
        db.close()

def apply_resource_damage_to_character(char_id: str, resource_name: str, damage_amount: int) -> Dict[str, Any]:
    """
    Applies damage to a specific resource pool (e.g., Chi, Stamina).

    Args:
        char_id (str): The unique identifier of the character.
        resource_name (str): The name of the resource pool to damage.
        damage_amount (int): The amount to reduce the resource by.

    Returns:
        Dict[str, Any]: The updated character context.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        updated_char = char_crud.apply_resource_damage(db, db_char, resource_name, damage_amount)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.apply_resource_damage_to_character] Error: {e}")
        raise
    finally:
        db.close()

def apply_healing_to_character(char_id: str, amount: int):
    """
    Applies healing to a character's Hit Points.

    Args:
        char_id (str): The unique identifier of the character.
        amount (int): The amount of HP to restore.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        char_crud.apply_healing(db, db_char, amount)
    finally:
        db.close()

def apply_temp_hp_to_character(char_id: str, amount: int) -> Dict[str, Any]:
    """
    Applies temporary HP to a character.

    Temporary HP usually does not stack; the higher value typically overrides.

    Args:
        char_id (str): The unique identifier of the character.
        amount (int): The amount of temporary HP to apply.

    Returns:
        Dict[str, Any]: The updated character context.
    """
    db = char_db.SessionLocal()
    try:
        db_char = _get_character_db(db, char_id)
        # This now calls the real CRUD function
        updated_char = char_crud.apply_temp_hp(db, db_char, amount)
        schema_char = char_services.get_character_context(updated_char)
        return schema_char.model_dump()
    except Exception as e:
        logger.exception(f"[character.apply_temp_hp_to_character] Error: {e}")
        raise
    finally:
        db.close()
