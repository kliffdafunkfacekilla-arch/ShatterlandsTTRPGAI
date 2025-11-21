"""
Public API for the AI Dungeon Master module.
"""
import logging
from typing import Dict, Any

# Import from this module's own internal package
from .ai_dm_pkg import keyword_handler
from .ai_dm_pkg import llm_handler

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

        # 2. Call the LLM handler
        # We need to access the settings to get the API key.
        # Since this is a monolith module, we might not have direct access to the client's settings_manager easily
        # if we strictly follow the architecture, but for now we can try to load it or rely on env vars.
        
        # Ideally, the API key should be passed in or available via a config service.
        # For this implementation, we'll try to load the client settings file directly if possible,
        # or rely on the handler's fallback.
        
        import json
        import os
        from pathlib import Path
        
        api_key = None
        # Try to find settings.json relative to this file? No, that's brittle.
        # Let's assume the client has set the env var or we can find the file.
        # A robust way:
        try:
            # This path construction is a bit hacky but works for this project structure
            settings_path = Path(__file__).resolve().parent.parent.parent.parent / "game_client" / "settings.json"
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    api_key = settings.get("google_api_key")
        except Exception:
            pass

        response_message = llm_handler.generate_dm_response(
            prompt_text,
            char_context,
            loc_context,
            api_key=api_key
        )

        return {"success": True, "message": response_message}

    except Exception as e:
        logger.exception(f"AI DM failed to generate response: {e}")
        return {"success": False, "message": "An error occurred in the AI DM."}

def register(orchestrator) -> None:
    # This module is called directly, but we register it
    # to be consistent and allow it to subscribe to events later.
    logger.info("[ai_dm] module registered (keyword-based handler)")
