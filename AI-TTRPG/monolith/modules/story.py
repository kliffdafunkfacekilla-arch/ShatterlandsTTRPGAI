# AI-TTRPG/monolith/modules/story.py
"""
Story adapter: Bridges the internal 'story_pkg' logic (combat,
interaction, etc.) into the monolith event bus.

This module subscribes to:
- command.story.start_combat
- command.story.interact
- command.story.advance_narrative
- command.story.player_action

And publishes story.* events returned by those handlers.
"""
from typing import Any, Dict
import asyncio
import logging
import httpx # Keep httpx for the *internal* async client pattern
from ..event_bus import get_event_bus

# Import from this module's *own* internal package
from .story_pkg import combat_handler as se_combat
from .story_pkg import interaction_handler as se_interaction
from .story_pkg import schemas as se_schemas
from .story_pkg import database as se_db
from .story_pkg import crud as se_crud
from .story_pkg import models as se_models

logger = logging.getLogger("monolith.story")

async def _on_command_start_combat(topic: str, payload: Dict[str, Any]) -> None:
    bus = get_event_bus()
    logger.info(f"[story] start_combat command received: {payload}")
    try:
        start_req = se_schemas.CombatStartRequest(**payload)
        db = se_db.SessionLocal()
        try:
            # --- THIS IS THE CHANGE: NO 'await' ---
            db_combat = se_combat.start_combat(db, start_req)
        finally:
            db.close()

        # ... (rest of the function is unchanged, await bus.publish is correct)
        participants = []
        for p in getattr(db_combat, "participants", []):
            participants.append({ "actor_id": p.actor_id, "actor_type": p.actor_type, "initiative_roll": getattr(p, "initiative_roll", 0) })
        await bus.publish("story.combat_initialized", {
            "combat_id": getattr(db_combat, "id", None), "location_id": getattr(db_combat, "location_id", None),
            "turn_order": getattr(db_combat, "turn_order", []), "current_turn_index": getattr(db_combat, "current_turn_index", 0),
            "participants": participants
        })
    except Exception as e:
        logger.exception(f"Failed to start combat: {e}")
        await bus.publish("story.combat_start_failed", {"error": str(e), "payload": payload})

async def _on_command_player_action(topic: str, payload: Dict[str, Any]) -> None:
    bus = get_event_bus()
    logger.info(f"[story] player_action command received: {payload}")
    # ... (payload validation unchanged) ...
    combat_id = payload.get("combat_id")
    actor_id = payload.get("actor_id")
    action_data = payload.get("action") or {}
    if combat_id is None or actor_id is None:
        await bus.publish("story.player_action_failed", {"error": "missing combat_id/actor_id", "payload": payload})
        return
    try:
        db = se_db.SessionLocal()
        try:
            combat = se_crud.get_combat_encounter(db, combat_id)
            if not combat:
                raise RuntimeError(f"Combat {combat_id} not found")
            action_req = se_schemas.PlayerActionRequest(**action_data)

            # --- THIS IS THE CHANGE: NO 'await' ---
            result = se_combat.handle_player_action(db, combat, actor_id, action_req)
        finally:
            db.close()
        await bus.publish("story.player_action_resolved", {"combat_id": combat_id, "result": result.model_dump() if hasattr(result, "model_dump") else result})
    except Exception as e:
        logger.exception(f"Error handling player action: {e}")
        await bus.publish("story.player_action_failed", {"error": str(e), "payload": payload})

async def _on_command_interact(topic: str, payload: Dict[str, Any]) -> None:
    bus = get_event_bus()
    logger.info(f"[story] interact command: {payload}")
    try:
        # (payload sanitation unchanged)
        sanitized = dict(payload)
        if "target_object_id" not in sanitized and "target_id" in sanitized:
            sanitized["target_object_id"] = sanitized.pop("target_id")
        if "actor_id" not in sanitized and "actor" in sanitized:
            sanitized["actor_id"] = sanitized.pop("actor")
        if "location_id" not in sanitized:
            sanitized["location_id"] = 1
        req = se_schemas.InteractionRequest(**sanitized)

        # --- THIS IS THE CHANGE: NO 'await' ---
        result = se_interaction.handle_interaction(req)

        resp = result.model_dump() if hasattr(result, "model_dump") else result
        await bus.publish("story.interaction_resolved", resp)
    except Exception as e:
        logger.exception(f"Interaction handling failed: {e}")
        await bus.publish("story.interaction_failed", {"error": str(e), "payload": payload})

async def _on_command_advance_narrative(topic: str, payload: Dict[str, Any]) -> None:
    bus = get_event_bus()
    logger.info(f"[story] advance_narrative command: {payload}")

    node_id = payload.get("node_id")
    # For now reuse the simple event to notify listeners;
    # A richer implementation could call story_pkg.crud to persist progress.
    await bus.publish("story.narrative_advanced", {"node_id": node_id, "timestamp": "now"})

def register(orchestrator) -> None:
    bus = get_event_bus()
    # subscribe to story commands
    asyncio.create_task(bus.subscribe("command.story.start_combat", _on_command_start_combat))
    asyncio.create_task(bus.subscribe("command.story.interact", _on_command_interact))
    asyncio.create_task(bus.subscribe("command.story.advance_narrative", _on_command_advance_narrative))
    asyncio.create_task(bus.subscribe("command.story.player_action", _on_command_player_action))
    logger.info("[story] module registered (self-contained logic)")
