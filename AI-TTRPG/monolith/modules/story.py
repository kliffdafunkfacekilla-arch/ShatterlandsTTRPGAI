"""
Story adapter: Bridges the internal 'story_pkg' logic (combat, interaction, etc.) into the monolith event bus.

Provides synchronous API functions for the Kivy client and registers async event bus handlers.
"""
import logging
import asyncio
from typing import Any, Dict, List
from ..event_bus import get_event_bus

# Internal package imports
from .story_pkg import combat_handler as se_combat
from .story_pkg import interaction_handler as se_interaction
from .story_pkg import schemas as se_schemas
from .story_pkg import dialogue_handler as se_dialogue
from .story_pkg import shop_handler as se_shop
from .rules_pkg import experience_handler as se_experience
from .camp_pkg import services as camp_services
from .camp_pkg import schemas as camp_schemas
from .story_pkg import database as se_db
from .story_pkg import crud as se_crud
from .story_pkg import models as se_models
from .story_pkg import director # Import the director
from . import ai_dm
# from ..simulation import run_simulation_turn # This relative import is failing in tests
# We can import it from the module if we are running from monolith root
from . import simulation # It is in the same directory 'modules'
from ..orchestrator import get_orchestrator
from .character_pkg import services as character_api

logger = logging.getLogger("monolith.story")

# ---------------------------------------------------------------------------
# Core synchronous API functions
# ---------------------------------------------------------------------------

def add_experience(char_id: str, xp_amount: int) -> Dict[str, Any]:
    """Add experience points to a character and return updated context."""
    logger.info(f"[story.sync] add_experience command received: char={char_id}, xp={xp_amount}")
    db = se_db.SessionLocal()
    try:
        updated_char = se_experience.add_experience(db, char_id, xp_amount)
        from .character_pkg import services as char_services
        return char_services.get_character_context(db, updated_char).model_dump()
    except Exception as e:
        logger.exception(f"Failed to add experience: {e}")
        raise
    finally:
        db.close()

def get_shop_inventory(shop_id: str) -> Dict[str, Any]:
    """Retrieve inventory for a specific shop."""
    logger.info(f"[story.sync] get_shop_inventory command received: shop_id={shop_id}")
    try:
        return se_shop.get_shop_inventory(shop_id)
    except Exception as e:
        logger.exception(f"Failed to get shop inventory: {e}")
        raise

def buy_item(char_id: str, shop_id: str, item_id: str, quantity: int) -> Dict[str, Any]:
    """Buy an item from a shop for a character."""
    logger.info(f"[story.sync] buy_item command received: char={char_id}, shop={shop_id}, item={item_id}, qty={quantity}")
    db = se_db.SessionLocal()
    try:
        updated_context = se_shop.buy_item(db, char_id, shop_id, item_id, quantity)
        return updated_context.model_dump()
    except Exception as e:
        logger.exception(f"Failed to buy item: {e}")
        raise
    finally:
        db.close()

def sell_item(char_id: str, shop_id: str, item_id: str, quantity: int) -> Dict[str, Any]:
    """Sell an item to a shop for a character."""
    logger.info(f"[story.sync] sell_item command received: char={char_id}, shop={shop_id}, item={item_id}, qty={quantity}")
    db = se_db.SessionLocal()
    try:
        updated_context = se_shop.sell_item(db, char_id, shop_id, item_id, quantity)
        return updated_context.model_dump()
    except Exception as e:
        logger.exception(f"Failed to sell item: {e}")
        raise
    finally:
        db.close()

def get_dialogue_node(dialogue_id: str, node_id: str) -> Dict[str, Any]:
    """Retrieve a specific node from a dialogue tree."""
    logger.info(f"[story.sync] get_dialogue_node command received: dialogue={dialogue_id}, node={node_id}")
    try:
        return se_dialogue.get_dialogue_node(dialogue_id, node_id)
    except Exception as e:
        logger.exception(f"Failed to get dialogue node: {e}")
        raise

