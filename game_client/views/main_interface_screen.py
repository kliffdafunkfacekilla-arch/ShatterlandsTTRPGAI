"""The Main Game Interface screen.
Handles the exploration UI and game logic."""
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
import threading
from kivy.clock import mainthread

# --- Monolith Imports ---
# Updated to use Orchestrator instead of database
try:
    from monolith.modules.story_pkg import schemas as story_schemas
    from monolith.modules.camp_pkg import schemas as camp_schemas
except ImportError as e:
    logging.error(f"MAIN_INTERFACE: Failed to import monolith modules: {e}")
    story_schemas = None
    camp_schemas = None

# --- Client Imports ---
try:
    from game_client import asset_loader
    from game_client.views.map_view_widget import MapViewWidget
    from game_client import debug_utils
    from game_client.utils import AsyncHelper
except ImportError as e:
    logging.error(f"MAIN_INTERFACE: Failed to import client modules: {e}")
    asset_loader = None
    MapViewWidget = None

TILE_SIZE = 64


MAIN_INTERFACE_KV = '''
<MainInterfaceScreen>:
    log_label: log_label
    narration_label: narration_label
    dm_input: dm_input
    party_panel: party_panel
    active_char_name: active_char_name
    active_char_status: active_char_status
    party_list_container: party_list_container
    map_view_anchor: map_view_anchor

    FloatLayout:
        # --- Map Layer (Bottom) ---
        BoxLayout:
            id: map_view_anchor
            size_hint: 1, 1
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}

        # --- UI Layer (Top) ---
        
        # Top Bar (Menu)
        BoxLayout:
            orientation: 'horizontal'
            size_hint: 1, None
            height: '48dp'
            pos_hint: {'top': 1}
            DungeonBackground:
                orientation: 'horizontal'
                DungeonButton:
                    text: 'Menu'
                    on_release:
                        app.root.get_screen('settings').previous_screen = 'main_interface'
                        app.root.current = 'settings'
                DungeonButton:
                    text: 'Debug'
                    on_release: root.show_debug_popup()
                DungeonButton:
                    text: 'Save Game'
                    on_release: root.show_save_popup()
                DungeonButton:
                    text: 'Inventory'
                    on_release: app.root.current = 'inventory'
                DungeonButton:
                    text: 'Quest Log'
                    on_release: app.root.current = 'quest_log'
                DungeonButton:
                    text: 'Character'
                    on_release: app.root.current = 'character_sheet'

        # Left Panel (Log & Party)
        BoxLayout:
            orientation: 'vertical'
            size_hint: 0.25, 0.8
            pos_hint: {'x': 0.02, 'y': 0.05}
            spacing: '10dp'
            
            # Log
            ParchmentPanel:
                orientation: 'vertical'
                size_hint_y: 0.4
                ParchmentLabel:
                    text: 'Log'
                    size_hint_y: None
                    height: '30dp'
                    font_size: '18sp'
                    bold: True
                ScrollView:
                    ParchmentLabel:
                        id: log_label
                        text: 'Welcome to Shatterlands.'
                        font_size: '14sp'
                        size_hint_y: None
                        height: self.texture_size[1]
                        text_size: self.width, None
                        padding: '5dp'

            # Party
            ParchmentPanel:
                id: party_panel
                orientation: 'vertical'
                size_hint_y: 0.6
                ParchmentLabel:
                    text: 'Active Character'
                    size_hint_y: None
                    height: '30dp'
                    font_size: '18sp'
                    bold: True
                ParchmentLabel:
                    id: active_char_name
                    text: 'Character Name'
                    font_size: '16sp'
                    size_hint_y: 0.1
                ParchmentLabel:
                    id: active_char_status
                    text: 'HP: 100/100'
                    size_hint_y: 0.1
                ParchmentLabel:
                    text: 'Party'
                    size_hint_y: None
                    height: '30dp'
                    font_size: '16sp'
                    bold: True
                ScrollView:
                    BoxLayout:
                        id: party_list_container
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height

        # Right Panel (Narration)
        BoxLayout:
            orientation: 'vertical'
            size_hint: 0.3, 0.8
            pos_hint: {'right': 0.98, 'y': 0.05}
            ParchmentPanel:
                orientation: 'vertical'
                spacing: '10dp'
                ParchmentLabel:
                    text: 'Narration'
                    size_hint_y: None
                    height: '30dp'
                    font_size: '18sp'
                    bold: True
                ScrollView:
                    ParchmentLabel:
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
'''
Builder.load_string(MAIN_INTERFACE_KV)



