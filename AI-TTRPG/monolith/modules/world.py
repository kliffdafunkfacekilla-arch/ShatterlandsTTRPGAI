# AI-TTRPG/monolith/modules/world.py
"""
Adapter module for world_engine.

This module exposes a set of async functions that mirror the
original HTTP API. It operates in-process by calling
into its own internal `crud` functions with a local DB session.
"""
from typing import Any, Dict, Optional
from pathlib import Path
import asyncio
import logging
import json

# Import from this module's own internal package
from .world_pkg import crud as we_crud
from .world_pkg import database as we_db
from .world_pkg import schemas as we_schemas
from .world_pkg import services as we_services

logger = logging.getLogger("monolith.world")

def get_world_location_context(location_id: int) -> Dict[str, Any]:
    """
    Retrieves the context for a specific location in the world.

    This includes its description, map data, and other metadata.

    Args:
        location_id (int): The unique identifier of the location.

    Returns:
        Dict[str, Any]: The location context dictionary.
    """
    # --- REMOVED ASYNC AND _client ---
    db = we_db.SessionLocal()
    try:
        ctx = we_services.get_location_context(db, location_id)
        if not ctx:
            raise Exception(f"Location {location_id} not found")
        if isinstance(ctx.get("generated_map_data"), str):
            try:
                ctx["generated_map_data"] = json.loads(ctx["generated_map_data"])
            except Exception:
                ctx["generated_map_data"] = None
        return ctx
    # ... (rest of function unchanged) ...
    except Exception as e:
        logger.exception(f"[world.get_world_location_context] Error: {e}")
        raise
    finally:
        db.close()

def spawn_trap_in_world(trap_request: Any) -> Dict[str, Any]:
    """
    Spawns a trap instance in the world based on a request object.

    Args:
        trap_request (Any): A request object (dict or Pydantic model) containing trap details.

    Returns:
        Dict[str, Any]: The context of the newly created trap instance.
    """
    db = we_db.SessionLocal()
    try:
        # Deserialize the request into the TrapInstanceCreate schema
        if hasattr(trap_request, "model_dump"):
            req_data = trap_request.model_dump()
        elif hasattr(trap_request, "dict"):
            req_data = trap_request.dict()
        else:
            req_data = dict(trap_request)

        schema = we_schemas.TrapInstanceCreate(**req_data)

        # Use the CRUD function to create the trap
        trap = we_crud.create_trap(db, schema)

        # Return the created trap's context
        schema_trap = we_schemas.TrapInstance.from_orm(trap)
        return schema_trap.model_dump()
    except Exception as e:
        logger.exception(f"[world.spawn_trap_in_world] Error: {e}")
        raise
    finally:
        db.close()

