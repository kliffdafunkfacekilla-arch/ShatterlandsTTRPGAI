import sys
import os
from pathlib import Path

# Setup Kivy headless
os.environ["KIVY_NO_CONSOLELOG"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"
import kivy
from kivy.core.image import Image as CoreImage

# Add game_client to path
sys.path.insert(0, str(Path.cwd()))

try:
    from game_client import asset_loader
    
    print("Initializing Assets...")
    asset_loader.initialize_assets()
    
    print(f"Loaded {len(asset_loader.ENTITY_DEFINITIONS)} entities.")
    if "character_2" in asset_loader.ENTITY_DEFINITIONS:
        print("  'character_2' found in definitions.")
        print(f"  Data: {asset_loader.ENTITY_DEFINITIONS['character_2']}")
    else:
        print("  'character_2' NOT found in definitions.")
        print(f"  Keys: {list(asset_loader.ENTITY_DEFINITIONS.keys())}")
    
    print("\nChecking 'character_2'...")
    info = asset_loader.get_sprite_render_info("character_2")
    
    if info:
        sheet_path, u, v, u2, v2 = info
        print(f"  Resolved to: {sheet_path}")
        print(f"  Coords: {u}, {v}, {u2}, {v2}")
        
        tex = asset_loader.get_texture(str(sheet_path))
        if tex:
            print("  [OK] Texture loaded successfully.")
        else:
            print("  [FAIL] Texture failed to load.")
    else:
        print("  [FAIL] Could not resolve 'character_2'")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
