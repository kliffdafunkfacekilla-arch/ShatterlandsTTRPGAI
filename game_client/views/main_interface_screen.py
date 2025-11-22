"""
The Main Game Interface screen.
Handles the exploration UI and game logic.
"""
import logging
from kivy.app import App
from kivy.lang import Builder
# ... (other Kivy imports)
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, ListProperty, StringProperty
from kivy.core.window import Window
from functools import partial
from typing import Optional, List
import datetime # <-- Import datetime for save game popup

# --- Monolith Imports ---
# ... (imports unchanged, make sure char_crud, char_services, etc. are imported) ...
try:
    from monolith.modules.character_pkg import crud as char_crud
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
    from monolith.modules.world_pkg import crud as world_crud
    from monolith.modules.world_pkg.database import SessionLocal as WorldSession
    from monolith.modules import character as character_api
    from monolith.modules import story as story_api
    from monolith.modules import save_api
    from monolith.modules.story_pkg import schemas as story_schemas
    from monolith.modules.character_pkg.schemas import CharacterContextResponse
    from monolith.modules.camp_pkg import schemas as camp_schemas
except ImportError as e:
    logging.error(f"MAIN_INTERFACE: Failed to import monolith modules: {e}")
    # ... (all set to None)
    CharacterContextResponse = None # Add this
    char_crud, char_services, CharSession = None, None, None
    world_crud, WorldSession = None, None
    character_api, story_api, story_schemas = None, None, None
    save_api = None
    CharacterContextResponse = None

# --- Client Imports ---
try:
    from game_client import asset_loader
    from game_client.views.map_view_widget import MapViewWidget
except ImportError as e:
    logging.error(f"MAIN_INTERFACE: Failed to import client modules: {e}")
    asset_loader = None
    MapViewWidget = None

TILE_SIZE = 64


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
                    on_release:
                        app.root.get_screen('settings').previous_screen = 'main_interface'
                        app.root.current = 'settings'
                Button:
                    text: 'Save Game'
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
                Button:
                    text: 'Rest'
                    on_release: root.on_rest()
                Button:
                    text: 'Shop'
                    on_release: app.root.current = 'shop_screen'
