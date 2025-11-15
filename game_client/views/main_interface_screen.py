"""
The Main Game Interface screen.
Handles rendering the game world, entities, and all UI panels.
"""import loggingfrom kivy.app import Appfrom kivy.lang import Builderfrom kivy.uix.screenmanager import Screenfrom kivy.uix.floatlayout import FloatLayoutfrom kivy.uix.boxlayout import BoxLayoutfrom kivy.uix.anchorlayout import AnchorLayoutfrom kivy.uix.scrollview import ScrollViewfrom kivy.uix.label import Labelfrom kivy.uix.textinput import TextInputfrom kivy.uix.button import Buttonfrom kivy.uix.image import Imagefrom kivy.properties import ObjectProperty, ListProperty, StringPropertyfrom kivy.core.window import Window# --- Monolith Imports ---try:
from monolith.modules.character_pkg import crud as char_crud
from monolith.modules.character_pkg import services as char_services
from monolith.modules.character_pkg.database import SessionLocal as CharSession
from monolith.modules.world_pkg import crud as world_crud
from monolith.modules.world_pkg.database import SessionLocal as WorldSession
from monolith.modules import character as character_api
from monolith.modules import story as story_api # <-- ADD THIS
from monolith.modules.story_pkg import schemas as story_schemas # <-- ADD THIS
except ImportError as e:
logging.error(f"MAIN_INTERFACE: Failed to import monolith modules: {e}")
char_crud, char_services, CharSession = None, None, None
world_crud, WorldSession, character_api, story_api, story_schemas = None, None, None, None, None
from game_client import asset_loaderexcept ImportError as e:
logging.error(f"MAIN_INTERFACE: Failed to import asset_loader: {e}")
asset_loader = None# Constants
TILE_SIZE = 64 # Render tiles at 64x64 pixels# --- Kivy Language (KV) String for the UI Layout ---# We define the entire UI layout here.# The 'id' tags allow our Python class to access these widgets.
MAIN_INTERFACE_KV = """
<MainInterfaceScreen>:
# Main layout: Anchors widgets to corners/sides
AnchorLayout:

# --- CENTER: Map View ---
# This layout will be centered and will contain the moving map
AnchorLayout:
anchor_x: 'center'
anchor_y: 'center'

# This is the container we add tiles and sprites to.
# Its size is set in build_scene() based on the map dimensions.
FloatLayout:
id: map_view_container
size_hint: None, None

# --- TOP-LEFT: Log Window ---
AnchorLayout:
anchor_x: 'left'
anchor_y: 'top'
size_hint: 0.3, 0.25
padding: '10dp'

BoxLayout:
orientation: 'vertical'
canvas.before:
Color:
rgba: 0.1, 0.1, 0.1, 0.8
Rectangle:
pos: self.pos
size: self.size

Label:
text: 'Log'
size_hint_y: None
height: '30dp'
font_size: '18sp'

ScrollView:
Label:
id: log_label
text: 'Welcome to Shatterlands.'
font_size: '14sp'
size_hint_y: None
height: self.texture_size[1]
text_size: self.width, None
padding: '5dp'

# --- BOTTOM-LEFT: Party Panel ---
AnchorLayout:
anchor_x: 'left'
anchor_y: 'bottom'
size_hint: 0.25, 0.3
padding: '10dp'

BoxLayout:
id: party_panel
orientation: 'vertical'
canvas.before:
Color:
rgba: 0.1, 0.1, 0.1, 0.8
Rectangle:
pos: self.pos
size: self.size

# Active Character Display
Label:
text: 'Active Character'
size_hint_y: None
height: '30dp'
font_size: '18sp'

Label:
id: active_char_name
text: 'Character Name'
font_size: '16sp'
size_hint_y: 0.2

Label:
id: active_char_status
text: 'HP: 100/100'
size_hint_y: 0.15

# Party List
Label:
text: 'Party'
size_hint_y: None
height: '30dp'
font_size: '16sp'

ScrollView:
BoxLayout:
id: party_list_container
orientation: 'vertical'
size_hint_y: None
height: self.minimum_height

# --- RIGHT: Narration & DM Input ---
AnchorLayout:
anchor_x: 'right'
anchor_y: 'center'
size_hint: 0.3, 0.95
padding: '10dp'

BoxLayout:
orientation: 'vertical'
spacing: '10dp'
canvas.before:
Color:
rgba: 0.1, 0.1, 0.1, 0.8
Rectangle:
pos: self.pos
size: self.size

Label:
text: 'Narration'
size_hint_y: None
height: '30dp'
font_size: '18sp'

ScrollView:
Label:
id: narration_label
text: 'The story begins...'
font_size: '14sp'
size_hint_y: None
height: self.texture_size[1]
text_size: self.width, None
padding: '10dp'

TextInput:
id: dm_input
hint_text: 'What do you do?'
size_hint_y: None
height: '44dp'
font_size: '16sp'
multiline: False

# --- TOP: Menu Bar ---
AnchorLayout:
anchor_x: 'center'
anchor_y: 'top'
size_hint_y: None
height: '48dp'

BoxLayout:
orientation: 'horizontal'
size_hint_x: 1
canvas.before:
Color:
rgba: 0.2, 0.2, 0.2, 0.9
Rectangle:
pos: self.pos
size: self.size

Button:
text: 'Menu'
on_release: app.root.current = 'main_menu'
Button:
text: 'Character'
# on_release: root.open_character_sheet() # We will add this later
Button:
text: 'Inventory'
# on_release: root.open_inventory() # We will add this later
Button:
text: 'Quests'
# on_release: root.open_quest_log() # We will add this later
"""# Load the KV string into Kivy's Builder
Builder.load_string(MAIN_INTERFACE_KV)class MainInterfaceScreen(Screen):
"""
Main game screen class. The layout is defined in the KV string above.
We use ObjectProperty to get references to the widgets defined in KV.
"""

