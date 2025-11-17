# AI-TTRPG/monolith/modules/story.py
"""
Story adapter: Bridges the internal 'story_pkg' logic (combat,
interaction, etc.) into the monolith event bus.

This module is the primary synchronous API endpoint for the Kivy client.
"""
from typing import Any, Dict, List
import asyncio
import logging
import httpx # This import is no longer used but safe to keep
from ..event_bus import get_event_bus

# Import from this module's *own* internal package
from .story_pkg import combat_handler as se_combat
from .story_pkg import interaction_handler as se_interaction
from .story_pkg import schemas as se_schemas
from .story_pkg import database as se_db
from .story_pkg import crud as se_crud
from .story_pkg import models as se_models
from . import ai_dm

logger = logging.getLogger("monolith.story")

# --- NEW SYNCHRONOUS COMBAT API FUNCTIONS ---

def start_combat(start_request: se_schemas.CombatStartRequest) -> Dict[str, Any]:
    """
    Synchronous API for the client to start a combat encounter.
    """
    logger.info(f"[story.sync] start_combat command received: {start_request.model_dump_json(indent=2)}")
    db = se_db.SessionLocal()
    try:
        # Call the (now synchronous) combat handler function
        db_combat = se_combat.start_combat(db, start_request)

        # Manually build the response dictionary from the DB model
        participants = []
        for p in getattr(db_combat, "participants", []):
            participants.append({
                "actor_id": p.actor_id,
                "actor_type": p.actor_type,
                "initiative_roll": getattr(p, "initiative_roll", 0)
            })

        response = {
            "id": getattr(db_combat, "id", None),
            "location_id": getattr(db_combat, "location_id", None),
            "status": getattr(db_combat, "status", "error"),
            "turn_order": getattr(db_combat, "turn_order", []),
            "current_turn_index": getattr(db_combat, "current_turn_index", 0),
            "participants": participants
        }
        return response

    except Exception as e:
        logger.exception(f"Failed to start combat: {e}")
        raise # Re-raise the exception so the client knows it failed
    finally:
        db.close()

def handle_player_action(combat_id: int, actor_id: str, action: se_schemas.PlayerActionRequest) -> Dict[str, Any]:
    """
    Synchronous API for the client to submit a player action.
    """
    logger.info(f"[story.sync] player_action command received for combat {combat_id}: {actor_id}")
    db = se_db.SessionLocal()
    try:
        combat = se_crud.get_combat_encounter(db, combat_id)
        if not combat:
            raise RuntimeError(f"Combat {combat_id} not found")

        # Call the (now synchronous) combat handler function
        result_schema = se_combat.handle_player_action(db, combat, actor_id, action)
        return result_schema.model_dump()

    except Exception as e:
        logger.exception(f"Error handling player action: {e}")
        raise
    finally:
        db.close()

def handle_npc_action(combat_id: int) -> Dict[str, Any]:
    """
    Synchronous API for the client to trigger an NPC's turn.
    """
    logger.info(f"[story.sync] handle_npc_action command received for combat {combat_id}")
    db = se_db.SessionLocal()
    try:
        combat = se_crud.get_combat_encounter(db, combat_id)
        if not combat:
            raise RuntimeError(f"Combat {combat_id} not found")

        current_actor_id = combat.turn_order[combat.current_turn_index]
        if not current_actor_id.startswith("npc_"):
             raise RuntimeError(f"It is not an NPC's turn. Actor: {current_actor_id}")

        # 1. Determine the action
        action_request = se_combat.determine_npc_action(db, combat, current_actor_id)

        # 2. Execute the action
        if action_request is None:
            # NPC chose to wait or is Staggered
            result_schema = se_combat.handle_no_action(db, combat, current_actor_id, reason="is processing...")
        else:
            result_schema = se_combat.handle_player_action(db, combat, current_actor_id, action_request)

        return result_schema.model_dump()

    except Exception as e:
        logger.exception(f"Error handling NPC action: {e}")
        raise
    finally:
        db.close()


# --- EXISTING NARRATIVE/INTERACTION FUNCTIONS ---

def handle_interaction(request: se_schemas.InteractionRequest) -> Dict[str, Any]:
    """
    Synchronous wrapper for the interaction handler.
    This is called directly by other modules (like the Kivy client).
    """
    logger.info(f"[story.sync] Handling interaction: Actor '{request.actor_id}' -> Target '{request.target_object_id}'")
    try:
        response_model = se_interaction.handle_interaction(request)
        return response_model.model_dump()
    except Exception as e:
        logger.exception(f"[story.sync] Interaction handling failed: {e}")
        return {
            "success": False,
            "message": f"An unexpected error occurred: {e}",
            "updated_annotations": None,
            "items_added": None,
            "items_removed": None,
        }

