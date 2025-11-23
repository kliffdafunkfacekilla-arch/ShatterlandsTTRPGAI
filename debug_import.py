import sys
import os
from pathlib import Path

# --- 1. SET SYS.PATH ---
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

MONOLITH_PATH = APP_ROOT / "AI-TTRPG"
if str(MONOLITH_PATH) not in sys.path:
    sys.path.insert(0, str(MONOLITH_PATH))

print(f"Sys path: {sys.path}")

try:
    from monolith.modules import story as story_api
    from monolith.modules.story_pkg import schemas as story_schemas
    print("Import successful")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