class MainInterfaceScreen(Screen, AsyncHelper):
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
        Clock.schedule_once(self._subscribe_to_events, 0)  # NEW: Event Bus subscriptions

    def _subscribe_to_events(self, dt):
        """Subscribe to Event Bus for reactive updates"""
        app = App.get_running_app()
        
        if app.event_bus:
            # Subscribe to turn changes
            app.event_bus.subscribe("player.turn_start", self.on_turn_changed)
            
            # Subscribe to ability results
            app.event_bus.subscribe("action.ability", self.on_ability_result)
            
            # Subscribe to state updates
            app.event_bus.subscribe("game.state_updated", self.on_state_updated)
            
            logging.info("Main Interface subscribed to Event Bus")
        else:
            logging.warning("Event Bus not available")

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

        # --- UPDATED: Load from Orchestrator State ---
        if not app.orchestrator:
            logging.error("No orchestrator found! Returning to menu.")
            app.root.current = 'main_menu'
            return

        try:
            # Get current game state from Orchestrator
            state = app.orchestrator.get_current_state()
            
            if not state or not state.characters:
                logging.error("No game state or characters found! Returning to menu.")
                app.root.current = 'main_menu'
                return
            
            # Load party from state
            self.party_contexts.clear()
            loaded_contexts = list(state.characters)
            self.party_contexts = loaded_contexts
            
            # Set the first character as active by default OR keep existing
            if self.party_contexts:
                # Try to keep current active character if valid
                if app.active_character_context and any(c.id == app.active_character_context.id for c in self.party_contexts):
                    self.active_character_context = app.active_character_context
                else:
                    self.active_character_context = self.party_contexts[0]
                
                # Update global context
                app.active_character_context = self.active_character_context
            
            # Set the party_list to trigger the UI update
            self.party_list = self.party_contexts

            logging.info(f"Loaded party from Orchestrator: {[c.name for c in self.party_contexts]}")

        except Exception as e:
            logging.error(f"Failed to load party from Orchestrator: {e}")
            from game_client.ui_utils import show_error
            show_error("Load Error", f"Failed to load game state:\n{e}")
            Clock.schedule_once(lambda dt: setattr(app.root, 'current', 'main_menu'), 1)
            return
        
        # Location context - simplified (map data should be in game state if needed)
        # For now, we'll skip location loading since it requires database
        # This can be implemented later by storing location data in game state
        self.location_context = None
        logging.info("Location context skipped (to be implemented in game state)")

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
        app = App.get_running_app()
        app.active_character_context = char_context
        
        # Save persistence
        if hasattr(app, 'app_settings'):
            app.app_settings['last_active_character_id'] = char_context.id
            from game_client import settings_manager
            settings_manager.save_settings(app.app_settings)
        self.update_log(f"{char_context.name} is now the active character.")
        # Re-firing update_party_list_ui will update the highlighting
        self.update_party_list_ui()

    # =========================================================================
    # EVENT BUS HANDLERS (NEW)
    # =========================================================================
    
    def on_turn_changed(self, player_id, player_name, **kwargs):
        """Called when hotseat turn changes"""
        self.update_log(f">>> It's {player_name}'s turn!")
        
        # Update active character if in party
        for char in self.party_contexts:
            if char.id == player_id:
                self.active_character_context = char
                break
    
    def on_ability_result(self, result, player_id, **kwargs):
        """Called when an ability is used"""
        if result.get("success"):
            narrative = result.get("narrative", "")
            if narrative:
                self.update_narration(narrative)
            
            # Show effects in log
            effects = result.get("effects_applied", [])
            for effect in effects:
                effect_type = effect.get('type', 'unknown')
                self.update_log(f"→ Effect: {effect_type}")
    
    def on_state_updated(self, **kwargs):
        """Called when game state changes"""
        # Refresh display from orchestrator
        app = App.get_running_app()
        
        if app.orchestrator:
            state = app.orchestrator.get_current_state()
            
            if state and state.characters:
                # Update party from state
                self.party_contexts = list(state.characters)
                self.party_list = self.party_contexts
                logging.info("Main Interface refreshed from game state")
    
    # =========================================================================
    # END EVENT BUS HANDLERS
    # =========================================================================

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
                events = result.get("events", [])
                if events:
                    # Example: Check for combat event
                    # In a real impl, we'd iterate and handle types
                    pass

            except Exception as e:
                logging.exception(f"Error updating UI after move: {e}")

        def on_fail(error):
            logging.exception(f"Failed to move player: {error}")
            self.update_log(f"Error: Could not move player.")

        self.run_async(background_task, on_complete, on_fail)

    def trigger_combat(self, encounter_id):
        """Transitions the game to the combat screen."""
        app = App.get_running_app()
        app.current_encounter_id = encounter_id
        app.root.current = 'combat_screen'

    def on_submit_narration(self, *args):
        pass

    def show_save_popup(self):
        pass

    def process_story_events(self, events: List[dict]):
        """
        Parses and displays a list of StoryEvents from the backend.
        """
        if not events:
            return

        for event in events:
            # 1. Display the narrative text in the log
            if event.get("narrative_text"):
                self.update_log(f"[Event] {event['narrative_text']}")

            # 2. Handle specific consequences (Visual feedback)
            c_type = event.get("consequence_type")
            payload = event.get("payload", {})

            if c_type == "WORLD_STATE_CHANGE":
                if "reputation_mod" in payload:
                    mod = payload["reputation_mod"]
                    sign = "+" if mod > 0 else ""
                    self.update_log(f">> Reputation {sign}{mod}")
                if "global_morale_debuff" in payload:
                    self.update_log(f">> Kingdom Morale Decreased!")

            elif c_type == "SPAWN_NPC":
                npc_id = payload.get("npc_template_id")
                self.update_log(f">> A {npc_id} appears!")
                # In a real implementation, we would trigger a map refresh here
                # self.refresh_map() 

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
        self.update_narration("The DM is thinking...")

        def background_task():
            return story_api.handle_narrative_prompt(actor_id, prompt_text)

        def on_complete(response):
            # Display the main AI response
            self.update_narration(response.get("message", "An error occurred."))
            
            # Process any side-effects/events included in the response
            if "events" in response:
                self.process_story_events(response["events"])

        def on_fail(error):
            logging.exception(f"Error handling narrative prompt: {error}")
            self.update_narration(f"Error: {error}")

        self.run_async(background_task, on_complete, on_fail)

    def on_rest(self):
        """Called when the 'Rest' button is pressed."""
        if not self.active_character_context or not story_api:
            self.update_log("Cannot rest right now.")
            return
        
        char_id = self.active_character_context.id
        rest_request = camp_schemas.CampRestRequest(char_id=char_id, duration=8) # Rest for 8 hours
        self.update_log("You rest for 8 hours...")

        def background_task():
            return story_api.rest_at_camp(rest_request)

        def on_complete(updated_context_dict):
            try:
                new_context = CharacterContextResponse(**updated_context_dict)
                for i, ctx in enumerate(self.party_contexts):
                    if ctx.id == char_id:
                        self.party_contexts[i] = new_context
                        break
                self.active_character_context = new_context
                self.party_list = list(self.party_contexts)
                self.update_log("You feel refreshed. HP and Composure restored.")
            except Exception as e:
                logging.exception(f"Error updating UI after rest: {e}")

        def on_fail(error):
            logging.exception(f"Error during rest: {error}")
            self.update_log(f"Rest failed: {error}")

        self.run_async(background_task, on_complete, on_fail)

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
                App.get_running_app().show_error("Success", "Game Saved Successfully")
            else:
                error_msg = result.get('error', 'Unknown error')
                self.update_log(f"Save failed: {error_msg}")
                App.get_running_app().show_error("Save Failed", error_msg)
        except Exception as e:
            logging.exception(f"Error calling save_game: {e}")
            self.update_log(f"Save failed: {e}")
            App.get_running_app().show_error("Save Error", str(e))
        self.save_popup.dismiss()

    def show_debug_popup(self):
        """Shows the debug menu."""
        if not debug_utils:
            logging.error("Debug utils not loaded.")
            return

        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        
        btn_teleport = Button(text='Teleport to Construct')
        btn_teleport.bind(on_release=lambda x: debug_utils.teleport_to_construct(App.get_running_app()))
        content.add_widget(btn_teleport)
        
        btn_spawn_dummy = Button(text='Spawn Dummy')
        btn_spawn_dummy.bind(on_release=lambda x: debug_utils.spawn_npc(App.get_running_app(), "training_dummy"))
        content.add_widget(btn_spawn_dummy)

        btn_spawn_goblin = Button(text='Spawn Goblin')
        btn_spawn_goblin.bind(on_release=lambda x: debug_utils.spawn_npc(App.get_running_app(), "live_goblin"))
        content.add_widget(btn_spawn_goblin)
        
        btn_items = Button(text='Grant Test Items')
        btn_items.bind(on_release=lambda x: debug_utils.grant_test_items(App.get_running_app()))
        content.add_widget(btn_items)
        
        btn_heal = Button(text='Heal Party')
        btn_heal.bind(on_release=lambda x: debug_utils.heal_party(App.get_running_app()))
        content.add_widget(btn_heal)
        
        btn_close = Button(text='Close')
        content.add_widget(btn_close)
        
        popup = Popup(title='Debug Menu', content=content, size_hint=(0.5, 0.8))
        btn_close.bind(on_release=popup.dismiss)
        popup.open()

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