def handle_player_action(combat_id: int, actor_id: str, action: se_schemas.PlayerActionRequest) -> Dict[str, Any]:
    """Process a player's combat action."""
    logger.info(f"[story.sync] player_action command received for combat {combat_id}: {actor_id}")
    db = se_db.SessionLocal()
    try:
        combat = se_crud.get_combat_encounter(db, combat_id)
        if not combat:
            raise RuntimeError(f"Combat {combat_id} not found")
        result_schema = se_combat.handle_player_action(db, combat, actor_id, action)
        return result_schema.model_dump()
    except Exception as e:
        logger.exception(f"Error handling player action: {e}")
        raise
    finally:
        db.close()

def get_combat_state(combat_id: int) -> Dict[str, Any]:
    """Retrieve the current state of a combat encounter."""
    logger.info(f"[story.sync] get_combat_state command received: {combat_id}")
    db = se_db.SessionLocal()
    try:
        combat = se_crud.get_combat_encounter(db, combat_id)
        if not combat:
            raise RuntimeError(f"Combat {combat_id} not found")
        
        participants = []
        for p in combat.participants:
            participants.append({
                "actor_id": p.actor_id,
                "actor_type": p.actor_type,
                "initiative_roll": p.initiative_roll,
                "team": p.team
            })
            
        return {
            "id": combat.id,
            "location_id": combat.location_id,
            "status": combat.status,
            "turn_order": combat.turn_order,
            "current_turn_index": combat.current_turn_index,
            "participants": participants,
            "log": [] 
        }
    except Exception as e:
        logger.exception(f"Error getting combat state: {e}")
        raise
    finally:
        db.close()

def handle_npc_action(combat_id: int) -> Dict[str, Any]:
    """Determine and execute an NPC action for the current turn."""
    logger.info(f"[story.sync] handle_npc_action command received for combat {combat_id}")
    db = se_db.SessionLocal()
    try:
        combat = se_crud.get_combat_encounter(db, combat_id)
        if not combat:
            raise RuntimeError(f"Combat {combat_id} not found")
        current_actor_id = combat.turn_order[combat.current_turn_index]
        if not current_actor_id.startswith("npc_"):
            raise RuntimeError(f"It is not an NPC's turn. Actor: {current_actor_id}")
        action_request = se_combat.determine_npc_action(db, combat, current_actor_id)
        if action_request is None:
            result_schema = se_combat.handle_no_action(db, combat, current_actor_id, reason="is processing...")
        else:
            result_schema = se_combat.handle_player_action(db, combat, current_actor_id, action_request)
        return result_schema.model_dump()
    except Exception as e:
        logger.exception(f"Error handling NPC action: {e}")
        raise
    finally:
        db.close()

def get_active_quest_requirements(location_id: int) -> Dict[str, Any]:
    """
    Returns a map injection request if any active quest requires items/NPCs in this location.
    """
    db = se_db.SessionLocal()
    try:
        quests = se_crud.get_all_quests(db, campaign_id=1) # MVP assumption

        required_items = []
        required_npcs = []

        if quests:
            for q in quests:
                # Filter logic: Only inject if quest is active and targeted at this location
                # Since we don't have location_id on quest, we rely on tags/description
                # Or we inject globally for MVP but only if "inject" keyword is present

                desc = q.description or ""

                # Improved parsing: check for location constraint in description
                # syntax: "loc:123 inject_item:xyz"
                # If no loc specified, inject globally (or assume global quest)

                target_loc = None
                if "loc:" in desc:
                    try:
                        parts = desc.split("loc:")
                        target_loc_str = parts[1].split()[0].strip()
                        target_loc = int(target_loc_str)
                    except:
                        pass

                if target_loc is not None and target_loc != location_id:
                    continue # Skip if not for this location

                # Look for items
                if "inject_item:" in desc:
                    parts = desc.split("inject_item:")
                    if len(parts) > 1:
                        item_id = parts[1].split()[0].strip()
                        required_items.append(item_id)

                # Look for NPCs
                if "inject_npc:" in desc:
                    parts = desc.split("inject_npc:")
                    if len(parts) > 1:
                        npc_id = parts[1].split()[0].strip()
                        required_npcs.append(npc_id)

        if required_items or required_npcs:
            return {
                "required_item_ids": required_items,
                "required_npc_ids": required_npcs,
                "atmosphere_tags": ["quest_active"]
            }
        return None
    finally:
        db.close()

