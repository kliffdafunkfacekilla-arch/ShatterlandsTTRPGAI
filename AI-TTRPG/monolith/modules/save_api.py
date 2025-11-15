"""
Public-facing API for the Save/Load system.
The Kivy client imports and calls these synchronous functions.
"""
import logging
import glob
import os
import json
from typing import List, Dict, Any
# Import from this module's own internal package
from . import save_manager

logger = logging.getLogger("monolith.save_api")

def save_game(slot_name: str) -> Dict[str, Any]:
    """
    Saves the entire game state to a file.
    :param slot_name: The name for the save slot (e.g., "my_save_1").
    :return: A dictionary with {"success": True} or {"success": False, "error": ...}
    """
    if not slot_name:
        return {"success": False, "error": "Save name cannot be empty."}
    try:
        # Calls the internal manager function
        return save_manager._save_game_internal(slot_name)
    except Exception as e:
        logger.exception(f"save_api: Save game failed for slot '{slot_name}'")
        return {"success": False, "error": str(e)}

def load_game(slot_name: str) -> Dict[str, Any]:
    """
    Loads the entire game state from a file, wiping current state.
    :param slot_name: The name of the save slot to load.
    :return: A dictionary with {"success": True, "active_character_name": ...} or {"success": False, "error": ...}
    """
    if not slot_name:
        return {"success": False, "error": "Load name cannot be empty."}
    try:
        # Calls the internal manager function
        return save_manager._load_game_internal(slot_name)
    except Exception as e:
        logger.exception(f"save_api: Load game failed for slot '{slot_name}'")
        return {"success": False, "error": str(e)}

def list_save_games() -> List[Dict[str, str]]:
    """
    Scans the 'saves' directory and returns info for each save file.
    :return: A list of dictionaries, e.g., [{"name": "my_save_1", "time": "...", "char": "Tester"}]
    """
    save_files_info = []
    try:
        for filepath in glob.glob(os.path.join(save_manager.SAVE_DIR, "*.json")):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    save_files_info.append({
                        "name": data.get("save_name", os.path.basename(filepath)),
                        "time": data.get("save_time", "Unknown"),
                        "char": data.get("active_character_name", "Unknown")
                    })
            except Exception as e:
                logger.warning(f"Could not read save file {filepath}: {e}")

        # Sort by time, newest first
        save_files_info.sort(key=lambda x: x.get("time", ""), reverse=True)
        return save_files_info
    except Exception as e:
        logger.exception(f"Failed to list save games: {e}")
        return []

def register(orchestrator) -> None:
    # This module is called directly by the client,
    # so it just needs to be loaded.
    logger.info("[save_api] module registered (direct-call API)")