"""
Builder.load_string(MAIN_INTERFACE_KV)

class MainInterfaceScreen(Screen):
    """
    The primary gameplay screen for exploration.

    Displays the map, party status, chat/log, and action buttons.
    Handles movement, resting, saving, and transitioning to other screens (Combat, Shop, etc.).
    """
    # ... (all existing ObjectProperty references) ...
    log_label = ObjectProperty(None)
    narration_label = ObjectProperty(None)
    dm_input = ObjectProperty(None)
    party_panel = ObjectProperty(None)
    active_char_name = ObjectProperty(None)
    active_char_status = ObjectProperty(None)
    party_list_container = ObjectProperty(None)
    map_view_widget = ObjectProperty(None)
    map_view_anchor = ObjectProperty(None)

    # --- MODIFIED: State Properties ---
    active_character_context = ObjectProperty(None, force_dispatch=True, allownone=True)
    location_context = ObjectProperty(None, force_dispatch=True, allownone=True)
    save_popup = ObjectProperty(None, allownone=True)

    # This holds the full context for ALL party members
    party_contexts = ListProperty([])
    # This is bound to the UI panel
    party_list = ListProperty([])

    def __init__(self, **kwargs):
        """
        Initializes the screen layout and widget bindings.
        """
        super().__init__(**kwargs)
        if MapViewWidget:
            self.map_view_widget = MapViewWidget()
        else:
            logging.error("CRITICAL: MapViewWidget failed to import, UI will be broken.")

        # --- BINDINGS ---
        self.bind(active_character_context=self.update_active_character_ui)
        self.bind(party_list=self.update_party_list_ui) # This now updates the party panel
        Window.bind(on_resize=self.center_layout)

        # We must schedule this to run after the KV string is loaded
        from kivy.clock import Clock
        Clock.schedule_once(self._bind_inputs)

    def _bind_inputs(self, *args):
        """Bind inputs that aren't available during __init__."""
        if self.ids.dm_input:
            self.ids.dm_input.bind(on_text_validate=self.on_submit_narration)
        else:
            logging.error("Failed to bind dm_input, widget not found.")

    def center_layout(self, instance, width, height):
        """
        Centers the map view within the screen.
        """
        if self.map_view_anchor:
            self.map_view_anchor.pos = (
                (width - self.map_view_anchor.width) / 2,
                (height - self.map_view_anchor.height) / 2
            )

    def on_enter(self, *args):
        """
        Called when the screen becomes active.
        Loads the full game state (party, location) and renders the scene.
        """
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

        # --- MODIFIED: Load Full Party ---
        char_names = app.game_settings.get('party_list')
        if not char_names:
            logging.error("No party_list in game settings! Returning to menu.")
            app.root.current = 'main_menu'
            return

        if not char_crud or not world_crud or not asset_loader:
            logging.error("A required monolith module or asset loader is not available.")
            return

        self.party_contexts.clear()
        char_db = None
        try:
            char_db = CharSession()
            loaded_contexts = []
            for char_name in char_names:
                db_char = char_crud.get_character_by_name(char_db, char_name)
                if not db_char:
                    raise Exception(f"Character '{char_name}' not found in database.")

                context = char_services.get_character_context(db, db_char.id)
                self.party_contexts.append(context)
                loaded_contexts.append(context)

            # --- FIX: Ensure party_contexts is updated ---
            self.party_contexts = loaded_contexts
            # --- END FIX ---

            # Set the first character as active by default
            if self.party_contexts:
                self.active_character_context = self.party_contexts[0]
            # Set the party_list to trigger the UI update
            self.party_list = self.party_contexts

            logging.info(f"Loaded party: {[c.name for c in self.party_contexts]}")

        except Exception as e:
            logging.error(f"Failed to load party: {e}")
            if char_db: char_db.close()
            app.root.current = 'main_menu'
            return
        finally:
            if char_db: char_db.close()
        # --- END MODIFIED ---

        # ... (Location loading is unchanged) ...
        world_db = None
        try:
            if self.active_character_context:
                loc_id = self.active_character_context.current_location_id # Use active char's location
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
            # --- MODIFIED: Pass the full party list ---
            self.map_view_widget.build_scene(
                self.location_context,
                self.party_contexts # Pass the full list
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
        """
        MODIFIED: Creates clickable buttons for each party member.
        """
        self.ids.party_list_container.clear_widgets()
        for char_context in self.party_list:

            # --- Use a Button instead of a Label ---
            party_member_button = Button(
                text=f"{char_context.name} (HP: {char_context.current_hp})",
                size_hint_y=None,
                height='30dp'
            )

            # Highlight the active character
            if self.active_character_context and (char_context.id == self.active_character_context.id):
                party_member_button.background_color = (0.5, 0.5, 1, 1) # Blueish tint
            else:
                party_member_button.background_color = (1, 1, 1, 1) # Default color

            # Bind the button to switch active character
            party_member_button.bind(on_release=partial(self.set_active_character, char_context))

            self.ids.party_list_container.add_widget(party_member_button)

    def set_active_character(self, char_context, *args):
        """Callback to switch the active character."""
        self.active_character_context = char_context
        self.update_log(f"{char_context.name} is now the active character.")
        # Re-firing update_party_list_ui will update the highlighting
        self.update_party_list_ui()

    def update_log(self, message: str):
        self.ids.log_label.text += f"\n- {message}"

    def update_narration(self, message: str):
        self.ids.narration_label.text = message

    def get_map_height(self):
        tile_map = self.location_context.get('generated_map_data', []) if self.location_context else []
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
            char_id = self.active_character_context.id # Use active char's ID
            loc_id = self.active_character_context.current_location_id
            new_coords = [tile_x, tile_y]

            updated_context_dict = character_api.update_character_location(
                char_id, loc_id, new_coords
            )

            # --- Refresh the specific character in the master list ---
            # Create a new CharacterContextResponse object from the updated dict
            # This ensures Kivy properties are updated correctly
            updated_char_context = CharacterContextResponse(**updated_context_dict)

            # Update the active_character_context
            self.active_character_context = updated_char_context

            # Update the context in our list (self.party_contexts)
            for i, ctx in enumerate(self.party_contexts):
                if ctx.id == char_id: # Use char_id to match the character being moved
                    self.party_contexts[i] = updated_char_context
                    break
            self.party_list = list(self.party_contexts) # Trigger UI refresh

            # --- Call the new move function on the map_view_widget ---
            self.map_view_widget.move_active_player_sprite(
                char_id, tile_x, tile_y, self.get_map_height()
            )
            self.update_log(f"{self.active_character_context.name} moved to ({tile_x}, {tile_y})")

        except Exception as e:
            logging.exception(f"Failed to move player: {e}")
            self.update_log(f"Error: Could not move player.")

    def on_submit_narration(self, *args):
        pass

    def show_save_popup(self):
        pass

    def on_submit_narration(self, instance):
        """Called when the user presses Enter in the DM input box."""
        prompt_text = instance.text
        if not prompt_text:
            return
        instance.text = ""
        if not self.active_character_context:
            logging.error("Cannot submit prompt, no active character.")
            return
        if not story_api:
            logging.error("Cannot submit prompt, story_api not loaded.")
            self.update_narration("Error: Story module not loaded.")
            return
        actor_id = self.active_character_context.id
        self.update_log(f"You: {prompt_text}")
        try:
            response = story_api.handle_narrative_prompt(actor_id, prompt_text)
            self.update_narration(response.get("message", "An error occurred."))
        except Exception as e:
            logging.exception(f"Error handling narrative prompt: {e}")
            self.update_narration(f"Error: {e}")

    def on_rest(self):
        """Called when the 'Rest' button is pressed."""
        if not self.active_character_context or not story_api:
            self.update_log("Cannot rest right now.")
            return
        try:
            char_id = self.active_character_context.id
            rest_request = camp_schemas.CampRestRequest(char_id=char_id, duration=8) # Rest for 8 hours
            self.update_log("You rest for 8 hours...")
            updated_context_dict = story_api.rest_at_camp(rest_request)
            new_context = CharacterContextResponse(**updated_context_dict)
            for i, ctx in enumerate(self.party_contexts):
                if ctx.id == char_id:
                    self.party_contexts[i] = new_context
                    break
            self.active_character_context = new_context
            self.party_list = list(self.party_contexts)
            self.update_log("You feel refreshed. HP and Composure restored.")
        except Exception as e:
            logging.exception(f"Error during rest: {e}")
            self.update_log(f"Rest failed: {e}")

    def show_save_popup(self):
        """Displays a popup to get a save game name."""
        if self.save_popup:
            self.save_popup.dismiss()
        char_name = self.active_character_context.name if self.active_character_context else "save"
        default_save_name = f"{char_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        content.add_widget(Label(text='Enter a name for your save file:'))
        text_input = TextInput(text=default_save_name, size_hint_y=None, height='44dp', multiline=False)
        content.add_widget(text_input)
        button_layout = BoxLayout(size_hint_y=None, height='44dp', spacing='10dp')
        save_btn = Button(text='Save')
        cancel_btn = Button(text='Cancel')
        button_layout.add_widget(save_btn)
        button_layout.add_widget(cancel_btn)
        content.add_widget(button_layout)
        self.save_popup = Popup(title='Save Game', content=content, size_hint=(0.5, 0.4), auto_dismiss=False)
        save_btn.bind(on_release=lambda x: self.do_save_game(text_input.text))
        cancel_btn.bind(on_release=self.save_popup.dismiss)
        self.save_popup.open()

    def do_save_game(self, slot_name: str):
        """Calls the save_api and closes the popup."""
        if not slot_name: return
        if not save_api:
            logging.error("Save API not loaded. Cannot save.")
            self.save_popup.dismiss()
            return
        try:
            result = save_api.save_game(slot_name)
            if result.get("success"):
                self.update_log(f"Game saved to slot: {slot_name}")
            else:
                self.update_log(f"Save failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logging.exception(f"Error calling save_game: {e}")
            self.update_log(f"Save failed: {e}")
        self.save_popup.dismiss()

    def on_touch_down(self, touch):
        """Handle clicks on the map for movement."""
        if not self.map_view_widget or not self.map_view_widget.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if self.active_character_context and self.location_context:
            local_pos = self.map_view_widget.to_local(*touch.pos)
            tile_x = int(local_pos[0] // TILE_SIZE)
            map_height = self.get_map_height()
            if map_height == 0: return True
            tile_y = (map_height - 1) - int(local_pos[1] // TILE_SIZE)
            target_npc = None
            for npc in self.location_context.get('npcs', []):
                coords = npc.get('coordinates')
                if coords and coords[0] == tile_x and coords[1] == tile_y:
                    target_npc = npc
                    break
            if target_npc:
                self.update_log(f"You start a conversation with {target_npc.get('template_id')}.")
                app = App.get_running_app()
                dialogue_id = "old_man_willow"
                app.game_settings['pending_dialogue'] = {
                    'dialogue_id': dialogue_id,
                    'start_node_id': 'intro'
                }
                app.root.current = 'dialogue_screen'
                return True
            if self.is_tile_passable(tile_x, tile_y):
                self.move_player_to(tile_x, tile_y)
                return True
            else:
                self.update_log("You can't move there.")
                return True
        return super().on_touch_down(touch)
