"""
Functional Combat Screen
Handles the turn-based combat loop, displays the map,
and provides player actions.
"""
import logging
from functools import partial # <-- ADDED

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import (BooleanProperty, ObjectProperty,
                             StringProperty)
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

# --- Monolith Imports ---
try:
    from monolith.modules import story as story_api
    from monolith.modules.character_pkg import crud as char_crud
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import \
        SessionLocal as CharSession
    from monolith.modules.story_pkg import schemas as story_schemas
    from monolith.modules.world_pkg import crud as world_crud
    from monolith.modules.world_pkg.database import SessionLocal as WorldSession
except ImportError as e:
    logging.error(f"COMBAT_SCREEN: Failed to import monolith modules: {e}")
    story_api, story_schemas = None, None
    char_services, CharSession = None, None
    world_crud, WorldSession = None, None

# --- Client Imports ---
try:
    from game_client.views.map_view_widget import MapViewWidget
except ImportError as e:
    logging.error(f"COMBAT_SCREEN: Failed to import MapViewWidget: {e}")
    MapViewWidget = None

# Constants
TILE_SIZE = 64


class CombatScreen(Screen):

    # --- UI References ---
    turn_order_label = ObjectProperty(None)
    combat_log_label = ObjectProperty(None)
    action_bar = ObjectProperty(None)
    map_view_anchor = ObjectProperty(None)
    map_view_widget = ObjectProperty(None)

    # --- State ---
    combat_state = ObjectProperty(None)
    location_context = ObjectProperty(None)
    player_context = ObjectProperty(None)
    log_text = StringProperty("Combat started.\n")

    current_action = StringProperty(None, allownone=True)
    selected_ability_id = StringProperty(None, allownone=True) # <-- ADDED
    ability_menu = ObjectProperty(None, allownone=True)      # <-- ADDED
    is_player_turn = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # --- Main Layout ---
        layout = BoxLayout(orientation='vertical', padding='20dp', spacing='10dp')
        title = Label(text='COMBAT MODE', font_size='32sp', size_hint_y=0.1)

        # --- Center Content (Map & Turn Order) ---
        center_layout = BoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=0.7)

        # Map Anchor (where the map widget goes)
        self.map_view_anchor = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_x=0.7)
        if MapViewWidget:
            self.map_view_widget = MapViewWidget()
            self.map_view_anchor.add_widget(self.map_view_widget)

        # Turn Order
        self.turn_order_label = Label(
            text='Turn Order:\n[loading...]',
            font_size='18sp',
            size_hint_x=0.3
        )

        center_layout.add_widget(self.map_view_anchor)
        center_layout.add_widget(self.turn_order_label)

        # --- Combat Log (Bottom) ---
        log_scroll = ScrollView(size_hint_y=0.2)
        self.combat_log_label = Label(
            text=self.log_text, font_size='14sp', size_hint_y=None,
            text_size=(self.width, None), padding='5dp'
        )
        self.combat_log_label.bind(
            texture_size=self.combat_log_label.setter('size'),
            text=self.setter('log_text')
        )
        log_scroll.add_widget(self.combat_log_label)

        # --- Action Bar (Very Bottom) ---
        self.action_bar = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing='10dp')

        layout.add_widget(title)
        layout.add_widget(center_layout)
        layout.add_widget(log_scroll)
        layout.add_widget(self.action_bar)

        self.add_widget(layout)

    def on_enter(self, *args):
        """Called when the screen is shown. Starts the combat loop."""
        app = App.get_running_app()
        self.combat_state = app.game_settings.get('combat_state')
        self.log_text = "Combat started.\n"
        self.current_action = None
        self.is_player_turn = False

        if not all([self.combat_state, story_api, char_services, world_crud, self.map_view_widget]):
            logging.error("CombatScreen missing critical modules or combat_state.")
            self.turn_order_label.text = "Error: Failed to load."
            return

        # --- 1. Load Location and Player Context ---
        try:
            loc_id = self.combat_state.get('location_id')
            player_id = app.game_settings.get('selected_character_name')

            player_actor_id = None
            for p in self.combat_state.get('participants', []):
                if p.get('actor_type') == 'player':
                    player_actor_id = p.get('actor_id')
                    break

            if not player_actor_id:
                raise Exception("No player found in combat participants.")

            with CharSession() as char_db:
                # This is still a bit of a hack, assuming the name is unique
                db_char = char_crud.get_character_by_name(char_db, player_id)
                self.player_context = char_services.get_character_context(db_char)

            with WorldSession() as world_db:
                self.location_context = world_crud.get_location_context(world_db, loc_id)

        except Exception as e:
            logging.exception(f"Failed to load context for combat scene: {e}")
            self.add_to_log(f"Error loading combat: {e}")
            return

        # --- 2. Build the Scene ---
        self.map_view_widget.build_scene(self.location_context, self.player_context)
        self.map_view_anchor.size = self.map_view_widget.size
        self.center_layout(None, self.width, self.height)

        # --- 3. Start the Turn Loop ---
        self.check_turn()

    def center_layout(self, instance, width, height):
        """Centers the map_view_anchor in the screen."""
        if self.map_view_anchor:
            self.map_view_anchor.pos = (
                (width - self.map_view_anchor.width) / 2,
                (self.height - self.map_view_anchor.height) / 2  # Use self.height
            )

    def check_turn(self):
        """The core combat loop. Checks whose turn it is and acts."""
        if not self.combat_state or self.combat_state.get('status') != 'active':
            return

        self.current_action = None

        turn_order = self.combat_state.get('turn_order', [])
        current_index = self.combat_state.get('current_turn_index', 0)

        ui_turn_list = [f"> {actor_id} <" if i == current_index else actor_id for i, actor_id in enumerate(turn_order)]
        self.turn_order_label.text = "Turn Order:\n\n" + "\n".join(ui_turn_list)

        current_actor_id = turn_order[current_index]

        if current_actor_id.startswith("player_"):
            self.is_player_turn = True
            self.add_to_log(f"It's your turn, {self.player_context.name}!")
            self.build_player_actions(current_actor_id)
        elif current_actor_id.startswith("npc_"):
            self.is_player_turn = False
            self.add_to_log(f"It's {current_actor_id}'s turn...")
            self.action_bar.clear_widgets()
            self.action_bar.add_widget(Label(text=f"Waiting for {current_actor_id}..."))
            Clock.schedule_once(self.take_npc_turn, 0.5)

    # --- NEW METHODS for Ability Menu ---
    def close_ability_menu(self, *args):
        """Removes the ability pop-up menu if it exists."""
        if self.ability_menu:
            self.remove_widget(self.ability_menu) # The menu is added to the screen
            self.ability_menu = None

    def open_ability_menu(self, *args):
        """Reads the player's abilities and shows a pop-up menu."""
        self.close_ability_menu()

        abilities = self.player_context.abilities
        if not abilities:
            self.add_to_log("You have no abilities to use.")
            return

        self.ability_menu = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width='200dp',
            pos_hint={'center_x': 0.5, 'y': self.action_bar.height / self.height }
        )
        self.ability_menu.height = len(abilities) * 44

        for ability_name in abilities:
            button_text = ability_name.split(':')[0]
            btn = Button(text=button_text, size_hint_y=None, height='44dp')
            btn.bind(on_release=partial(self.select_ability, ability_name))
            self.ability_menu.add_widget(btn)

        self.add_widget(self.ability_menu)

    def select_ability(self, ability_id: str, *args):
        """Called when an ability is chosen. Sets targeting mode."""
        self.close_ability_menu()
        self.selected_ability_id = ability_id
        self.set_action_mode("use_ability")

    # --- UPDATED Method ---
    def build_player_actions(self, player_id: str):
        """Populates the action bar with buttons for the player."""
        self.action_bar.clear_widgets()
        self.close_ability_menu()

        attack_btn = Button(text='Attack', font_size='18sp')
        attack_btn.bind(on_release=lambda x: self.set_action_mode("attack"))

        ability_btn = Button(text='Ability', font_size='18sp')
        ability_btn.bind(on_release=self.open_ability_menu) # <-- CHANGED

        wait_btn = Button(text='Wait', font_size='18sp')
        wait_btn.bind(on_release=lambda x: self.handle_player_action(
            player_id, story_schemas.PlayerActionRequest(action="wait")
        ))

        self.action_bar.add_widget(attack_btn)
        self.action_bar.add_widget(ability_btn)
        self.action_bar.add_widget(Button(text='Item (TBD)'))
        self.action_bar.add_widget(wait_btn)

    def set_action_mode(self, action_name: str):
        """Sets the client to wait for a target."""
        self.current_action = action_name
        self.add_to_log(f"Action: {action_name}. Select a target on the map.")

    def take_npc_turn(self, *args):
        """Calls the monolith to process an NPC's turn."""
        if not story_api: return
        try:
            combat_id = self.combat_state.get('id')
            response_dict = story_api.handle_npc_action(combat_id)
            self.process_action_response(response_dict)
        except Exception as e:
            logging.exception(f"Failed to take NPC turn: {e}")
            self.add_to_log(f"Error: {e}")

    def handle_player_action(self, actor_id: str, action: story_schemas.PlayerActionRequest):
        """Calls the monolith to process the player's chosen action."""
        if not story_api: return
        try:
            combat_id = self.combat_state.get('id')
            response_dict = story_api.handle_player_action(combat_id, actor_id, action)
            self.process_action_response(response_dict)
        except Exception as e:
            logging.exception(f"Failed to handle player action: {e}")
            self.add_to_log(f"Error: {e}")

    def process_action_response(self, response: dict):
        """Handles the response from the monolith and advances the turn."""
        for log_entry in response.get('log', []):
            self.add_to_log(log_entry)

        if response.get('combat_over', False):
            self.add_to_log("Combat has ended!")
            self.action_bar.clear_widgets()
            exit_btn = Button(text='Return to Exploration')
            exit_btn.bind(on_release=self.end_combat)
            self.action_bar.add_widget(exit_btn)
            return

        self.combat_state['current_turn_index'] = response.get('new_turn_index')
        self.refresh_combat_context()
        self.check_turn()

    def add_to_log(self, message: str):
        """Appends a message to the combat log."""
        logging.info(f"[CombatLog] {message}")
        self.log_text += f"\n- {message}"
        if self.combat_log_label and self.combat_log_label.parent:
            self.combat_log_label.parent.scroll_y = 0

    def end_combat(self, instance):
        """Called to leave the combat screen."""
        app = App.get_running_app()
        if 'combat_state' in app.game_settings:
            del app.game_settings['combat_state']
        logging.info("Leaving combat screen.")
        app.root.current = 'main_interface'

    def refresh_combat_context(self):
        """Reloads location and player context."""
        try:
            with WorldSession() as world_db:
                self.location_context = world_crud.get_location_context(
                    world_db, self.location_context.get('id')
                )
            with CharSession() as char_db:
                # Use the full player_id from the context
                char_uuid = self.player_context.id.split('_')[1]
                db_char = char_crud.get_character(char_db, char_uuid)
                self.player_context = char_services.get_character_context(db_char)

            self.map_view_widget.build_scene(self.location_context, self.player_context)
        except Exception as e:
            logging.exception(f"Failed to refresh combat context: {e}")
            self.add_to_log("Error refreshing world state.")

    def get_target_at_coord(self, tile_x: int, tile_y: int):
        """Finds an NPC at the clicked tile."""
        for npc in self.location_context.get('npcs', []):
            coords = npc.get('coordinates')
            if coords and coords[0] == tile_x and coords[1] == tile_y:
                return "npc", npc
        return None

    # --- MAJORLY UPDATED Method ---
    def on_touch_down(self, touch):
        """Handle mouse clicks for targeting or closing menus."""
        if self.ability_menu:
            if not self.ability_menu.collide_point(*touch.pos):
                self.close_ability_menu()
                return True

        if not self.is_player_turn or not self.current_action:
            return super().on_touch_down(touch)

        if not self.map_view_widget or not self.map_view_widget.collide_point(*touch.pos):
            self.add_to_log("Targeting cancelled.")
            self.current_action = None
            self.selected_ability_id = None
            return super().on_touch_down(touch)

        local_pos = self.map_view_widget.to_local(*touch.pos)
        tile_x = int(local_pos[0] // TILE_SIZE)
        map_height = len(self.location_context.get('generated_map_data', []))
        if map_height == 0: return True
        tile_y = (map_height - 1) - int(local_pos[1] // TILE_SIZE)

        target = self.get_target_at_coord(tile_x, tile_y)

        if target:
            target_type, target_data = target
            if target_type == "npc":
                target_id = f"npc_{target_data.get('id')}"
                action_name = self.current_action
                ability_id = self.selected_ability_id if action_name == "use_ability" else None

                self.add_to_log(f"You target {target_id} with {action_name}!")

                action = story_schemas.PlayerActionRequest(
                    action=action_name,
                    target_id=target_id,
                    ability_id=ability_id
                )
                self.handle_player_action(self.player_context.id, action)

                self.current_action = None
                self.selected_ability_id = None
        else:
            self.add_to_log("You must target an enemy.")
            self.current_action = None
            self.selected_ability_id = None

        return True