# --- UI Widget References ---
render_layout = ObjectProperty(None)
log_label = ObjectProperty(None)
narration_label = ObjectProperty(None)
dm_input = ObjectProperty(None)
party_panel = ObjectProperty(None)
active_char_name = ObjectProperty(None)
active_char_status = ObjectProperty(None)
party_list_container = ObjectProperty(None)

# --- Game State Properties ---
tile_sprites = ListProperty([])
entity_sprites = ListProperty([])
player_sprite = ObjectProperty(None)
context_menu = ObjectProperty(None, allownone=True) # <-- ADD THIS

# Store the context data
active_character_context = ObjectProperty(None, force_dispatch=True)
location_context = ObjectProperty(None, force_dispatch=True)
party_list = ListProperty([]) # Will hold all character contexts

def __init__(self, **kwargs):
super().__init__(**kwargs)

# We find the 'map_view_container' defined in the KV string
# and assign it to our 'render_layout' property.
# This is a bit of a workaround for Kivy's initialization order.
self.render_layout = self.ids.get('map_view_container')

# Bind property changes to UI update functions
self.bind(active_character_context=self.update_active_character_ui)
self.bind(party_list=self.update_party_list_ui)

Window.bind(on_resize=self.center_layout)

def center_layout(self, instance, width, height):
"""Centers the render_layout in the screen."""
if self.render_layout:
self.render_layout.pos = (
(width - self.render_layout.width) / 2,
(height - self.render_layout.height) / 2
)

def on_enter(self, *args):
"""
Called when this screen is shown. Loads all game data.
"""
logging.info("Entering Main Interface Screen. Loading game state...")

# Find the render_layout from the 'ids' dictionary
self.render_layout = self.ids.get('map_view_container')
if not self.render_layout:
logging.error("CRITICAL: 'map_view_container' not found in ids.")
return

app = App.get_running_app()
if not app.game_settings:
logging.error("No game settings found! Returning to menu.")
app.root.current = 'main_menu'
return

char_name = app.game_settings.get('selected_character_name')
if not char_name:
logging.error("No character name in game settings! Returning to menu.")
app.root.current = 'main_menu'
return

if not char_crud or not world_crud or not asset_loader:
logging.error("A required monolith module or asset loader is not available.")
return

# --- Load Character Context (for now, just the one) ---
char_db = None
try:
char_db = CharSession()
db_char = char_crud.get_character_by_name(char_db, char_name)
if not db_char:
raise Exception(f"Character '{char_name}' not found in database.")

# This is now our "Active" character
self.active_character_context = char_services.get_character_context(db_char)

# For now, the party list is just the active character
self.party_list = [self.active_character_context]

logging.info(f"Loaded context for {self.active_character_context.name}")

except Exception as e:
logging.error(f"Failed to load character '{char_name}': {e}")
if char_db: char_db.close()
app.root.current = 'main_menu'
return
finally:
if char_db: char_db.close()

# --- Load Location Context ---
world_db = None
try:
loc_id = self.active_character_context.current_location_id
world_db = WorldSession()
self.location_context = world_crud.get_location_context(world_db, loc_id)
if not self.location_context:
raise Exception(f"Location ID '{loc_id}' not found in database.")

logging.info(f"Loaded context for location: {self.location_context.get('name')}")