def update_location_annotations(location_id: int, annotations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates the AI annotations for a specific location.

    Args:
        location_id (int): The unique identifier of the location.
        annotations (Dict[str, Any]): The new annotations data.

    Returns:
        Dict[str, Any]: A dictionary containing the updated 'ai_annotations'.
    """
    # --- REMOVED ASYNC AND _client ---
    db = we_db.SessionLocal()
    try:
        updated = we_crud.update_location_annotations(db, location_id, annotations)
        if not updated:
            raise Exception(f"Location {location_id} not found for annotation update")
        return {"ai_annotations": getattr(updated, "ai_annotations", None)}
    # ... (rest of function unchanged) ...
    except Exception as e:
        logger.exception(f"[world.update_location_annotations] Error: {e}")
        raise
    finally:
        db.close()

# --- (Apply same sync refactor to all other functions in this file) ---
def spawn_npc_in_world(spawn_request: Any) -> Dict[str, Any]:
    """
    Spawns an NPC in the world based on a request object.

    Args:
        spawn_request (Any): A request object (dict or Pydantic model) containing NPC details.

    Returns:
        Dict[str, Any]: A summary of the spawned NPC's data (ID, location, stats).
    """
    db = we_db.SessionLocal()
    try:
        if hasattr(spawn_request, "model_dump"): # Pydantic v2
            req_data = spawn_request.model_dump()
        elif hasattr(spawn_request, "dict"): # Pydantic v1
            req_data = spawn_request.dict()
        else:
            req_data = dict(spawn_request)
        schema = we_schemas.NpcSpawnRequest(**req_data)
        npc = we_crud.spawn_npc(db, schema)
        return {
            "id": getattr(npc, "id", None),
            "template_id": getattr(npc, "template_id", None),
            "location_id": getattr(npc, "location_id", None),
            "coordinates": getattr(npc, "coordinates", None),
            "current_hp": getattr(npc, "current_hp", 0),
            "max_hp": getattr(npc, "max_hp", 0),
        }
    except Exception as e:
        logger.exception(f"[world.spawn_npc_in_world] Error: {e}")
        raise
    finally:
        db.close()

def get_npc_context(npc_instance_id: int) -> Dict[str, Any]:
    """
    Retrieves the full context/state of a specific NPC instance.

    Args:
        npc_instance_id (int): The unique identifier of the NPC instance.

    Returns:
        Dict[str, Any]: The NPC instance data.
    """
    db = we_db.SessionLocal()
    try:
        npc = we_crud.get_npc(db, npc_instance_id)
        if npc is None:
            raise Exception(f"NPC {npc_instance_id} not found")
        schema_npc = we_schemas.NpcInstance.from_orm(npc)
        return schema_npc.model_dump() # Use model_dump for Pydantic v2
    except Exception as e:
        logger.exception(f"[world.get_npc_context] Error: {e}")
        raise
    finally:
        db.close()

def update_npc_state(npc_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates the state of a specific NPC instance.

    Args:
        npc_id (int): The unique identifier of the NPC instance.
        updates (Dict[str, Any]): A dictionary of fields to update.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
    db = we_db.SessionLocal()
    try:
        update_schema = we_schemas.NpcUpdate(**updates)
        updated_npc = we_crud.update_npc(db, npc_id, update_schema)
        if not updated_npc:
            raise Exception(f"NPC {npc_id} not found for update")
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.update_npc_state] Error: {e}")
        raise
    finally:
        db.close()

def spawn_item_in_world(spawn_request: Any) -> Dict[str, Any]:
    """
    Spawns an item in the world (on the ground).

    Args:
        spawn_request (Any): A request object (dict or Pydantic model) containing item details.

    Returns:
        Dict[str, Any]: The created item instance data.
    """
    db = we_db.SessionLocal()
    try:
        if hasattr(spawn_request, "model_dump"):
            req_data = spawn_request.model_dump()
        elif hasattr(spawn_request, "dict"):
            req_data = spawn_request.dict()
        else:
            req_data = dict(spawn_request)
        schema = we_schemas.ItemSpawnRequest(**req_data)
        item = we_crud.spawn_item(db, schema)
        schema_item = we_schemas.ItemInstance.from_orm(item)
        return schema_item.model_dump()
    except Exception as e:
        logger.exception(f"[world.spawn_item_in_world] Error: {e}")
        raise
    finally:
        db.close()

def delete_item_from_world(item_id: int) -> Dict[str, Any]:
    """
    Removes an item instance from the world.

    Args:
        item_id (int): The unique identifier of the item instance.

    Returns:
        Dict[str, Any]: A success dictionary.
    """
    db = we_db.SessionLocal()
    try:
        success = we_crud.delete_item(db, item_id)
        if not success:
            raise Exception(f"Item {item_id} not found for deletion")
        return {"success": True}
    except Exception as e:
        logger.exception(f"[world.delete_item_from_world] Error: {e}")
        raise
    finally:
        db.close()

def update_location_map(location_id: int, map_update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates the map data for a specific location.

    Args:
        location_id (int): The unique identifier of the location.
        map_update (Dict[str, Any]): The map data to update.

    Returns:
        Dict[str, Any]: The updated location data.
    """
    db = we_db.SessionLocal()
    try:
        schema = we_schemas.LocationMapUpdate(**map_update)
        updated_loc = we_crud.update_location_map(db, location_id, schema)
        if not updated_loc:
            raise Exception(f"Location {location_id} not found for map update")
        schema_loc = we_schemas.Location.from_orm(updated_loc)
        return schema_loc.model_dump()
    except Exception as e:
        logger.exception(f"[world.update_location_map] Error: {e}")
        raise
    finally:
        db.close()

def apply_status_to_npc(npc_id: int, status_id: str) -> Dict[str, Any]:
    """
    Applies a status effect to an NPC.

    Args:
        npc_id (int): The unique identifier of the NPC.
        status_id (str): The status effect identifier.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
    db = we_db.SessionLocal()
    try:
        updated_npc = we_crud.apply_status_to_npc(db, npc_id, status_id)
        if not updated_npc:
            raise Exception(f"NPC {npc_id} not found")
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.apply_status_to_npc] Error: {e}")
        raise
    finally:
        db.close()

def remove_status_from_npc(npc_id: int, status_id: str) -> Dict[str, Any]:
    """
    Removes a status effect from an NPC.

    Args:
        npc_id (int): The unique identifier of the NPC.
        status_id (str): The status effect identifier to remove.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
    db = we_db.SessionLocal()
    try:
        updated_npc = we_crud.remove_status_from_npc(db, npc_id, status_id)
        if not updated_npc:
            raise Exception(f"NPC {npc_id} not found")
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.remove_status_from_npc] Error: {e}")
        raise
    finally:
        db.close()


