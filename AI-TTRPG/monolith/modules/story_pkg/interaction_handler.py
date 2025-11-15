# AI-TTRPG/story_engine/app/interaction_handler.py
import httpx
from fastapi import HTTPException
from typing import Dict, Any, Tuple, Optional, List
from . import schemas, services
import logging

logger = logging.getLogger("uvicorn.error")

def handle_interaction(request: schemas.InteractionRequest) -> schemas.InteractionResponse:
    """
    Handles player interactions with objects based on world state annotations.
    NOW SYNCHRONOUS.
    """
    logger.info(f"Handling interaction: Actor '{request.actor_id}' -> Target '{request.target_object_id}' in Loc {request.location_id}")

    try:
        # 1. Get Location Context (including annotations)
        # --- REMOVED AWAIT ---
        location_context = services.get_world_location_context(request.location_id)
        annotations = location_context.get("ai_annotations")

        if annotations is None:
            logger.warning(f"Location {request.location_id} has no AI annotations.")
            return schemas.InteractionResponse(success=False, message="There are no interactable objects here.")

        target_object_state = annotations.get(request.target_object_id)

        if target_object_state is None:
            return schemas.InteractionResponse(success=False, message=f"You don't see a '{request.target_object_id}' here to interact with.")

        # 2. Process Interaction based on Type and Object State
        if request.interaction_type == "use" and isinstance(target_object_state, dict) and target_object_state.get("type") == "door":
            if target_object_state.get("status") == "locked":
                has_key = False
                key_needed = target_object_state.get("key_id")

                if key_needed:
                    logger.info(f"Door requires key: {key_needed}. Checking {request.actor_id}'s inventory.")
                    try:
                        # --- REMOVED AWAIT ---
                        char_context = services.get_character_context(request.actor_id)
                        inventory = char_context.get("inventory", {})
                        has_key = inventory.get(key_needed, 0) > 0
                    except Exception as e:
                        logger.exception(f"Unexpected error during inventory check for key {key_needed}: {e}")

                if has_key:
                    target_object_state["status"] = "unlocked"
                    logger.info(f"Door '{request.target_object_id}' unlocked by {request.actor_id}.")
                    items_removed_list = []
                    try:
                        # --- REMOVED AWAIT ---
                        services.remove_item_from_character(request.actor_id, key_needed, 1)
                        items_removed_list.append({"item_id": key_needed, "quantity": 1})
                    except Exception as e:
                        logger.error(f"Failed to remove key {key_needed} after use: {e}. Door is unlocked anyway.")

                    # --- REMOVED AWAIT ---
                    updated_context = services.update_location_annotations(request.location_id, annotations)
                    return schemas.InteractionResponse(
                        success=True,
                        message=f"You use the {key_needed.replace('_', ' ')} and unlock the {request.target_object_id.replace('_', ' ')}.",
                        updated_annotations=updated_context.get("ai_annotations"),
                        items_removed=items_removed_list
                    )
                else:
                    return schemas.InteractionResponse(success=False, message=f"The {request.target_object_id.replace('_', ' ')} is locked." + (f" It seems to require a '{key_needed}'." if key_needed else ""))

            elif target_object_state.get("status") in ("unlocked", "closed"):
                target_object_state["status"] = "open"
                # --- REMOVED AWAIT ---
                updated_context = services.update_location_annotations(request.location_id, annotations)
                return schemas.InteractionResponse(
                    success=True,
                    message=f"You open the {request.target_object_id.replace('_', ' ')}.",
                    updated_annotations=updated_context.get("ai_annotations")
                )
            # ... (rest of door logic is the same, just remove 'await')
            elif target_object_state.get("status") == "open":
                target_object_state["status"] = "closed"
                updated_context = services.update_location_annotations(request.location_id, annotations)
                return schemas.InteractionResponse(
                    success=True,
                    message=f"You close the {request.target_object_id.replace('_', ' ')}.",
                    updated_annotations=updated_context.get("ai_annotations")
                )
            else:
                return schemas.InteractionResponse(success=False, message="You can't use the door that way right now.")

        elif request.interaction_type == "use" and isinstance(target_object_state, dict) and target_object_state.get("type") == "item_pickup":
            item_id_to_give = target_object_state.get("item_id")
            quantity = target_object_state.get("quantity", 1)
            if not item_id_to_give:
                return schemas.InteractionResponse(success=False, message="There's nothing here to pick up.")
            try:
                # --- REMOVED AWAIT ---
                services.add_item_to_character(request.actor_id, item_id_to_give, quantity)
                del annotations[request.target_object_id]
                updated_context = services.update_location_annotations(request.location_id, annotations)
                return schemas.InteractionResponse(
                    success=True,
                    message=f"You pick up the {request.target_object_id.replace('_', ' ')} ({item_id_to_give} x{quantity}).",
                    updated_annotations=updated_context.get("ai_annotations"),
                    items_added=[{"item_id": item_id_to_give, "quantity": quantity}]
                )
            except Exception as e:
                logger.error(f"Failed to add item {item_id_to_give} to {request.actor_id}: {e}")
                return schemas.InteractionResponse(success=False, message="You couldn't pick that up.")
        else:
            return schemas.InteractionResponse(success=False, message=f"You're not sure how to '{request.interaction_type}' the {request.target_object_id.replace('_', ' ')}.")

    except HTTPException as he:
        logger.error(f"HTTPException during interaction: {he.detail}")
        return schemas.InteractionResponse(success=False, message=f"An error occurred: {he.detail}")
    except Exception as e:
        logger.exception(f"Unexpected error during interaction: {e}")
        return schemas.InteractionResponse(success=False, message="An unexpected error occurred during the interaction.")