except Exception as e:
logging.error(f"Failed to load location context: {e}")
if world_db: world_db.close()
app.root.current = 'main_menu'
return
finally:
if world_db: world_db.close()

# --- Render the Scene ---
self.build_scene()
self.center_layout(Window, Window.width, Window.height)

def build_scene(self):
"""
Clears the old scene and builds a new one based on the
loaded location_context.
"""
self.render_layout.clear_widgets()
self.tile_sprites = []
self.entity_sprites = []

if not self.location_context:
logging.error("Cannot build scene, location_context is missing.")
return

tile_map = self.location_context.get('generated_map_data')
if not tile_map:
logging.error("Location has no 'generated_map_data' to render.")
return

map_height = len(tile_map)
map_width = len(tile_map[0]) if map_height > 0 else 0

self.render_layout.size = (map_width * TILE_SIZE, map_height * TILE_SIZE)

# --- 1. Render Tiles ---
logging.info(f"Rendering {map_width}x{map_height} tilemap...")
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
self.render_layout.add_widget(tile_image)
self.tile_sprites.append(tile_image)

# --- 2. Render NPCs ---
npcs = self.location_context.get('npcs', [])
for npc in npcs:
sprite_id = npc.get('template_id', 'goblin_scout')
coords = npc.get('coordinates', [1, 1])

render_info = asset_loader.get_sprite_render_info(sprite_id)
if not render_info:
render_info = asset_loader.get_sprite_render_info('character_2')
if not render_info:
logging.warning(f"No render info for NPC sprite ID {sprite_id}")
continue

sheet_path, u, v, u2, v2 = render_info
render_y = (map_height - 1 - coords[1]) * TILE_SIZE

npc_image = Image(
source=sheet_path,
texture=asset_loader.get_texture(sheet_path),
tex_coords=(u, v, u2, v2),
size_hint=(None, None),
size=(TILE_SIZE, TILE_SIZE),
pos=(coords[0] * TILE_SIZE, render_y)
)
self.render_layout.add_widget(npc_image)
self.entity_sprites.append(npc_image)

# --- 3. Render Player ---
player = self.active_character_context
sprite_id = player.portrait_id or 'character_1'

render_info = asset_loader.get_sprite_render_info(sprite_id)
if not render_info:
logging.error(f"Failed to get render info for player sprite {sprite_id}")
return

sheet_path, u, v, u2, v2 = render_info
render_y = (map_height - 1 - player.position_y) * TILE_SIZE

# Create the image and store it in our property
self.player_sprite = Image(
source=sheet_path,
texture=asset_loader.get_texture(sheet_path),
tex_coords=(u, v, u2, v2),
size_hint=(None, None),
size=(TILE_SIZE, TILE_SIZE),
pos=(player.position_x * TILE_SIZE, render_y)
)

# Add the stored sprite to the layout
self.render_layout.add_widget(self.player_sprite)
self.entity_sprites.append(self.player_sprite)
logging.info(f"Player '{player.name}' rendered at ({player.position_x}, {player.position_y})")

# --- UI Update Functions ---

def update_active_character_ui(self, *args):
"""Called when self.active_character_context changes."""
if self.active_character_context:
self.ids.active_char_name.text = self.active_character_context.name
self.ids.active_char_status.text = f"HP: {self.active_character_context.current_hp} / {self.active_character_context.max_hp}"
# We can add status effects here later
else:
self.ids.active_char_name.text = "No Character"
self.ids.active_char_status.text = "HP: --/--"

def update_party_list_ui(self, *args):
"""Called when self.party_list changes."""
self.ids.party_list_container.clear_widgets()
for char_context in self.party_list:
# We will make a custom widget for this later
party_member_label = Label(
text=f"{char_context.name} (HP: {char_context.current_hp})",
size_hint_y=None,
height='30dp'
)
self.ids.party_list_container.add_widget(party_member_label)

def update_log(self, message: str):
"""Appends a new message to the log window."""
self.ids.log_label.text += f"\n- {message}"

def update_narration(self, message: str):
"""Replaces the narration text."""
self.ids.narration_label.text = message

def get_target_at_coord(self, tile_x: int, tile_y: int) -> Optional[tuple[str, dict]]:
    """
    Checks if an NPC or interactable object exists at these tile coordinates.
    Returns a tuple: (target_type, target_data) or None
    """
    # 1. Check for NPCs
    for npc in self.location_context.get('npcs', []):
        coords = npc.get('coordinates')
        if coords and coords[0] == tile_x and coords[1] == tile_y:
            # Return 'npc' and the npc data dictionary
            return "npc", npc

    # 2. Check for Interactable Objects (ai_annotations)
    annotations = self.location_context.get('ai_annotations', {})
    for obj_id, obj_data in annotations.items():
        coords = obj_data.get('coordinates')
        if coords and coords[0] == tile_x and coords[1] == tile_y:
            # Add the ID to the data so we can reference it
            obj_data['id'] = obj_id
            # Return 'object' and the annotation data
            return "object", obj_data

    # 3. Nothing found
    return None