def register(orchestrator) -> None:
    """
    Registers the world module with the orchestrator.

    This module is primarily a direct-call adapter for other modules and does not
    currently subscribe to event bus commands.

    Args:
        orchestrator: The system orchestrator instance.
    """
    # This module doesn't subscribe to commands directly.
    # It's imported and called directly by other modules (like story.py)
    # for synchronous data queries.
    logger.info("[world] module registered (direct-call adapter)")

def apply_composure_damage_to_npc(npc_id: int, damage_amount: int) -> Dict[str, Any]:
    """
    Applies composure damage to an NPC.

    Args:
        npc_id (int): The unique identifier of the NPC.
        damage_amount (int): The amount of composure damage to apply.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
    db = we_db.SessionLocal()
    try:
        db_npc = we_crud.get_npc(db, npc_id)
        if not db_npc:
            raise Exception(f"NPC {npc_id} not found")

        new_composure = max(0, db_npc.current_composure - damage_amount)
        update_schema = we_schemas.NpcUpdate(current_composure=new_composure)

        updated_npc = we_crud.update_npc(db, npc_id, update_schema)
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.apply_composure_damage_to_npc] Error: {e}")
        raise
    finally:
        db.close()

def apply_composure_healing_to_npc(npc_id: int, amount: int) -> Dict[str, Any]:
    """
    Applies composure healing to an NPC.

    Args:
        npc_id (int): The unique identifier of the NPC.
        amount (int): The amount of composure to restore.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
    db = we_db.SessionLocal()
    try:
        db_npc = we_crud.get_npc(db, npc_id)
        if not db_npc:
            raise Exception(f"NPC {npc_id} not found")

        new_composure = min(db_npc.max_composure, db_npc.current_composure + amount)
        update_schema = we_schemas.NpcUpdate(current_composure=new_composure)

        updated_npc = we_crud.update_npc(db, npc_id, update_schema)
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.apply_composure_healing_to_npc] Error: {e}")
        raise
    finally:
        db.close()

