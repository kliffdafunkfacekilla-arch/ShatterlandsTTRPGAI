"""
AssetLoader for the Shatterlands Python Client.

Loads all tile and entity definitions from JSON files and provides
helper functions to get rendering information (spritesheet paths,
clipping coordinates) for Kivy and Arcade.
"""import jsonimport loggingfrom pathlib import Pathfrom typing import Dict, Any, Optional, Tuple# --- Constants ---
TILE_SIZE = 128 # Pixel size for a single tile/sprite# --- Path Setup ---# Assumes this file is in 'game_client/asset_loader.py'# and the 'assets' folder is at 'game_client/assets/'
CLIENT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = CLIENT_ROOT / "assets"
GFX_DIR = ASSETS_DIR / "graphics"
TILES_DIR = GFX_DIR / "tiles"
ENTITIES_DIR = GFX_DIR / "entities"# --- In-Memory Asset Caches ---# Stores the raw data from tile_definitions.json# e.g., "0": {"name": "Grass", "passable": True, ...}
TILE_DEFINITIONS: Dict[str, Dict[str, Any]] = {}# Stores the raw data from entity_definitions.json# e.g., "player_default": {"name": "Player", "sheet": "character1.png", ...}
ENTITY_DEFINITIONS: Dict[str, Dict[str, Any]] = {}# Stores the final, calculated render info# e.g., "0": ("game_client/assets/graphics/tiles/outdoor_tiles_1.png", 384, 384)# e.g., "player_default": ("game_client/assets/graphics/entities/character1.png", 0, 0)
SPRITE_RENDER_INFO: Dict[str, Tuple[Path, int, int]] = {}def _load_json_data(filepath: Path) -> Dict:
"""Helper to load a JSON file."""
if not filepath.exists():
logging.error(f"AssetLoader: JSON file not found at {filepath}")
return {}
try:
with open(filepath, 'r', encoding='utf-8') as f:
return json.load(f)
except Exception as e:
logging.exception(f"AssetLoader: Failed to load or parse {filepath}: {e}")
return {}def _build_sprite_lookup_map():
"""
Processes raw definitions into a unified lookup map for rendering.
This function calculates and caches the (path, sx, sy) for every sprite.
"""
global SPRITE_RENDER_INFO

# --- 1. Manually map Tile IDs to their spritesheet coordinates ---
# This is the Python version of the manual map in assetLoader.ts
# We use 1-based columns/rows here for easier mapping from an atlas.
tile_sprite_map = {
"0": {"sheet": TILES_DIR / "outdoor_tiles_1.png", "col": 3, "row": 3}, # Grass
"1": {"sheet": TILES_DIR / "outdoor_tiles_1.png", "col": 5, "row": 4}, # Tree
"2": {"sheet": TILES_DIR / "outdoor_tiles_1.png", "col": 2, "row": 5}, # Water
"3": {"sheet": TILES_DIR / "Indoor_town_default_1.png", "col": 3, "row": 4}, # Stone Floor
"4": {"sheet": TILES_DIR / "Indoor_town_default_1.png", "col": 2, "row": 1}, # Stone Wall
"5": {"sheet": TILES_DIR / "Indoor_town_default_1.png", "col": 3, "row": 1}, # Door Closed
"5_open": {"sheet": TILES_DIR / "Indoor_town_default_1.png", "col": 1, "row": 1}, # Door Open
}

# --- 2. Process Tile Definitions ---
for tile_id, definition in TILE_DEFINITIONS.items():
map_info = tile_sprite_map.get(tile_id)
if map_info:
# Convert 1-based (col, row) to 0-based (sx, sy) pixel coordinates
sx = (map_info['col'] - 1) * TILE_SIZE
sy = (map_info['row'] - 1) * TILE_SIZE
SPRITE_RENDER_INFO[tile_id] = (map_info['sheet'], sx, sy)
else:
logging.warning(f"AssetLoader: No manual sprite map for Tile ID: {tile_id}")

# Process states (e.g., "open" for doors)
for state_name in definition.get("states", {}):
state_key = f"{tile_id}_{state_name}"
map_info = tile_sprite_map.get(state_key)
if map_info:
sx = (map_info['col'] - 1) * TILE_SIZE
sy = (map_info['row'] - 1) * TILE_SIZE
SPRITE_RENDER_INFO[state_key] = (map_info['sheet'], sx, sy)
else:
logging.warning(f"AssetLoader: No manual sprite map for Tile State: {state_key}")

# --- 3. Process Entity Definitions ---
for entity_id, definition in ENTITY_DEFINITIONS.items():
sheet_name = definition.get("sheet")
col = definition.get("col")
row = definition.get("row")

if not sheet_name or col is None or row is None:
logging.warning(f"AssetLoader: Incomplete definition for Entity ID: {entity_id}")
continue

sheet_path = ENTITIES_DIR / sheet_name
# col/row in entity_definitions.json are 0-based, convert to pixel coords
sx = col * TILE_SIZE
sy = row * TILE_SIZE
SPRITE_RENDER_INFO[entity_id] = (sheet_path, sx, sy)

logging.info(f"AssetLoader: Built sprite map with {len(SPRITE_RENDER_INFO)} entries.")def initialize_assets():
"""
Loads all asset definitions from JSON files.
This must be called once at application startup.
"""
global TILE_DEFINITIONS, ENTITY_DEFINITIONS

logging.info("--- Initializing Game Assets ---")

tile_def_path = ASSETS_DIR / "tile_definitions.json"
entity_def_path = ASSETS_DIR / "entity_definitions.json"

TILE_DEFINITIONS = _load_json_data(tile_def_path)
ENTITY_DEFINITIONS = _load_json_data(entity_def_path)

_build_sprite_lookup_map()

logging.info(f"Loaded {len(TILE_DEFINITIONS)} tile definitions.")
logging.info(f"Loaded {len(ENTITY_DEFINITIONS)} entity definitions.")
logging.info("--- Asset Initialization Complete ---")# --- Public Getter Functions ---def get_sprite_render_info(entity_id: str, state: Optional[str] = None) -> Optional[Tuple[str, int, int, int, int]]:
"""
Gets the render info for a tile or entity ID.

Returns:
A tuple (spritesheet_path, sx, sy, TILE_SIZE, TILE_SIZE) or None
"""
key = str(entity_id)
if state:
key = f"{key}_{state}"

# Try state-specific key first
info = SPRITE_RENDER_INFO.get(key)

# If not found, try base key
if not info:
info = SPRITE_RENDER_INFO.get(str(entity_id))

# If still not found, try fallback
if not info:
info = SPRITE_RENDER_INFO.get("fallback")
if not info:
logging.error(f"AssetLoader: No render info for '{key}' and no 'fallback' defined.")
return None

sheet_path, sx, sy = info
# Return path as a string, and clipping box
return (str(sheet_path), sx, sy, TILE_SIZE, TILE_SIZE)def get_tile_definition(tile_id: int) -> Optional[Dict[str, Any]]:
"""
Gets the raw data for a tile (name, passable, etc.)
"""
return TILE_DEFINITIONS.get(str(tile_id))def get_entity_definition(entity_id: str) -> Optional[Dict[str, Any]]:
"""
Gets the raw data for an entity (name, sheet, etc.)
"""
return ENTITY_DEFINITIONS.get(entity_id)