def handle_examine(self, target_type: str, target_data: dict):
    """(Client-side) Displays the description of a target."""
    desc = "You see nothing special."
    if target_type == "npc":
        # We'd eventually get this from the rules_api, but for now, use template_id
        desc = f"You see a {target_data.get('template_id', 'creature')}."
    elif target_type == "object":
        desc = target_data.get('description', f"You see a {target_data.get('id', 'thing')}.")

    self.update_narration(desc)
    self.update_log(f"Examined: {target_data.get('id', target_data.get('template_id', 'target'))}")

def open_context_menu(self, target_type: str, target_data: dict, touch_pos):
    """Creates and displays a right-click context menu."""
    # Close any old menu
    self.close_context_menu()

    menu_items = []
    target_id = target_data.get('id') or target_data.get('template_id')

    # --- 1. Define Menu Items ---
    if target_type == "npc":
        menu_items.append(("Examine", partial(self.handle_examine, target_type, target_data)))
        menu_items.append(("Attack", partial(self.initiate_combat, target_data))) # Use our existing combat function
        menu_items.append(("Talk", partial(self.handle_interaction, target_id, "talk"))) # 'talk' is a placeholder

    elif target_type == "object":
        menu_items.append(("Examine", partial(self.handle_examine, target_type, target_data)))
        menu_items.append(("Use", partial(self.handle_interaction, target_id, "use")))

    if not menu_items:
        return # No actions

    # --- 2. Build Kivy Widgets ---
    self.context_menu = BoxLayout(
        orientation='vertical',
        size_hint=(None, None),
        width='150dp',
        height=f"{len(menu_items) * 44}dp",
        pos=touch_pos # Display at the click position
    )

    for text, callback in menu_items:
        btn = Button(
            text=text,
            size_hint_y=None,
            height='44dp'
        )
        btn.bind(on_release=callback)
        self.context_menu.add_widget(btn)

    # Add the menu to the root layout (not the map)
    self.add_widget(self.context_menu)

def close_context_menu(self, *args):
    """Removes the context menu if it exists."""
    if self.context_menu:
        self.remove_widget(self.context_menu)
        self.context_menu = None

def handle_interaction(self, target_id: str, action_type: str, *args):
    """
    (Client -> Monolith) Calls the monolith's story module to perform an action.
    """
    self.close_context_menu()

    if not story_api or not story_schemas:
        self.update_narration("Error: Story module not loaded.")
        return

    actor_id = self.active_character_context.id
    loc_id = self.active_character_context.current_location_id

    self.update_log(f"Attempting '{action_type}' on '{target_id}'...")

    try:
        # 1. Create the request schema
        request = story_schemas.InteractionRequest(
            actor_id=actor_id,
            location_id=loc_id,
            target_object_id=target_id, # The handler expects this field
            interaction_type=action_type
        )

        # 2. Call the synchronous story_api function
        response_dict = story_api.handle_interaction(request)

        # 3. Process the response dictionary
        response = story_schemas.InteractionResponse(**response_dict)

        self.update_narration(response.message)

        # 4. If the world state changed, we must update our local context
        if response.success and response.updated_annotations:
            self.location_context['ai_annotations'] = response.updated_annotations
            # Re-render the scene to show changes (e.g., open door)
            self.build_scene()

        # TODO: Handle items_added, items_removed

    except Exception as e:
        logging.exception(f"Interaction failed: {e}")
        self.update_narration(f"An error occurred: {e}")

def initiate_combat(self, target_npc: dict):
    """
    (Client -> Monolith) Calls the story API to start a combat encounter.
    """
    if not story_api or not story_schemas:
        self.update_narration("Error: Story module not loaded.")
        return

    app = App.get_running_app()
    actor_id = self.active_character_context.id
    loc_id = self.active_character_context.current_location_id

    # NPCs in the location_context are dicts, not full schemas.
    # We need the template_id to start combat.
    npc_template_id = target_npc.get('template_id')
    if not npc_template_id:
        self.update_log(f"Cannot start combat: NPC has no template_id.")
        return

    self.update_log(f"You attack the {npc_template_id}!")

    try:
        # 1. Create the request schema
        request = story_schemas.CombatStartRequest(
            location_id=loc_id,
            player_ids=[actor_id], # Just our active player for now
            npc_template_ids=[npc_template_id] # Just the NPC we clicked
        )

        # 2. Call the new synchronous story_api function
        combat_state_dict = story_api.start_combat(request)

        # 3. Store the combat state in the app
        app.game_settings['combat_state'] = combat_state_dict

        # 4. Transition to the Combat Screen
        app.root.current = 'combat_screen'

    except Exception as e:
        logging.exception(f"Failed to start combat: {e}")
        self.update_narration(f"An error occurred: {e}")