def apply_temp_hp_to_npc(npc_id: int, amount: int) -> Dict[str, Any]:
    """
    Applies temporary HP to an NPC.

    Does not stack; the higher value replaces the current one.

    Args:
        npc_id (int): The unique identifier of the NPC.
        amount (int): The amount of temporary HP to apply.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
    db = we_db.SessionLocal()
    try:
        db_npc = we_crud.get_npc(db, npc_id)
        if not db_npc:
            raise Exception(f"NPC {npc_id} not found")

        # Temp HP generally doesn't stack; it replaces
        new_temp_hp = max(db_npc.temp_hp, amount)
        update_schema = we_schemas.NpcUpdate(temp_hp=new_temp_hp)

        updated_npc = we_crud.update_npc(db, npc_id, update_schema)
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.apply_temp_hp_to_npc] Error: {e}")
        raise
    finally:
        db.close()

def update_npc_resource_pool(npc_id: int, pool_name: str, new_value: int) -> Dict[str, Any]:
    """
    Updates a specific resource pool for an NPC.

    Args:
        npc_id (int): The unique identifier of the NPC.
        pool_name (str): The name of the resource pool.
        new_value (int): The new current value for the pool.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
    db = we_db.SessionLocal()
    try:
        db_npc = we_crud.get_npc(db, npc_id)
        if not db_npc:
            raise Exception(f"NPC {npc_id} not found")

        current_pools = db_npc.resource_pools or {}

        if pool_name not in current_pools:
            # Initialize pool if it doesn't exist (e.g., from base stats)
            current_pools[pool_name] = {"max": 10, "current": 0}

        current_pools[pool_name]["current"] = max(0, new_value)
        update_schema = we_schemas.NpcUpdate(resource_pools=current_pools)

        updated_npc = we_crud.update_npc(db, npc_id, update_schema)
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.update_npc_resource_pool] Error: {e}")
        raise
    finally:
        db.close()


def apply_composure_damage_to_npc(npc_id: int, damage_amount: int) -> Dict[str, Any]:
    """Applies composure damage to an NPC and returns new context."""
    db = we_db.SessionLocal()
    try:
        db_npc = we_crud.get_npc(db, npc_id)
        if not db_npc:
            raise Exception(f"NPC {npc_id} not found")

        new_composure = max(0, db_npc.current_composure - damage_amount)
        update_schema = we_schemas.NpcUpdate(current_composure=new_composure)

        updated_npc = we_crud.update_npc(db, npc_id, update_schema)
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.apply_composure_damage_to_npc] Error: {e}")
        raise
    finally:
        db.close()

def apply_composure_healing_to_npc(npc_id: int, amount: int) -> Dict[str, Any]:
    """Applies composure healing to an NPC and returns new context."""
    db = we_db.SessionLocal()
    try:
        db_npc = we_crud.get_npc(db, npc_id)
        if not db_npc:
            raise Exception(f"NPC {npc_id} not found")

        new_composure = min(db_npc.max_composure, db_npc.current_composure + amount)
        update_schema = we_schemas.NpcUpdate(current_composure=new_composure)

        updated_npc = we_crud.update_npc(db, npc_id, update_schema)
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.apply_composure_healing_to_npc] Error: {e}")
        raise
    finally:
        db.close()

def apply_temp_hp_to_npc(npc_id: int, amount: int) -> Dict[str, Any]:
    """Adds temporary HP to an NPC (does not stack, takes highest) and returns new context."""
    db = we_db.SessionLocal()
    try:
        db_npc = we_crud.get_npc(db, npc_id)
        if not db_npc:
            raise Exception(f"NPC {npc_id} not found")

        # Temp HP generally doesn't stack; it replaces
        new_temp_hp = max(db_npc.temp_hp, amount)
        update_schema = we_schemas.NpcUpdate(temp_hp=new_temp_hp)

        updated_npc = we_crud.update_npc(db, npc_id, update_schema)
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.apply_temp_hp_to_npc] Error: {e}")
        raise
    finally:
        db.close()

def update_npc_resource_pool(npc_id: int, pool_name: str, new_value: int) -> Dict[str, Any]:
    """Updates a specific resource pool for an NPC and returns new context."""
    db = we_db.SessionLocal()
    try:
        db_npc = we_crud.get_npc(db, npc_id)
        if not db_npc:
            raise Exception(f"NPC {npc_id} not found")

        current_pools = db_npc.resource_pools or {}

        if pool_name not in current_pools:
            # Initialize pool if it doesn't exist (e.g., from base stats)
            current_pools[pool_name] = {"max": 10, "current": 0}

        current_pools[pool_name]["current"] = max(0, new_value)
        update_schema = we_schemas.NpcUpdate(resource_pools=current_pools)

        updated_npc = we_crud.update_npc(db, npc_id, update_schema)
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.update_npc_resource_pool] Error: {e}")
        raise
    finally:
        db.close()