def handle_interaction(request: se_schemas.InteractionRequest) -> Dict[str, Any]:
    """Handle an interaction request between an actor and a target object."""
    logger.info(f"[story.sync] Handling interaction: Actor '{request.actor_id}' -> Target '{request.target_object_id}'")

    # --- DIRECTOR HOOK: Check for Story Seed ---
    try:
        if request.target_object_id.startswith("seed_"):
            # This is a story seed interaction
            # We assume campaign_id=1 for single player MVP, or we'd fetch from actor context
            db = se_db.SessionLocal()
            try:
                camp_director = director.get_director(db, campaign_id=1)
                generated_quest = camp_director.resolve_seed(request.target_object_id)

                # Format response as a narrative message
                # In a full impl, this would create the quest in DB and notify client.
                return {
                    "success": True,
                    "message": f"QUEST TRIGGERED: {generated_quest['title']}\n{generated_quest['description']}",
                    "updated_annotations": {"quest_data": generated_quest}
                }
            finally:
                db.close()
    except Exception as e:
        logger.error(f"Director hook failed: {e}")
    # -------------------------------------------

    try:
        response_model = se_interaction.handle_interaction(request)
        return response_model.model_dump()
    except Exception as e:
        logger.exception(f"[story.sync] Interaction handling failed: {e}")
        return {"success": False, "message": f"An unexpected error occurred: {e}"}

def get_all_quests(campaign_id: int) -> List[Dict[str, Any]]:
    """Retrieve all active quests for a campaign."""
    db = se_db.SessionLocal()
    try:
        db_quests = se_crud.get_all_quests(db, campaign_id)
        return [se_schemas.ActiveQuest.from_orm(q).model_dump() for q in db_quests]
    finally:
        db.close()

def rest_at_camp(rest_request: camp_schemas.CampRestRequest) -> Dict[str, Any]:
    """Process a camp rest action for a character."""
    logger.info(f"[story.sync] rest_at_camp command received: {rest_request.model_dump_json(indent=2)}")
    db = se_db.SessionLocal()
    try:
        updated_character_context = camp_services.rest_at_camp(db, rest_request)
        return updated_character_context.model_dump()
    except Exception as e:
        logger.exception(f"Failed to rest at camp: {e}")
        raise
    finally:
        db.close()

def handle_narrative_prompt(actor_id: str, prompt_text: str) -> Dict[str, Any]:
    """Generate a narrative response using intent classification and deterministic routing.
    
    This function implements the AI gatekeeper pattern:
    1. Classify intent using lightweight keyword matching
    2. Route deterministic actions to coded logic
    3. Only call expensive AI for truly narrative/creative requests
    """
    logger.info(f"[story.sync] Narrative prompt from {actor_id}: {prompt_text}")
    try:
        # Import here to avoid circular dependency
        from .ai_dm_pkg.keyword_handler import classify_intent
        
        # Step 1: Intent Classification (Deterministic Filter)
        action_intent = classify_intent(prompt_text)
        logger.debug(f"[story.sync] Intent classified as: {action_intent.intent_type}, deterministic={action_intent.is_deterministic}")
        
        # Step 2: Deterministic Routing for known actions
        if action_intent.is_deterministic:
            intent_type = action_intent.intent_type
            
            if intent_type == "combat_action":
                # Player typed something like "I attack the goblin"
                # In production, this would parse the target and route to combat handler
                return {"success": True, "message": "[Deterministic Combat Action] Use the combat system to attack."}
            
            elif intent_type == "shop_interaction":
                # Player typed "buy potion" or similar
                return {"success": True, "message": "[Deterministic Shop Action] Use the shop interface to trade."}
            
            elif intent_type == "inspect_item":
                # Player typed "examine door" or similar
                return {"success": True, "message": "[Deterministic Inspect] Use the inspect command to examine objects."}
            
            elif intent_type == "dialogue_action":
                # Player typed "talk to guard" or similar
                return {"success": True, "message": "[Deterministic Dialogue] Use the dialogue system to speak with NPCs."}
            
            # If we reach here with a deterministic flag but no handler, log warning
            logger.warning(f"[story.sync] Deterministic intent '{intent_type}' has no handler, falling back to AI")
        
        # Step 3: AI Gatekeeper (Legacy check for backward compatibility)
        orchestrator = get_orchestrator()
        if not orchestrator.should_ai_be_called(action_intent.action_tags):
            return {"success": True, "message": "[Simple Query] No AI needed for this request."}
        
        # Step 4: Call expensive AI-DM only for narrative/creative requests
        logger.info(f"[story.sync] Invoking AI-DM for narrative request")
        response = ai_dm.get_narrative_response(actor_id, prompt_text)
        return response
        
    except Exception as e:
        logger.exception(f"Call to AI DM module failed: {e}")
        return {"success": False, "message": "The world feels unresponsive..."}

