import sys
import os
import logging
from pathlib import Path

# Setup paths
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

# Mock Kivy CoreImage to avoid window creation
from unittest.mock import MagicMock
import kivy.core.image
kivy.core.image.Image = MagicMock()

# Configure logging
logging.basicConfig(level=logging.INFO)

from game_client import asset_loader

def debug_assets():
    print("--- Debugging Asset Loader ---")
    asset_loader.initialize_assets()
    
    entity_id = "character_2"
    print(f"Looking up: {entity_id}")
    
    info = asset_loader.get_sprite_render_info(entity_id)
    if info:
        path, x, y, x2, y2 = info
        print(f"SUCCESS: Found render info for {entity_id}")
        print(f"  Path: {path}")
        print(f"  Coords: ({x}, {y}, {x2}, {y2})")
        
        # Check if file exists
        if os.path.exists(path):
            print("  File exists on disk.")
        else:
            print("  ERROR: File does NOT exist on disk.")
    else:
        print(f"FAILURE: Could not resolve {entity_id}")

if __name__ == "__main__":
    debug_assets()