def handle_narrative_prompt(actor_id: str, prompt_text: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for the AI DM narration.
    This is called directly by other modules (like the Kivy client).
    """
    logger.info(f"[story.sync] Narrative prompt from {actor_id}: {prompt_text}")
    try:
        response = ai_dm.get_narrative_response(actor_id, prompt_text)
        return response
    except Exception as e:
        logger.exception(f"Call to AI DM module failed: {e}")
        return {"success": False, "message": "The world feels unresponsive..."}

def get_all_quests(campaign_id: int) -> List[Dict[str, Any]]:
    """Retrieves all active quests for a campaign."""
    db = se_db.SessionLocal()
    try:
        db_quests = se_crud.get_all_quests(db, campaign_id)
        return [se_schemas.ActiveQuest.from_orm(q).model_dump() for q in db_quests]
    finally:
        db.close()


# --- ASYNC EVENT BUS REGISTRATION (Unused by client, for internal monolith) ---

async def _on_command_start_combat(topic: str, payload: Dict[str, Any]) -> None:
    bus = get_event_bus()
    logger.info(f"[story] (async) start_combat command received: {payload}")
    try:
        start_req = se_schemas.CombatStartRequest(**payload)
        # This is async, but we can't call our new sync function.
        # This async path is for *internal* module calls, not the client.
        db = se_db.SessionLocal()
        try:
            db_combat = se_combat.start_combat(db, start_req)
        finally:
            db.close()

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
    logger.info(f"[story] (async) player_action command received: {payload}")
    combat_id = payload.get("combat_id")
    actor_id = payload.get("actor_id")
    action_data = payload.get("action") or {}
    if combat_id is None or actor_id is None:
        await bus.publish("story.player_action_failed", {"error": "missing combat_id/actor_id", "payload": payload})
        return
    try:
        action_req = se_schemas.PlayerActionRequest(**action_data)
        # Call the *synchronous* API function
        result_dict = handle_player_action(combat_id, actor_id, action_req)

        await bus.publish("story.player_action_resolved", {"combat_id": combat_id, "result": result_dict})
    except Exception as e:
        logger.exception(f"Error handling player action: {e}")
        await bus.publish("story.player_action_failed", {"error": str(e), "payload": payload})

async def _on_command_interact(topic: str, payload: Dict[str, Any]) -> None:
    bus = get_event_bus()
    logger.info(f"[story] (async) interact command: {payload}")
    try:
        sanitized = dict(payload)
        if "target_object_id" not in sanitized and "target_id" in sanitized:
            sanitized["target_object_id"] = sanitized.pop("target_id")
        if "actor_id" not in sanitized and "actor" in sanitized:
            sanitized["actor_id"] = sanitized.pop("actor")
        if "location_id" not in sanitized:
            sanitiz_loc = 1 # Fallback
            # Try to get location from actor
            try:
                actor_ctx = character_api.get_character_context(sanitized["actor_id"])
                sanitiz_loc = actor_ctx.get("current_location_id", 1)
            except Exception:
                pass # Use fallback
            sanitized["location_id"] = sanitiz_loc

        req = se_schemas.InteractionRequest(**sanitized)

        # Call the *synchronous* API function
        resp = handle_interaction(req)
        await bus.publish("story.interaction_resolved", resp)
    except Exception as e:
        logger.exception(f"Interaction handling failed: {e}")
        await bus.publish("story.interaction_failed", {"error": str(e), "payload": payload})

async def _on_command_advance_narrative(topic: str, payload: Dict[str, Any]) -> None:
    bus = get_event_bus()
    logger.info(f"[story] (async) advance_narrative command: {payload}")
    node_id = payload.get("node_id")
    await bus.publish("story.narrative_advanced", {"node_id": node_id, "timestamp": "now"})

def register(orchestrator) -> None:
    bus = get_event_bus()
    # subscribe to story commands
    asyncio.create_task(bus.subscribe("command.story.start_combat", _on_command_start_combat))
    asyncio.create_task(bus.subscribe("command.story.interact", _on_command_interact))
    asyncio.create_task(bus.subscribe("command.story.advance_narrative", _on_command_advance_narrative))
    asyncio.create_task(bus.subscribe("command.story.player_action", _on_command_player_action))
    logger.info("[story] module registered (sync API and async bus)")