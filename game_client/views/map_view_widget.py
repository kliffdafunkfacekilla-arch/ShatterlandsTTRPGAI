"""
Reusable Map View Widget
This widget is responsible for rendering the tilemap and all
entities (player, NPCs, items) on top of it.
It does not contain any game logic, only rendering logic.
"""import loggingfrom kivy.uix.floatlayout import FloatLayoutfrom kivy.uix.image import Imagefrom kivy.properties import ListProperty, ObjectProperty# --- Client Asset Loader ---try:
from game_client import asset_loaderexcept ImportError as e:
logging.error(f"MAP_VIEW: Failed to import asset_loader: {e}")
asset_loader = None# Constants
TILE_SIZE = 64 # Render tiles at 64x64 pixelsclass MapViewWidget(FloatLayout):

# Keep track of rendered sprites
tile_sprites = ListProperty([])
entity_sprites = ListProperty([])
player_sprite = ObjectProperty(None, allownone=True)

def __init__(self, **kwargs):
super().__init__(**kwargs)
# We are a simple FloatLayout, so our size must
# be set from the outside.
self.size_hint = (None, None)

def build_scene(self, location_context, player_context):
"""
Clears and rebuilds the entire map visual.
This is called by the parent screen (e.g., Interface or Combat).
"""
if not asset_loader:
logging.error("Cannot build scene, asset_loader is not available.")
return

self.clear_widgets()
self.tile_sprites = []
self.entity_sprites = []
self.player_sprite = None

tile_map = location_context.get('generated_map_data')
if not tile_map:
logging.error("Location has no 'generated_map_data' to render.")
return

map_height = len(tile_map)
map_width = len(tile_map[0]) if map_height > 0 else 0

# Set our own size based on the map
self.size = (map_width * TILE_SIZE, map_height * TILE_SIZE)

# --- 1. Render Tiles ---
for y, row in enumerate(tile_map):
for x, tile_id in enumerate(row):
render_info = asset_loader.get_sprite_render_info(str(tile_id))

if not render_info:
logging.warning(f"No render info for tile ID {tile_id} at ({x},{y})")
continue

sheet_path, u, v, u2, v2 = render_info
render_y = (map_height - 1 - y) * TILE_SIZE

tile_image = Image(
source=sheet_path,
texture=asset_loader.get_texture(sheet_path),
tex_coords=(u, v, u2, v2),
size_hint=(None, None),
size=(TILE_SIZE, TILE_SIZE),
pos=(x * TILE_SIZE, render_y)
)
self.add_widget(tile_image)
self.tile_sprites.append(tile_image)

# --- 2. Render NPCs ---
for npc in location_context.get('npcs', []):
self.add_entity_sprite(npc, map_height)

# --- 3. Render Player ---
self.add_entity_sprite(player_context, map_height, is_player=True)
logging.info("MapViewWidget: Scene built.")

def add_entity_sprite(self, entity_context, map_height, is_player=False):
"""Adds a single NPC or player sprite to the map."""
if is_player:
sprite_id = entity_context.portrait_id or 'character_1'
coords = [entity_context.position_x, entity_context.position_y]
else:
sprite_id = entity_context.get('template_id', 'goblin_scout')
coords = entity_context.get('coordinates', [1, 1])

render_info = asset_loader.get_sprite_render_info(sprite_id)
if not render_info:
render_info = asset_loader.get_sprite_render_info('character_2') # Fallback
if not render_info:
logging.warning(f"No render info for entity sprite ID {sprite_id}")
return

sheet_path, u, v, u2, v2 = render_info
render_y = (map_height - 1 - coords[1]) * TILE_SIZE

entity_image = Image(
source=sheet_path,
texture=asset_loader.get_texture(sheet_path),
tex_coords=(u, v, u2, v2),
size_hint=(None, None),
size=(TILE_SIZE, TILE_SIZE),
pos=(coords[0] * TILE_SIZE, render_y)
)

self.add_widget(entity_image)
self.entity_sprites.append(entity_image)

if is_player:
self.player_sprite = entity_image
logging.info(f"Player '{entity_context.name}' rendered at ({coords[0]}, {coords[1]})")

def move_player_sprite(self, tile_x: int, tile_y: int, map_height: int):
"""Updates the position of the player's sprite."""
if self.player_sprite:
render_y = (map_height - 1 - tile_y) * TILE_SIZE
self.player_sprite.pos = (tile_x * TILE_SIZE, render_y)
else:
logging.warning("Cannot move player sprite, it does not exist.")
