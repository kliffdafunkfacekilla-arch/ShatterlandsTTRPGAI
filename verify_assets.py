import os
import sys
from pathlib import Path

# Setup Kivy headless
os.environ["KIVY_NO_CONSOLELOG"] = "1"
os.environ["KIVY_NO_ARGS"] = "1"
import kivy
from kivy.core.image import Image as CoreImage

# Setup paths
CLIENT_ROOT = Path("game_client").resolve()
ASSETS_DIR = CLIENT_ROOT / "assets"
GFX_DIR = ASSETS_DIR / "graphics"
TILES_DIR = GFX_DIR / "tiles"
ENTITIES_DIR = GFX_DIR / "entities"

def test_load_image(path):
    print(f"Testing: {path}")
    if not path.exists():
        print(f"  [MISSING] File does not exist: {path}")
        return False
        
    try:
        img = CoreImage(str(path))
        if img:
            print(f"  [OK] Loaded successfully. Size: {img.size}")
            return True
        else:
            print(f"  [FAIL] CoreImage returned None")
            return False
    except Exception as e:
        print(f"  [CRASH] {e}")
        return False

def main():
    print(f"Checking assets in: {ASSETS_DIR}")
    
    # Check Tiles
    print("\n--- Checking Tiles ---")
    tiles = [
        TILES_DIR / "outdoor_tiles_1.png",
        TILES_DIR / "Indoor_town_default_1.png"
    ]
    for t in tiles:
        test_load_image(t)
        
    # Check Entities
    print("\n--- Checking Entities ---")
    entities = [
        ENTITIES_DIR / "character1.png",
        ENTITIES_DIR / "hero.png",
        ENTITIES_DIR / "goblin.png"
    ]
    for e in entities:
        test_load_image(e)
        
    print("\nDone.")

if __name__ == "__main__":
    main()
