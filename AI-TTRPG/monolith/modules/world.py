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

# Import story to access director or active quests
from . import story
from ..shared import with_db_session

logger = logging.getLogger("monolith.world")

@with_db_session(we_db.SessionLocal)
def get_world_location_context(location_id: int, db: Session = None) -> Dict[str, Any]:
    """
    Retrieves the context for a specific location in the world.

    This includes its description, map data, and other metadata.

    Checks story system for map injections (Phase 4 integration).

    Args:
        location_id (int): The unique identifier of the location.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The location context dictionary.
    """
    try:
        # Check if map needs generation
        loc = we_crud.get_location(db, location_id)
        if loc and not loc.generated_map_data:
             # It needs generation. Let's check for injections.
             # We need to get active quests.
             tags = loc.tags or ["generic"]

             # --- Determine Injections from Quests ---
             injection_req = story.get_active_quest_requirements(location_id)
             if injection_req:
                 logger.info(f"Injecting into map {location_id}: {injection_req}")

             # Manually trigger generation via map_api
             from . import map as map_api

             # generate map
             map_data = map_api.generate_map(tags, injections=injection_req)

             # save it using crud
             update_schema = we_schemas.LocationMapUpdate(
                generated_map_data=map_data.get("map_data"),
                map_seed=map_data.get("seed_used"),
                spawn_points=map_data.get("spawn_points")
             )
             we_crud.update_location_map(db, location_id, update_schema)

             # Now `get_location_context` will find the map and return it.

        ctx = we_crud.get_location_context(db, location_id)
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

@with_db_session(we_db.SessionLocal)
def spawn_trap_in_world(trap_request: Any, db: Session = None) -> Dict[str, Any]:
    """
    Spawns a trap instance in the world based on a request object.

    Args:
        trap_request (Any): A request object (dict or Pydantic model) containing trap details.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The context of the newly created trap instance.
    """
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

@with_db_session(we_db.SessionLocal)
def update_location_annotations(location_id: int, annotations: Dict[str, Any], db: Session = None) -> Dict[str, Any]:
    """
    Updates the AI annotations for a specific location.

    Args:
        location_id (int): The unique identifier of the location.
        annotations (Dict[str, Any]): The new annotations data.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: A dictionary containing the updated 'ai_annotations'.
    """
    try:
        updated = we_crud.update_location_annotations(db, location_id, annotations)
        if not updated:
            raise Exception(f"Location {location_id} not found for annotation update")
        return {"ai_annotations": getattr(updated, "ai_annotations", None)}
    # ... (rest of function unchanged) ...
    except Exception as e:
        logger.exception(f"[world.update_location_annotations] Error: {e}")
        raise

# --- (Apply same sync refactor to all other functions in this file) ---
@with_db_session(we_db.SessionLocal)
def spawn_npc_in_world(spawn_request: Any, db: Session = None) -> Dict[str, Any]:
    """
    Spawns an NPC in the world based on a request object.

    Args:
        spawn_request (Any): A request object (dict or Pydantic model) containing NPC details.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: A summary of the spawned NPC's data (ID, location, stats).
    """
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

@with_db_session(we_db.SessionLocal)
def get_npc_context(npc_instance_id: int, db: Session = None) -> Dict[str, Any]:
    """
    Retrieves the full context/state of a specific NPC instance.

    Args:
        npc_instance_id (int): The unique identifier of the NPC instance.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The NPC instance data.
    """
    try:
        npc = we_crud.get_npc(db, npc_instance_id)
        if npc is None:
            raise Exception(f"NPC {npc_instance_id} not found")
        schema_npc = we_schemas.NpcInstance.from_orm(npc)
        return schema_npc.model_dump() # Use model_dump for Pydantic v2
    except Exception as e:
        logger.exception(f"[world.get_npc_context] Error: {e}")
        raise

