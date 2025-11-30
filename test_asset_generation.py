import sys
from pathlib import Path

# Setup paths
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
    
# Add AI-TTRPG to path as well for monolith imports
MONOLITH_PATH = ROOT_DIR / "AI-TTRPG"
if str(MONOLITH_PATH) not in sys.path:
    sys.path.insert(0, str(MONOLITH_PATH))

import os
import logging
from game_client import asset_loader

# --- LOAD ENV VARS ---
def load_env_file():
    """Manually load .env file to avoid external dependencies."""
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        print(f"Loading environment from {env_path}")
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        # Don't overwrite existing system env vars
                        if key.strip() not in os.environ:
                            os.environ[key.strip()] = value.strip()
        except Exception as e:
            print(f"Failed to load .env file: {e}")

load_env_file()

# Setup logging
logging.basicConfig(level=logging.INFO)

# Mock Kivy CoreImage to avoid window creation
from unittest.mock import MagicMock
import sys
sys.modules['kivy.core.image'] = MagicMock()
sys.modules['kivy.core.image'].Image = MagicMock()
sys.modules['kivy.core.image'].Image.return_value.texture = MagicMock()

# Define a fake asset path
fake_asset_path = Path(asset_loader.ASSETS_DIR) / "graphics" / "entities" / "missing_hero.png"

# Ensure it doesn't exist
if fake_asset_path.exists():
    os.remove(fake_asset_path)
svg_path = fake_asset_path.with_suffix('.svg')
if svg_path.exists():
    os.remove(svg_path)

print(f"Testing asset generation for: {fake_asset_path}")

# Trigger loading
# Import ai_client to check status
# Import ai_client to check status
from monolith.modules.ai_dm_pkg.llm_service import ai_client

with open("debug_api_key.txt", "w") as f:
    f.write(f"DEBUG: GEMINI_API_KEY present: {'GEMINI_API_KEY' in os.environ}\n")
    if 'GEMINI_API_KEY' in os.environ:
        key = os.environ['GEMINI_API_KEY']
        f.write(f"DEBUG: Key length: {len(key)}\n")
        if len(key) > 4:
            f.write(f"DEBUG: Key starts with: {key[:4]}...\n")
        else:
            f.write(f"DEBUG: Key is too short: {key}\n")
    else:
        f.write("DEBUG: GEMINI_API_KEY NOT FOUND in os.environ\n")

    f.write(f"DEBUG: AI Model initialized: {ai_client.model}\n")
    
    # Try direct generation to capture error
    try:
        f.write("DEBUG: Attempting direct generation...\n")
        response = ai_client.model.generate_content("Test")
        f.write(f"DEBUG: Direct generation success: {response.text[:50]}...\n")
    except Exception as e:
        f.write(f"DEBUG: Direct generation failed: {e}\n")
        import traceback
        f.write(traceback.format_exc())

texture = asset_loader.get_texture(str(fake_asset_path))

# Check if SVG was created
if svg_path.exists():
    print(f"SUCCESS: SVG generated at {svg_path}")
    with open(svg_path, 'r') as f:
        print("Content preview:", f.read()[:100])
else:
    print("FAILURE: SVG was not generated.")
