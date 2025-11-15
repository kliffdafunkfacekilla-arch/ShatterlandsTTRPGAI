"""
The Main Game Interface screen.
Handles the exploration UI and game logic.
"""
import logging
import datetime
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup # <-- ADD THIS IMPORT
from kivy.properties import ObjectProperty, ListProperty, StringProperty
from kivy.core.window import Window
from kivy.clock import Clock
from functools import partial
from typing import Optional

# --- Monolith Imports ---
try:
    from monolith.modules.character_pkg import crud as char_crud
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
    from monolith.modules.world_pkg import crud as world_crud
    from monolith.modules.world_pkg.database import SessionLocal as WorldSession
    from monolith.modules import character as character_api
    from monolith.modules import story as story_api
    from monolith.modules import save_api # <-- ADD THIS IMPORT
    from monolith.modules.story_pkg import schemas as story_schemas
except ImportError as e:
    logging.error(f"MAIN_INTERFACE: Failed to import monolith modules: {e}")
    char_crud, char_services, CharSession = None, None, None
    world_crud, WorldSession = None, None
    character_api, story_api, story_schemas = None, None, None
    save_api = None # <-- ADD THIS

# --- Client Imports ---
try:
    from game_client import asset_loader
    from game_client.views.map_view_widget import MapViewWidget # <-- IMPORT OUR NEW WIDGET
except ImportError as e:
    logging.error(f"MAIN_INTERFACE: Failed to import client modules: {e}")
    asset_loader = None
    MapViewWidget = None

# Constants
TILE_SIZE = 64 # Must match the MapViewWidget's TILE_SIZE

# --- Kivy Language (KV) String for the UI Layout ---
MAIN_INTERFACE_KV = """
<MainInterfaceScreen>:
    log_label: log_label
    narration_label: narration_label
    dm_input: dm_input
    party_panel: party_panel
    active_char_name: active_char_name
    active_char_status: active_char_status
    party_list_container: party_list_container
    map_view_anchor: map_view_anchor
    AnchorLayout:
        AnchorLayout:
            anchor_x: 'center'
            anchor_y: 'center'
            BoxLayout:
                id: map_view_anchor
                size_hint: None, None
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
                    on_text_validate: root.on_submit_narration(self)
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
                    text: 'Save Game' # <-- ADD THIS BUTTON
                    on_release: root.show_save_popup()

                Button:
                    text: 'Character'
                    on_release: app.root.current = 'character_sheet'
                Button:
                    text: 'Inventory'
                    on_release: app.root.current = 'inventory'
                Button:
                    text: 'Quests'
                    on_release: app.root.current = 'quest_log'
"""
Builder.load_string(MAIN_INTERFACE_KV)

