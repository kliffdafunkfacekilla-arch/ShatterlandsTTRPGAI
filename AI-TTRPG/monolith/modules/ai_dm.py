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
    The main entry point for the AI DM.
    It fetches context and calls the handler to get a response.
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
    # This module is called directly, but we register it
    # to be consistent and allow it to subscribe to events later.
    logger.info("[ai_dm] module registered (keyword-based handler)")
