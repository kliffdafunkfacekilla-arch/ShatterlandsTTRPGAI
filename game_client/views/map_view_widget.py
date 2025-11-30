"""
Reusable Map View Widget
This widget is responsible for rendering the tilemap and all
entities (player, NPCs, items) on top of it.
It does not contain any game logic, only rendering logic.
"""
import logging
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.properties import ListProperty, ObjectProperty, DictProperty

# --- Client Asset Loader ---
# ... (imports unchanged) ...
try:
    from game_client import asset_loader
except ImportError as e:
    logging.error(f"MAP_VIEW: Failed to import asset_loader: {e}")
    asset_loader = None

# Constants
TILE_SIZE = 64 # Render tiles at 64x64 pixels

from kivy.uix.scatterlayout import ScatterLayout

class MapViewWidget(ScatterLayout):
    """
    A Widget that renders the 2D tile-based map and entities.
    Uses ScatterLayout to allow zooming and panning.
    """
    # Keep track of rendered sprites
    tile_sprites = ListProperty([])
    entity_sprites = ListProperty([])

    # --- MODIFIED: Store all player sprites by ID ---
    player_sprites = DictProperty({})
    # player_sprite is now just a reference to the *active* one
    player_sprite = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        """
        Initializes the map widget.
        """
        super().__init__(**kwargs)
        self.do_rotation = False # Disable rotation
        self.do_scale = True
        self.do_translation = True
        self.auto_bring_to_front = False # Don't reorder widgets on click
        
        # We are a ScatterLayout, so our size is determined by content, 
        # but we need to set size_hint to None to allow scrolling/panning within parent if needed.
        # However, ScatterLayout usually fills its parent or is sized explicitly.
        # Let's keep size_hint None for now as we set size in build_scene.
        self.size_hint = (None, None)

    def on_touch_down(self, touch):
        # Handle zooming with mouse scroll
        if touch.is_mouse_scrolling:
            if touch.button == 'scrolldown':
                if self.scale < 2.0:
                    self.scale *= 1.1
            elif touch.button == 'scrollup':
                if self.scale > 0.5:
                    self.scale *= 0.9
            return True
        return super().on_touch_down(touch)

    def build_scene(self, location_context, party_contexts_list):
        """
        Clears and rebuilds the entire map visual.

        This function iterates through the map data, NPCs, and player list provided
        in the context, looks up their assets via `asset_loader`, and adds Image widgets
        to the scene.

        Args:
            location_context (Dict): The full location context (map data, NPCs, etc.).
            party_contexts_list (List[Dict]): A list of character context dictionaries for the party.
        """
        if not asset_loader:
            logging.error("Cannot build scene, asset_loader is not available.")
            return

        self.clear_widgets()
        self.tile_sprites = []
        self.entity_sprites = []
        self.player_sprites = {} # Clear the sprite dict
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
        # Check for new MapState format
        map_state = location_context.get('map_state')
        
        if map_state:
            # Render from MapState (Dict or Object)
            # If it's a Pydantic model, convert to dict, otherwise assume dict
            if hasattr(map_state, 'dict'):
                tiles = map_state.tiles
            elif isinstance(map_state, dict) and 'tiles' in map_state:
                tiles = map_state['tiles']
            else:
                tiles = {}

            for tile_key, tile_data in tiles.items():
                # tile_key is "x,y"
                try:
                    if hasattr(tile_data, 'coordinates'):
                        tx, ty = tile_data.coordinates
                        terrain = tile_data.terrain_type
                    else:
                        tx, ty = tile_data.get('coordinates', (0,0))
                        terrain = tile_data.get('terrain_type', 'floor')
                        
                    # Map terrain to ID (simplified)
                    tile_id = "1" if terrain == "wall" else "0"
                    
                    render_info = asset_loader.get_sprite_render_info(tile_id)
                    if not render_info: continue
                    
                    sheet_path, rtx, rty, _, _ = render_info
                    render_y = (map_height - 1 - ty) * TILE_SIZE
                    
                    texture = asset_loader.get_texture(sheet_path)
                    if texture:
                        region = texture.get_region(rtx, rty, TILE_SIZE, TILE_SIZE)
                        tile_image = Image(
                            texture=region,
                            size_hint=(None, None),
                            size=(TILE_SIZE, TILE_SIZE),
                            pos=(tx * TILE_SIZE, render_y)
                        )
                        self.add_widget(tile_image)
                        self.tile_sprites.append(tile_image)
                        
                except Exception as e:
                    logging.error(f"Error rendering tile {tile_key}: {e}")

        else:
            # Legacy Render (List of Lists)
            for y, row in enumerate(tile_map):
                for x, tile_id in enumerate(row):
                    render_info = asset_loader.get_sprite_render_info(str(tile_id))
    
                    if not render_info:
                        logging.warning(f"No render info for tile ID {tile_id} at ({x},{y})")
                        continue
    
                    sheet_path, tx, ty, tx2, ty2 = render_info
                    render_y = (map_height - 1 - y) * TILE_SIZE
    
                    texture = asset_loader.get_texture(sheet_path)
                    if not texture:
                        continue
    
                    # Create a texture region for the sprite
                    region = texture.get_region(tx, ty, TILE_SIZE, TILE_SIZE)
    
                    tile_image = Image(
                        texture=region,
                        size_hint=(None, None),
                        size=(TILE_SIZE, TILE_SIZE),
                        pos=(x * TILE_SIZE, render_y)
                    )
                    self.add_widget(tile_image)
                    self.tile_sprites.append(tile_image)


        # --- 2. Render NPCs ---
        for npc in location_context.get('npcs', []):
            self.add_entity_sprite(npc, map_height)

        # --- 3. Render Players ---
        if party_contexts_list:
            for i, player_context in enumerate(party_contexts_list):
                is_first_player = (i == 0) # The first player is active by default
                self.add_entity_sprite(player_context, map_height, is_player=True, is_active=is_first_player)

        logging.info("MapViewWidget: Scene built.")

    def add_entity_sprite(self, entity_context, map_height, is_player=False, is_active=False):
        """
        Instantiates and adds a single sprite (NPC or Player) to the map.

        Args:
            entity_context (Dict): The data for the entity (location, ID, etc.).
            map_height (int): The height of the map in tiles (needed for coordinate conversion).
            is_player (bool): Whether this entity is a player character.
            is_active (bool): Whether this player is the currently controlled character.
        """
        if is_player:
            sprite_id = entity_context.portrait_id or 'character_1'
            coords = [entity_context.position_x, entity_context.position_y]
            entity_id_log = entity_context.name
            player_uuid = entity_context.id # Get the unique ID
        else:
            sprite_id = entity_context.get('template_id', 'goblin_scout')
            coords = entity_context.get('coordinates', [1, 1])
            entity_id_log = sprite_id
            player_uuid = None

        render_info = asset_loader.get_sprite_render_info(sprite_id)
        if not render_info:
            render_info = asset_loader.get_sprite_render_info('character_2') # Fallback
            if not render_info:
                logging.warning(f"No render info for entity sprite ID {sprite_id}")
                return

        sheet_path, tx, ty, tx2, ty2 = render_info
        render_y = (map_height - 1 - coords[1]) * TILE_SIZE

        texture = asset_loader.get_texture(sheet_path)
        if not texture:
            logging.warning(f"Skipping entity {entity_id_log}: texture not found at {sheet_path}")
            return

        # Create a texture region for the sprite
        region = texture.get_region(tx, ty, TILE_SIZE, TILE_SIZE)

        entity_image = Image(
            texture=region,
            size_hint=(None, None),
            size=(TILE_SIZE, TILE_SIZE),
            pos=(coords[0] * TILE_SIZE, render_y)
        )

        self.add_widget(entity_image)

        if is_player:
            self.entity_sprites.append(entity_image) # Add to general list
            self.player_sprites[player_uuid] = entity_image # Add to player-specific dict
            if is_active:
                self.player_sprite = entity_image # Set the active sprite
            logging.info(f"Player '{entity_id_log}' rendered at ({coords[0]}, {coords[1]})")
        else:
            self.entity_sprites.append(entity_image)


    def move_active_player_sprite(self, player_id: str, tile_x: int, tile_y: int, map_height: int):
        """
        Updates the position of a specific player's sprite on the map.

        Args:
            player_id (str): The ID of the player to move.
            tile_x (int): The new X grid coordinate.
            tile_y (int): The new Y grid coordinate.
            map_height (int): The height of the map in tiles.
        """

        # Find the correct sprite from our dictionary
        sprite_to_move = self.player_sprites.get(player_id)

        if sprite_to_move:
            render_y = (map_height - 1 - tile_y) * TILE_SIZE
            sprite_to_move.pos = (tile_x * TILE_SIZE, render_y)

            # Also update the main 'player_sprite' reference
            self.player_sprite = sprite_to_move
        else:
            logging.warning(f"Cannot move player sprite {player_id}, it does not exist in dict.")
