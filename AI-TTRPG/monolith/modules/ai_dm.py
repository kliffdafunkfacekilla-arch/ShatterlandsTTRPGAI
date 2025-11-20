"""
Public API for the AI Dungeon Master module.
"""
import logging
from typing import Dict, Any

# Import from this module's own internal package
from .ai_dm_pkg import keyword_handler

# Import monolith APIs to fetch context
from . import character as character_api
from . import world as world_api

logger = logging.getLogger("monolith.ai_dm")

def get_narrative_response(actor_id: str, prompt_text: str) -> Dict[str, Any]:
    """
    Generates a narrative response from the AI Dungeon Master based on a player's prompt.

    This function fetches the current context for the actor (character) and their location,
    then delegates the response generation to the keyword handler.

    Args:
        actor_id (str): The unique identifier of the actor (character) initiating the prompt.
        prompt_text (str): The text of the prompt or action provided by the player.

    Returns:
        Dict[str, Any]: A dictionary containing the success status and the generated message.
            - success (bool): True if the response was generated successfully, False otherwise.
            - message (str): The generated narrative response or an error message.
    """
    try:
        # 1. Fetch the necessary context
        char_context = character_api.get_character_context(actor_id)
        if not char_context:
            raise Exception(f"Could not get character context for {actor_id}")

        loc_id = char_context.get('current_location_id')
        loc_context = world_api.get_world_location_context(loc_id)
        if not loc_context:
             raise Exception(f"Could not get location context for {loc_id}")

        # 2. Call the keyword handler
        response_message = keyword_handler.get_keyword_response(
            prompt_text,
            char_context,
            loc_context
        )

        return {"success": True, "message": response_message}

    except Exception as e:
        logger.exception(f"AI DM failed to generate response: {e}")
        return {"success": False, "message": "An error occurred in the AI DM."}

def register(orchestrator) -> None:
    """
    Registers the AI DM module with the orchestrator.

    This function is called during the monolith startup sequence. Although this module
    is primarily called directly via its API, registration allows for potential future
    event subscriptions.

    Args:
        orchestrator: The system orchestrator instance (not currently used but required by the interface).
    """
    # This module is called directly, but we register it
    # to be consistent and allow it to subscribe to events later.
    logger.info("[ai_dm] module registered (keyword-based handler)")
