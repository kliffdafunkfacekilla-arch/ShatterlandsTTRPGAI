"""
The Main Game Interface screen.
Handles rendering the game world, entities, and all UI panels.
"""import loggingfrom kivy.app import Appfrom kivy.lang import Builderfrom kivy.uix.screenmanager import Screenfrom kivy.uix.floatlayout import FloatLayoutfrom kivy.uix.boxlayout import BoxLayoutfrom kivy.uix.anchorlayout import AnchorLayoutfrom kivy.uix.scrollview import ScrollViewfrom kivy.uix.label import Labelfrom kivy.uix.textinput import TextInputfrom kivy.uix.button import Buttonfrom kivy.uix.image import Imagefrom kivy.properties import ObjectProperty, ListProperty, StringPropertyfrom kivy.core.window import Window# --- Monolith Imports ---try:
from monolith.modules.character_pkg import crud as char_crud
from monolith.modules.character_pkg import services as char_services
from monolith.modules.character_pkg.database import SessionLocal as CharSession
from monolith.modules.world_pkg import crud as world_crud
from monolith.modules.world_pkg.database import SessionLocal as WorldSessionexcept ImportError as e:
logging.error(f"MAIN_INTERFACE: Failed to import monolith modules: {e}")
char_crud, char_services, CharSession = None, None, None
world_crud, WorldSession = None, None# --- Client Asset Loader ---try:
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

player_image = Image(
source=sheet_path,
texture=asset_loader.get_texture(sheet_path),
tex_coords=(u, v, u2, v2),
size_hint=(None, None),
size=(TILE_SIZE, TILE_SIZE),
pos=(player.position_x * TILE_SIZE, render_y)
)
self.render_layout.add_widget(player_image)
self.entity_sprites.append(player_image)
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