# ---------------------------------------------------------------------------
# Async event bus registration (internal use)
# ---------------------------------------------------------------------------
async def _on_command_start_combat(topic: str, payload: Dict[str, Any]) -> None:
    bus = get_event_bus()
    logger.info(f"[story] (async) start_combat command received: {payload}")
    try:
        start_req = se_schemas.CombatStartRequest(**payload)
        db = se_db.SessionLocal()
        try:
            db_combat = se_combat.start_combat(db, start_req)
        finally:
            db.close()
        participants = []
        for p in getattr(db_combat, "participants", []):
            participants.append({"actor_id": p.actor_id, "actor_type": p.actor_type, "initiative_roll": getattr(p, "initiative_roll", 0)})
        await bus.publish("story.combat_initialized", {
            "combat_id": getattr(db_combat, "id", None),
            "location_id": getattr(db_combat, "location_id", None),
            "turn_order": getattr(db_combat, "turn_order", []),
            "current_turn_index": getattr(db_combat, "current_turn_index", 0),
            "participants": participants,
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
            sanitiz_loc = 1
            try:
                actor_ctx = character_api.get_character_context(sanitized["actor_id"])
                sanitiz_loc = actor_ctx.get("current_location_id", 1)
            except Exception:
                pass
            sanitized["location_id"] = sanitiz_loc
        req = se_schemas.InteractionRequest(**sanitized)
        resp = handle_interaction(req)
        await bus.publish("story.interaction_resolved", resp)
    except Exception as e:
        logger.exception(f"Interaction handling failed: {e}")
        await bus.publish("story.interaction_failed", {"error": str(e), "payload": payload})

async def _on_command_advance_narrative(topic: str, payload: Dict[str, Any]) -> None:
    bus = get_event_bus()
    logger.info(f"[story] (async) advance_narrative command: {payload}")
    node_id = payload.get("node_id")

    # --- Integration Hook: Quest Completion / Narrative Advance ---
    # Simplified trigger: If node_id indicates completion
    if node_id and "complete" in node_id:
        db = se_db.SessionLocal()
        try:
             camp_director = director.get_director(db, campaign_id=1)
             camp_director.record_event(f"Narrative Advanced: {node_id}")

             # Trigger Simulation Turn
             events = simulation.run_simulation_turn()
             logger.info(f"Simulation Turn Processed: {events}")

             # Check if we need to generate new beat?
             # Handled by next interaction usually or explicit check
        finally:
             db.close()

    await bus.publish("story.narrative_advanced", {"node_id": node_id, "timestamp": "now"})

def register(orchestrator) -> None:
    bus = get_event_bus()
    asyncio.create_task(bus.subscribe("command.story.start_combat", _on_command_start_combat))
    asyncio.create_task(bus.subscribe("command.story.interact", _on_command_interact))
    asyncio.create_task(bus.subscribe("command.story.advance_narrative", _on_command_advance_narrative))
    asyncio.create_task(bus.subscribe("command.story.player_action", _on_command_player_action))
    logger.info("[story] module registered (sync API and async bus)")