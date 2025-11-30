"""
AssetLoader for the Shatterlands Python Client.

Loads all tile and entity definitions from JSON files and provides
helper functions to get rendering information (spritesheet paths,
clipping coordinates) for Kivy and Arcade.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Add these to the top of game_client/asset_loader.py
from kivy.core.image import Image as CoreImage
from kivy.properties import ObjectProperty

# --- Constants ---
TILE_SIZE = 64  # Pixel size for a single tile/sprite

# --- Path Setup ---
# Assumes this file is in 'game_client/asset_loader.py'
# and the 'assets' folder is at 'game_client/assets/'
CLIENT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = CLIENT_ROOT / "assets"
GFX_DIR = ASSETS_DIR / "graphics"
TILES_DIR = GFX_DIR / "tiles"
ENTITIES_DIR = GFX_DIR / "entities"

# --- In-Memory Asset Caches ---
# Stores the raw data from tile_definitions.json
# e.g., "0": {"name": "Grass", "passable": True, ...}
TILE_DEFINITIONS: Dict[str, Dict[str, Any]] = {}

# Stores the raw data from entity_definitions.json
# e.g., "player_default": {"name": "Player", "sheet": "character1.png", ...}
ENTITY_DEFINITIONS: Dict[str, Dict[str, Any]] = {}

# Stores the final, calculated render info
# e.g., "0": ("game_client/assets/graphics/tiles/outdoor_tiles_1.png", 384, 384)
# e.g., "player_default": ("game_client/assets/graphics/entities/character1.png", 0, 0)
SPRITE_RENDER_INFO: Dict[str, Tuple[Path, int, int]] = {}

# --- In-Memory Texture Cache for Kivy ---
KIVY_TEXTURE_CACHE: Dict[str, ObjectProperty] = {}

def get_texture(sheet_path: str):
    """
    Caches and returns a Kivy texture object for the given file path.

    Loads the image from disk if not already cached, setting appropriate
    filtering for pixel art (nearest neighbor).

    Args:
        sheet_path (str): The absolute path to the spritesheet file.

    Returns:
        Texture: The Kivy Texture object, or None if loading failed.
    """
    if sheet_path not in KIVY_TEXTURE_CACHE:
        logging.info(f"AssetLoader: Caching new texture for {sheet_path}")
        try:
            texture = CoreImage(str(sheet_path)).texture
            if not texture:
                logging.error(f"AssetLoader: Failed to load texture at {sheet_path} (Texture is None)")
                return None
            
            # Enable texture clipping
            texture.mag_filter = 'nearest'
            texture.min_filter = 'nearest'
            texture.wrap = 'clamp_to_edge'

            KIVY_TEXTURE_CACHE[sheet_path] = texture
            
        except Exception as e:
            logging.error(f"AssetLoader: Exception loading texture at {sheet_path}: {e}")
            return None

    return KIVY_TEXTURE_CACHE[sheet_path]

def _load_json_data(filepath: Path) -> Dict:
    """
    Helper function to safely load a JSON file.

    Args:
        filepath (Path): The path to the JSON file.

    Returns:
        Dict: The parsed JSON data, or an empty dict on failure.
    """
    if not filepath.exists():
        logging.error(f"AssetLoader: JSON file not found at {filepath}")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.exception(f"AssetLoader: Failed to load or parse {filepath}: {e}")
        return {}

def _build_sprite_lookup_map():
    """
    Compiles raw tile and entity definitions into a fast lookup map for rendering.

    Iterates through all loaded definitions, resolves spritesheet paths,
    and calculates the top-left pixel coordinates (sx, sy) for each sprite frame.
    Populates the global `SPRITE_RENDER_INFO` dictionary.
    """
    global SPRITE_RENDER_INFO

    # --- 1. Manually map Tile IDs to their spritesheet coordinates ---
    # This is the Python version of the manual map in assetLoader.ts
    # We use 1-based columns/rows here for easier mapping from an atlas.
    tile_sprite_map = {
        "0": {"sheet": TILES_DIR / "outdoor_tiles_1.png", "col": 3, "row": 3},  # Grass
        "1": {"sheet": TILES_DIR / "outdoor_tiles_1.png", "col": 5, "row": 4},  # Tree
        "2": {"sheet": TILES_DIR / "outdoor_tiles_1.png", "col": 2, "row": 5},  # Water
        "3": {"sheet": TILES_DIR / "Indoor_town_default_1.png", "col": 3, "row": 4},  # Stone Floor
        "4": {"sheet": TILES_DIR / "Indoor_town_default_1.png", "col": 2, "row": 1},  # Stone Wall
        "5": {"sheet": TILES_DIR / "Indoor_town_default_1.png", "col": 3, "row": 1},  # Door Closed
        "5_open": {"sheet": TILES_DIR / "Indoor_town_default_1.png", "col": 1, "row": 1},  # Door Open
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
        logging.info(f"AssetLoader: Mapped {entity_id} -> {sheet_path} ({sx}, {sy})")

    logging.info(f"AssetLoader: Built sprite map with {len(SPRITE_RENDER_INFO)} entries.")

def initialize_assets():
    """
    The main initialization routine for the Asset Loader.

    Loads tile and entity definition JSONs from the assets directory and builds
    the sprite lookup map. This function must be called before any rendering occurs.
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
    logging.info("--- Asset Initialization Complete ---")

# --- Public Getter Functions ---

def get_sprite_render_info(entity_id: str, state: Optional[str] = None) -> Optional[Tuple[str, int, int, int, int]]:
    """
    Retrieves the rendering information for a specific entity or tile.

    Calculates the texture coordinates required by Kivy to render the correct
    sub-region (sprite) from the spritesheet.

    Args:
        entity_id (str): The unique identifier of the tile or entity.
        state (Optional[str]): An optional state suffix (e.g., "open" for a door).

    Returns:
        Optional[Tuple[str, int, int, int, int]]: A tuple containing:
            (spritesheet_path, x, y, x2, y2)
            where coords are in pixels relative to the texture's origin.
            Returns None if the sprite cannot be resolved.
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
        # Try to find a fallback defined in entity definitions
        fallback_def = ENTITY_DEFINITIONS.get("fallback")
        if fallback_def:
            info = SPRITE_RENDER_INFO.get("fallback")

    if not info:
        logging.error(f"AssetLoader: No render info for '{key}' and no 'fallback' defined.")
        return None

    sheet_path, sx, sy = info

    # --- Calculate texture coordinates for Kivy ---
    texture = get_texture(str(sheet_path))
    if not texture:
        return None  # Failed to load texture

    tex_h = texture.height

    # Kivy's `tex_coords` are (x, y, x2, y2) in pixels, from bottom-left.
    kivy_y_bottom_left = tex_h - sy - TILE_SIZE

    kivy_tex_coords = (sx, kivy_y_bottom_left, sx + TILE_SIZE, kivy_y_bottom_left + TILE_SIZE)

    # Return path as a string, and the 4 tex_coords values.
    return (str(sheet_path), *kivy_tex_coords)

def get_tile_definition(tile_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves the raw definition data for a specific tile ID.

    Args:
        tile_id (int): The ID of the tile.

    Returns:
        Optional[Dict[str, Any]]: The tile definition dictionary.
    """
    return TILE_DEFINITIONS.get(str(tile_id))

def get_entity_definition(entity_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the raw definition data for a specific entity ID.

    Args:
        entity_id (str): The ID of the entity.

    Returns:
        Optional[Dict[str, Any]]: The entity definition dictionary.
    """
    return ENTITY_DEFINITIONS.get(entity_id)

