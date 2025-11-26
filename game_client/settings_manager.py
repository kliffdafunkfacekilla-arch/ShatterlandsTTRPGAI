# game_client/settings_manager.py
"""
Handles loading and saving user settings from a JSON file.
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

# Use the same logic as asset_loader.py to find the client root
# This file is in 'game_client/', so its parent is the root.
try:
    CLIENT_ROOT = Path(__file__).resolve().parent
except NameError:
    # Fallback if __file__ isn't defined (e.g., in some frozen environments)
    CLIENT_ROOT = Path(os.getcwd())

SETTINGS_FILE = CLIENT_ROOT / "settings.json"

# Define the default settings structure
DEFAULT_SETTINGS = {
    "music_volume": 80,
    "sfx_volume": 100,
    "colorblind_mode": False,
    "reduce_flashing": False,
    "google_api_key": "",
    "last_active_character_id": None
}

def load_settings() -> Dict[str, Any]:
    """
    Loads settings from settings.json.
    If the file doesn't exist or is corrupt, it returns default settings.
    """
    if not os.path.exists(SETTINGS_FILE):
        logging.warning(f"Settings file not found at {SETTINGS_FILE}. Creating with defaults.")
        # Save defaults for next time
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS

    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)

        # Ensure all keys are present, add defaults if missing
        # This handles cases where we add new settings in an update
        missing_keys = False
        for key, value in DEFAULT_SETTINGS.items():
            if key not in settings:
                settings[key] = value
                missing_keys = True

        if missing_keys:
            logging.info("Settings file was missing keys. Adding defaults and re-saving.")
            save_settings(settings)

        logging.info(f"Settings loaded successfully from {SETTINGS_FILE}")
        return settings

    except json.JSONDecodeError:
        logging.error(f"Failed to read settings.json (corrupt?). Loading defaults and overwriting.")
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    except Exception as e:
        logging.error(f"Unexpected error loading settings: {e}. Loading defaults.")
        return DEFAULT_SETTINGS

def save_settings(settings_data: Dict[str, Any]):
    """
    Saves the provided settings dictionary to settings.json.
    """
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_data, f, indent=4)
        logging.info(f"Settings saved successfully to {SETTINGS_FILE}")
    except Exception as e:
        logging.error(f"Failed to save settings: {e}")
