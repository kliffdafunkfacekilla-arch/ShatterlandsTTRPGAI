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

logger = logging.getLogger("monolith.world")

def get_world_location_context(location_id: int) -> Dict[str, Any]:
    # --- REMOVED ASYNC AND _client ---
    db = we_db.SessionLocal()
    try:
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
    finally:
        db.close()

def update_location_annotations(location_id: int, annotations: Dict[str, Any]) -> Dict[str, Any]:
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

def register(orchestrator) -> None:
    # This module doesn't subscribe to commands directly.
    # It's imported and called directly by other modules (like story.py)
    # for synchronous data queries.
    logger.info("[world] module registered (direct-call adapter)")