@with_db_session(we_db.SessionLocal)
def update_npc_state(npc_id: int, updates: Dict[str, Any], db: Session = None) -> Dict[str, Any]:
    """
    Updates the state of a specific NPC instance.

    Args:
        npc_id (int): The unique identifier of the NPC instance.
        updates (Dict[str, Any]): A dictionary of fields to update.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
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

@with_db_session(we_db.SessionLocal)
def spawn_item_in_world(spawn_request: Any, db: Session = None) -> Dict[str, Any]:
    """
    Spawns an item in the world (on the ground).

    Args:
        spawn_request (Any): A request object (dict or Pydantic model) containing item details.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The created item instance data.
    """
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

@with_db_session(we_db.SessionLocal)
def delete_item_from_world(item_id: int, db: Session = None) -> Dict[str, Any]:
    """
    Removes an item instance from the world.

    Args:
        item_id (int): The unique identifier of the item instance.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: A success dictionary.
    """
    try:
        success = we_crud.delete_item(db, item_id)
        if not success:
            raise Exception(f"Item {item_id} not found for deletion")
        return {"success": True}
    except Exception as e:
        logger.exception(f"[world.delete_item_from_world] Error: {e}")
        raise

@with_db_session(we_db.SessionLocal)
def update_location_map(location_id: int, map_update: Dict[str, Any], db: Session = None) -> Dict[str, Any]:
    """
    Updates the map data for a specific location.

    Args:
        location_id (int): The unique identifier of the location.
        map_update (Dict[str, Any]): The map data to update.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The updated location data.
    """
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

@with_db_session(we_db.SessionLocal)
def apply_status_to_npc(npc_id: int, status_id: str, db: Session = None) -> Dict[str, Any]:
    """
    Applies a status effect to an NPC.

    Args:
        npc_id (int): The unique identifier of the NPC.
        status_id (str): The status effect identifier.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
    try:
        updated_npc = we_crud.apply_status_to_npc(db, npc_id, status_id)
        if not updated_npc:
            raise Exception(f"NPC {npc_id} not found")
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.apply_status_to_npc] Error: {e}")
        raise

@with_db_session(we_db.SessionLocal)
def remove_status_from_npc(npc_id: int, status_id: str, db: Session = None) -> Dict[str, Any]:
    """
    Removes a status effect from an NPC.

    Args:
        npc_id (int): The unique identifier of the NPC.
        status_id (str): The status effect identifier to remove.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
    try:
        updated_npc = we_crud.remove_status_from_npc(db, npc_id, status_id)
        if not updated_npc:
            raise Exception(f"NPC {npc_id} not found")
        schema_npc = we_schemas.NpcInstance.from_orm(updated_npc)
        return schema_npc.model_dump()
    except Exception as e:
        logger.exception(f"[world.remove_status_from_npc] Error: {e}")
        raise


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

@with_db_session(we_db.SessionLocal)
def apply_composure_damage_to_npc(npc_id: int, damage_amount: int, db: Session = None) -> Dict[str, Any]:
    """
    Applies composure damage to an NPC.

    Args:
        npc_id (int): The unique identifier of the NPC.
        damage_amount (int): The amount of composure damage to apply.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
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

@with_db_session(we_db.SessionLocal)
def apply_composure_healing_to_npc(npc_id: int, amount: int, db: Session = None) -> Dict[str, Any]:
    """
    Applies composure healing to an NPC.

    Args:
        npc_id (int): The unique identifier of the NPC.
        amount (int): The amount of composure to restore.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
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

@with_db_session(we_db.SessionLocal)
def apply_temp_hp_to_npc(npc_id: int, amount: int, db: Session = None) -> Dict[str, Any]:
    """
    Applies temporary HP to an NPC.

    Does not stack; the higher value replaces the current one.

    Args:
        npc_id (int): The unique identifier of the NPC.
        amount (int): The amount of temporary HP to apply.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
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

@with_db_session(we_db.SessionLocal)
def update_npc_resource_pool(npc_id: int, pool_name: str, new_value: int, db: Session = None) -> Dict[str, Any]:
    """
    Updates a specific resource pool for an NPC.

    Args:
        npc_id (int): The unique identifier of the NPC.
        pool_name (str): The name of the resource pool.
        new_value (int): The new current value for the pool.
        db (Session): Injected database session.

    Returns:
        Dict[str, Any]: The updated NPC instance data.
    """
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