# --- Add these new methods inside the MainInterfaceScreen class ---

def is_tile_passable(self, tile_x: int, tile_y: int) -> bool:
    """Checks if a given tile coordinate is walkable."""
    if not self.location_context:
        return False
    tile_map = self.location_context.get('generated_map_data')
    if not tile_map:
        return False

    map_height = len(tile_map)
    map_width = len(tile_map[0])

    # 1. Check map bounds
    if not (0 <= tile_x < map_width and 0 <= tile_y < map_height):
        return False

    # 2. Get tile ID from map data
    try:
        tile_id = tile_map[tile_y][tile_x] # y is row, x is col
    except IndexError:
        return False

    # 3. Get tile definition from asset loader
    tile_def = asset_loader.get_tile_definition(tile_id)
    if not tile_def:
        logging.warning(f"No tile definition found for ID {tile_id}")
        return False # Unknown tiles are not passable

    # 4. Return the 'passable' status
    return tile_def.get('passable', False)

def move_player_to(self, tile_x: int, tile_y: int):
    """Calls the monolith to update position and moves the sprite."""
    if not self.active_character_context or not self.player_sprite:
        return

    try:
        # 1. Call Monolith to update the database
        char_id = self.active_character_context.id
        loc_id = self.active_character_context.current_location_id
        new_coords = [tile_x, tile_y]

        # This is a synchronous, direct-call to the monolith module
        updated_context_dict = character_api.update_character_location(
            char_id, loc_id, new_coords
        )

        # 2. Update local context in memory
        self.active_character_context.position_x = updated_context_dict.get('position_x', tile_x)
        self.active_character_context.position_y = updated_context_dict.get('position_y', tile_y)

        # 3. Update sprite position on screen
        map_height = len(self.location_context.get('generated_map_data', []))
        # Kivy Y is flipped
        render_y = (map_height - 1 - tile_y) * TILE_SIZE
        self.player_sprite.pos = (tile_x * TILE_SIZE, render_y)

        self.update_log(f"Moved to ({tile_x}, {tile_y})")

    except Exception as e:
        logging.exception(f"Failed to move player: {e}")
        self.update_log(f"Error: Could not move player.")

def on_touch_down(self, touch):
    """Handle mouse/touch input."""

    # If a context menu is open, a click anywhere should close it.
    if self.context_menu:
        # Check if the click is *outside* the menu
        if not self.context_menu.collide_point(*touch.pos):
            self.close_context_menu()
        return True # Consume the touch

    # Check if the click is within the map rendering area
    if not self.render_layout or not self.render_layout.collide_point(*touch.pos):
        # If click is outside the map, let Kivy handle it (e.g., for buttons)
        return super().on_touch_down(touch)

    # --- Click is on the map ---

    # 1. Convert window coordinates to tile coordinates
    local_pos = self.render_layout.to_local(*touch.pos)
    tile_x = int(local_pos[0] // TILE_SIZE)

    map_height = len(self.location_context.get('generated_map_data', []))
    if map_height == 0:
        return True # No map

    tile_y = (map_height - 1) - int(local_pos[1] // TILE_SIZE)

    logging.debug(f"Map click at tile ({tile_x}, {tile_y}) - Button: {touch.button}")

    # 2. Check for target at this coordinate
    target = self.get_target_at_coord(tile_x, tile_y)

    # 3. Handle Left-Click (Move or Examine)
    if touch.button == 'left':
        if target:
            # Target found: Examine it
            target_type, target_data = target
            self.handle_examine(target_type, target_data)
        else:
            # No target: Attempt to move
            if self.is_tile_passable(tile_x, tile_y):
                self.move_player_to(tile_x, tile_y)
            else:
                logging.info(f"Clicked impassable tile at ({tile_x}, {tile_y})")
                self.update_log("You can't move there.")

    # 4. Handle Right-Click (Context Menu)
    elif touch.button == 'right':
        if target:
            # Target found: Open context menu
            target_type, target_data = target
            self.open_context_menu(target_type, target_data, touch.pos)
        else:
            # No target: Do nothing
            logging.debug("Right-clicked on empty tile.")
            pass

    return True # We consumed the touch
