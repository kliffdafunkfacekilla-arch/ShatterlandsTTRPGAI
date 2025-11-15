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

class MapViewWidget(FloatLayout):
    # Keep track of rendered sprites
    tile_sprites = ListProperty([])
    entity_sprites = ListProperty([])

    # --- MODIFIED: Store all player sprites by ID ---
    player_sprites = DictProperty({})
    # player_sprite is now just a reference to the *active* one
    player_sprite = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # We are a simple FloatLayout, so our size must
        # be set from the outside.
        self.size_hint = (None, None)

    def build_scene(self, location_context, party_contexts_list):
        """
        Clears and rebuilds the entire map visual.
        - party_contexts_list: A LIST of player character contexts.
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

        # --- 3. Render Players ---
        if party_contexts_list:
            for i, player_context in enumerate(party_contexts_list):
                is_first_player = (i == 0) # The first player is active by default
                self.add_entity_sprite(player_context, map_height, is_player=True, is_active=is_first_player)

        logging.info("MapViewWidget: Scene built.")

    def add_entity_sprite(self, entity_context, map_height, is_player=False, is_active=False):
        """Adds a single NPC or player sprite to the map."""
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

        if is_player:
            self.entity_sprites.append(entity_image) # Add to general list
            self.player_sprites[player_uuid] = entity_image # Add to player-specific dict
            if is_active:
                self.player_sprite = entity_image # Set the active sprite
            logging.info(f"Player '{entity_id_log}' rendered at ({coords[0]}, {coords[1]})")
        else:
            self.entity_sprites.append(entity_image)


    def move_active_player_sprite(self, player_id: str, tile_x: int, tile_y: int, map_height: int):
        """Updates the position of the specified player's sprite."""

        # Find the correct sprite from our dictionary
        sprite_to_move = self.player_sprites.get(player_id)

        if sprite_to_move:
            render_y = (map_height - 1 - tile_y) * TILE_SIZE
            sprite_to_move.pos = (tile_x * TILE_SIZE, render_y)

            # Also update the main 'player_sprite' reference
            self.player_sprite = sprite_to_move
        else:
            logging.warning(f"Cannot move player sprite {player_id}, it does not exist in dict.")