class MainInterfaceScreen(Screen):
    log_label = ObjectProperty(None)
    narration_label = ObjectProperty(None)
    dm_input = ObjectProperty(None)
    party_panel = ObjectProperty(None)
    active_char_name = ObjectProperty(None)
    active_char_status = ObjectProperty(None)
    party_list_container = ObjectProperty(None)
    map_view_widget = ObjectProperty(None)
    map_view_anchor = ObjectProperty(None)
    context_menu = ObjectProperty(None, allownone=True)
    active_character_context = ObjectProperty(None, force_dispatch=True)
    location_context = ObjectProperty(None, force_dispatch=True)
    party_list = ListProperty([])
    save_popup = ObjectProperty(None, allownone=True) # <-- ADD THIS

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if MapViewWidget:
            self.map_view_widget = MapViewWidget()
        else:
            logging.error("CRITICAL: MapViewWidget failed to import, UI will be broken.")
        self.bind(active_character_context=self.update_active_character_ui)
        self.bind(party_list=self.update_party_list_ui)
        Window.bind(on_resize=self.center_layout)

        # --- ADD BINDING FOR DM INPUT ---
        # We must schedule this to run after the KV string is loaded
        Clock.schedule_once(self._bind_inputs)

    def _bind_inputs(self, *args):
        """Bind inputs that aren't available during __init__."""
        if self.ids.dm_input:
            self.ids.dm_input.bind(on_text_validate=self.on_submit_narration)
        else:
            logging.error("Failed to bind dm_input, widget not found.")

    def center_layout(self, instance, width, height):
        if self.map_view_anchor:
            self.map_view_anchor.pos = (
                (width - self.map_view_anchor.width) / 2,
                (height - self.map_view_anchor.height) / 2
            )

    def on_enter(self, *args):
        logging.info("Entering Main Interface Screen. Loading game state...")
        if self.map_view_anchor and self.map_view_widget:
            self.map_view_anchor.clear_widgets()
            self.map_view_anchor.add_widget(self.map_view_widget)
        else:
            logging.error("CRITICAL: 'map_view_anchor' not found or MapViewWidget is None.")
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
        char_db = None
        try:
            char_db = CharSession()
            db_char = char_crud.get_character_by_name(char_db, char_name)
            if not db_char:
                raise Exception(f"Character '{char_name}' not found in database.")
            self.active_character_context = char_services.get_character_context(db_char)
            self.party_list = [self.active_character_context]
            logging.info(f"Loaded context for {self.active_character_context.name}")
        except Exception as e:
            logging.error(f"Failed to load character '{char_name}': {e}")
            if char_db: char_db.close()
            app.root.current = 'main_menu'
            return
        finally:
            if char_db: char_db.close()
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
        self.build_scene()
        self.center_layout(Window, Window.width, Window.height)

    def build_scene(self):
        if self.map_view_widget:
            self.map_view_widget.build_scene(
                self.location_context,
                self.active_character_context
            )
            self.map_view_anchor.size = self.map_view_widget.size
        else:
            logging.error("Cannot build scene, map_view_widget is None.")

    def update_active_character_ui(self, *args):
        if self.active_character_context:
            self.ids.active_char_name.text = self.active_character_context.name
            self.ids.active_char_status.text = f"HP: {self.active_character_context.current_hp} / {self.active_character_context.max_hp}"
        else:
            self.ids.active_char_name.text = "No Character"
            self.ids.active_char_status.text = "HP: --/--"

    def update_party_list_ui(self, *args):
        self.ids.party_list_container.clear_widgets()
        for char_context in self.party_list:
            party_member_label = Label(
                text=f"{char_context.name} (HP: {char_context.current_hp})",
                size_hint_y=None,
                height='30dp'
            )
            self.ids.party_list_container.add_widget(party_member_label)

    def update_log(self, message: str):
        self.ids.log_label.text += f"\n- {message}"

    def update_narration(self, message: str):
        self.ids.narration_label.text = message

    def get_map_height(self):
        tile_map = self.location_context.get('generated_map_data', [])
        return len(tile_map)

    def is_tile_passable(self, tile_x: int, tile_y: int) -> bool:
        if not self.location_context: return False
        tile_map = self.location_context.get('generated_map_data')
        if not tile_map: return False
        map_height = len(tile_map)
        map_width = len(tile_map[0]) if map_height > 0 else 0
        if not (0 <= tile_x < map_width and 0 <= tile_y < map_height):
            return False
        try:
            tile_id = tile_map[tile_y][tile_x]
        except IndexError:
            return False
        tile_def = asset_loader.get_tile_definition(str(tile_id))
        if not tile_def:
            logging.warning(f"No tile definition found for ID {tile_id}")
            return False
        return tile_def.get('passable', False)

    def move_player_to(self, tile_x: int, tile_y: int):
        if not self.active_character_context or not self.map_view_widget:
            return
        try:
            char_id = self.active_character_context.id
            loc_id = self.active_character_context.current_location_id
            new_coords = [tile_x, tile_y]
            updated_context_dict = character_api.update_character_location(
                char_id, loc_id, new_coords
            )
            self.active_character_context.position_x = updated_context_dict.get('position_x', tile_x)
            self.active_character_context.position_y = updated_context_dict.get('position_y', tile_y)
            self.map_view_widget.move_player_sprite(tile_x, tile_y, self.get_map_height())
            self.update_log(f"Moved to ({tile_x}, {tile_y})")
        except Exception as e:
            logging.exception(f"Failed to move player: {e}")
            self.update_log(f"Error: Could not move player.")

    def get_target_at_coord(self, tile_x: int, tile_y: int) -> Optional[tuple[str, dict]]:
        for npc in self.location_context.get('npcs', []):
            coords = npc.get('coordinates')
            if coords and coords[0] == tile_x and coords[1] == tile_y:
                return "npc", npc
        annotations = self.location_context.get('ai_annotations', {})
        for obj_id, obj_data in annotations.items():
            coords = obj_data.get('coordinates')
            if coords and coords[0] == tile_x and coords[1] == tile_y:
                obj_data['id'] = obj_id
                return "object", obj_data
        return None

    def handle_examine(self, target_type: str, target_data: dict, *args):
        self.close_context_menu()
        desc = "You see nothing special."
        if target_type == "npc":
            desc = f"You see a {target_data.get('template_id', 'creature')}."
        elif target_type == "object":
            desc = target_data.get('description', f"You see a {target_data.get('id', 'thing')}.")
        self.update_narration(desc)
        self.update_log(f"Examined: {target_data.get('id', target_data.get('template_id', 'target'))}")

    def open_context_menu(self, target_type: str, target_data: dict, touch_pos):
        self.close_context_menu()
        menu_items = []
        target_id = target_data.get('id') or target_data.get('template_id')
        if target_type == "npc":
            menu_items.append(("Examine", partial(self.handle_examine, target_type, target_data)))
            menu_items.append(("Attack", partial(self.initiate_combat, target_data)))
            menu_items.append(("Talk", partial(self.handle_interaction, target_id, "talk")))
        elif target_type == "object":
            menu_items.append(("Examine", partial(self.handle_examine, target_type, target_data)))
            menu_items.append(("Use", partial(self.handle_interaction, target_id, "use")))
            menu_items.append(("Bash", partial(self.handle_interaction, target_id, "bash")))
        if not menu_items: return
        self.context_menu = BoxLayout(
            orientation='vertical', size_hint=(None, None),
            width='150dp', height=f"{len(menu_items) * 44}dp",
            pos=touch_pos
        )
        for text, callback in menu_items:
            btn = Button(text=text, size_hint_y=None, height='44dp')
            btn.bind(on_release=callback)
            self.context_menu.add_widget(btn)
        self.add_widget(self.context_menu)

    def close_context_menu(self, *args):
        if self.context_menu:
            self.remove_widget(self.context_menu)
            self.context_menu = None

    def handle_interaction(self, target_id: str, action_type: str, *args):
        self.close_context_menu()
        if not story_api or not story_schemas:
            self.update_narration("Error: Story module not loaded.")
            return
        actor_id = self.active_character_context.id
        loc_id = self.active_character_context.current_location_id
        self.update_log(f"Attempting '{action_type}' on '{target_id}'...")
        try:
            request = story_schemas.InteractionRequest(
                actor_id=actor_id, location_id=loc__id,
                target_object_id=target_id, interaction_type=action_type
            )
            response_dict = story_api.handle_interaction(request)
            response = story_schemas.InteractionResponse(**response_dict)
            self.update_narration(response.message)
            if response.success and response.updated_annotations:
                self.location_context['ai_annotations'] = response.updated_annotations
                self.build_scene()
        except Exception as e:
            logging.exception(f"Interaction failed: {e}")
            self.update_narration(f"An error occurred: {e}")

    def initiate_combat(self, target_npc: dict, *args):
        self.close_context_menu()
        if not story_api or not story_schemas:
            self.update_narration("Error: Story module not loaded.")
            return
        app = App.get_running_app()
        actor_id = self.active_character_context.id
        loc_id = self.active_character_context.current_location_id
        npc_template_id = target_npc.get('template_id')
        if not npc_template_id:
            self.update_log(f"Cannot start combat: NPC has no template_id.")
            return
        self.update_log(f"You attack the {npc_template_id}!")
        try:
            request = story_schemas.CombatStartRequest(
                location_id=loc_id, player_ids=[actor_id],
                npc_template_ids=[npc_template_id]
            )
            combat_state_dict = story_api.start_combat(request)
            app.game_settings['combat_state'] = combat_state_dict
            app.root.current = 'combat_screen'
        except Exception as e:
            logging.exception(f"Failed to start combat: {e}")
            self.update_narration(f"An error occurred: {e}")

    def on_touch_down(self, touch):
        if self.context_menu:
            if not self.context_menu.collide_point(*touch.pos):
                self.close_context_menu()
            return True
        if not self.map_view_widget or not self.map_view_widget.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        local_pos = self.map_view_widget.to_local(*touch.pos)
        tile_x = int(local_pos[0] // TILE_SIZE)
        map_height = self.get_map_height()
        if map_height == 0: return True
        tile_y = (map_height - 1) - int(local_pos[1] // TILE_SIZE)
        logging.debug(f"Map click at tile ({tile_x}, {tile_y}) - Button: {touch.button}")
        target = self.get_target_at_coord(tile_x, tile_y)
        if touch.button == 'left':
            if target:
                target_type, target_data = target
                self.handle_examine(target_type, target_data)
            else:
                if self.is_tile_passable(tile_x, tile_y):
                    self.move_player_to(tile_x, tile_y)
                else:
                    logging.info(f"Clicked impassable tile at ({tile_x}, {tile_y})")
                    self.update_log("You can't move there.")
        elif touch.button == 'right':
            if target:
                target_type, target_data = target
                self.open_context_menu(target_type, target_data, touch.pos)
            else:
                logging.debug("Right-clicked on empty tile.")
        return True

    # --- ADD THESE NEW METHODS for the Save Popup ---

    def show_save_popup(self):
        """Displays a popup to get a save game name."""
        if self.save_popup:
            self.save_popup.dismiss()

        # Get a default name
        char_name = self.active_character_context.name if self.active_character_context else "save"
        default_save_name = f"{char_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"

        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')

        content.add_widget(Label(text='Enter a name for your save file:'))

        text_input = TextInput(
            text=default_save_name,
            size_hint_y=None,
            height='44dp',
            multiline=False
        )
        content.add_widget(text_input)

        button_layout = BoxLayout(size_hint_y=None, height='44dp', spacing='10dp')

        save_btn = Button(text='Save')
        cancel_btn = Button(text='Cancel')

        button_layout.add_widget(save_btn)
        button_layout.add_widget(cancel_btn)
        content.add_widget(button_layout)

        self.save_popup = Popup(
            title='Save Game',
            content=content,
            size_hint=(0.5, 0.4),
            auto_dismiss=False
        )

        save_btn.bind(on_release=lambda x: self.do_save_game(text_input.text))
        cancel_btn.bind(on_release=self.save_popup.dismiss)

        self.save_popup.open()

    def do_save_game(self, slot_name: str):
        """Calls the save_api and closes the popup."""
        if not slot_name:
            return # Or show an error in the popup

        if not save_api:
            logging.error("Save API not loaded. Cannot save.")
            self.save_popup.dismiss()
            return

        try:
            result = save_api.save_game(slot_name)
            if result.get("success"):
                self.update_log(f"Game saved as '{slot_name}'")
            else:
                raise Exception(result.get("error", "Unknown save error"))
        except Exception as e:
            logging.exception(f"Failed to save game: {e}")
            self.update_log(f"Error saving game: {e}")

        self.save_popup.dismiss()
        self.save_popup = None

    def on_submit_narration(self, instance):
        """Called when the user presses Enter in the DM input box."""
        prompt_text = instance.text
        if not prompt_text:
            return # Ignore empty submits

        instance.text = "" # Clear the input box

        if not self.active_character_context:
            logging.error("Cannot submit prompt, no active character.")
            return

        if not story_api:
            logging.error("Cannot submit prompt, story_api not loaded.")
            self.update_narration("Error: Story module not loaded.")
            return

        actor_id = self.active_character_context.id
        self.update_log(f"You: {prompt_text}") # Log the player's prompt

        try:
            # Call the new backend function
            response = story_api.handle_narrative_prompt(actor_id, prompt_text)
            self.update_narration(response.get("message", "An error occurred."))
        except Exception as e:
            logging.exception(f"Error handling narrative prompt: {e}")
            self.update_narration(f"Error: {e}")
