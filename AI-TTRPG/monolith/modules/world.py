"""Adapter module for world_engine.

This module exposes a small set of async functions that mirror the
HTTP API the story_engine expects, but operate in-process by calling
into `world_engine.app.crud` with a local DB session.

Functions are intentionally thin wrappers so they can be awaited like
the original HTTP-based implementations.
"""
from typing import Any, Dict, Optional
from pathlib import Path
import asyncio
import logging

logger = logging.getLogger("monolith.world")


async def get_world_location_context(_client: Any, location_id: int) -> Dict[str, Any]:
    # Lazy import to avoid import cycles at module import time
    from world_engine.app import crud as we_crud
    from world_engine.app import database as we_db

    db = we_db.SessionLocal()
    try:
        ctx = we_crud.get_location_context(db, location_id)
        # Ensure generated_map_data is parsed if needed (keeps parity with HTTP)
        return ctx
    finally:
        db.close()


async def update_location_annotations(_client: Any, location_id: int, annotations: Dict[str, Any]) -> Dict[str, Any]:
    from world_engine.app import crud as we_crud
    from world_engine.app import database as we_db

    db = we_db.SessionLocal()
    try:
        updated = we_crud.update_location_annotations(db, location_id, annotations)
        return {"ai_annotations": getattr(updated, "ai_annotations", None)}
    finally:
        db.close()


async def spawn_npc_in_world(_client: Any, spawn_request: Any) -> Dict[str, Any]:
    """spawn_request may be a pydantic model or dict-like with fields matching NpcSpawnRequest"""
    from world_engine.app import crud as we_crud
    from world_engine.app import database as we_db
    from world_engine.app import schemas as we_schemas

    db = we_db.SessionLocal()
    try:
        # Accept dict or pydantic model
        if hasattr(spawn_request, "dict"):
            req_data = spawn_request.dict()
        else:
            req_data = dict(spawn_request)

        schema = we_schemas.NpcSpawnRequest(**req_data)
        npc = we_crud.spawn_npc(db, schema)
        # Return a dict similar to the HTTP response
        return {"id": getattr(npc, "id", None), "template_id": getattr(npc, "template_id", None)}
    finally:
        db.close()


async def get_npc_context(_client: Any, npc_instance_id: int) -> Dict[str, Any]:
    from world_engine.app import crud as we_crud
    from world_engine.app import database as we_db
    from world_engine.app import schemas as we_schemas

    db = we_db.SessionLocal()
    try:
        npc = we_crud.get_npc(db, npc_instance_id)
        if npc is None:
            raise Exception(f"NPC {npc_instance_id} not found")
        # Convert ORM to a simple dict similar to the HTTP API
        return we_schemas.NpcInstance.from_orm(npc).dict()
    finally:
        db.close()


def register(orchestrator) -> None:
    # world module currently doesn't subscribe to events; placeholder to match module API
    logger.info("[world] module registered")
