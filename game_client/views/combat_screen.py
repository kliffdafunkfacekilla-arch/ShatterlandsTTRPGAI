"""
Functional Combat Screen
Handles the turn-based combat loop, displays the map,
and provides player actions.
"""
import logging
from kivy.app import App
# ... (all kivy imports) ...
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, ListProperty, StringProperty
from typing import Optional, List
# --- Monolith Imports ---
try:
    from monolith.modules import story as story_api
    from monolith.modules.story_pkg import schemas as story_schemas
    from monolith.modules.character_pkg import crud as char_crud
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
    from monolith.modules.world_pkg import crud as world_crud
    from monolith.modules.world_pkg.database import SessionLocal as WorldSession
    from monolith.modules.character_pkg.schemas import CharacterContextResponse
except ImportError as e:
    logging.error(f"COMBAT_SCREEN: Failed to import monolith modules: {e}")
    # ... (all set to None)
    CharacterContextResponse = None
    story_api, story_schemas = None, None
    char_crud, char_services, CharSession = None, None, None
    world_crud, WorldSession = None, None


# --- Client Imports ---
try:
    from game_client.views.map_view_widget import MapViewWidget
    from game_client import asset_loader
except ImportError as e:
    logging.error(f"COMBAT_SCREEN: Failed to import client modules: {e}")
    MapViewWidget = None
    asset_loader = None

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.anchorlayout import AnchorLayout
from kivy.clock import Clock
from functools import partial
from kivy.core.window import Window


# Constants
TILE_SIZE = 64 # Must match MapViewWidget

class CombatScreen(Screen):
    # ... (UI References) ...
    turn_order_label = ObjectProperty(None)
    combat_log_label = ObjectProperty(None)
    action_bar = ObjectProperty(None)
    map_view_anchor = ObjectProperty(None)
    map_view_widget = ObjectProperty(None)

    # --- State ---
    combat_state = ObjectProperty(None)
    location_context = ObjectProperty(None)

    # --- MODIFIED: Party-based state ---
    party_contexts_list = ListProperty([])
    active_combat_character = ObjectProperty(None, allownone=True) # The char whose turn it is
    # player_context is no longer used

    log_text = StringProperty("Combat started.\n")
    # ... (rest of state properties) ...
    current_action = StringProperty(None, allownone=True)
    selected_ability_id = StringProperty(None, allownone=True)
    ability_menu = ObjectProperty(None, allownone=True)
    selected_item_id = StringProperty(None, allownone=True)
    item_menu = ObjectProperty(None, allownone=True)
    is_player_turn = ObjectProperty(False)


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
            padding='5dp'
        )
        # Make the label auto-resize with text
        self.combat_log_label.bind(
            width=lambda *x: self.combat_log_label.setter('text_size')(self, (self.combat_log_label.width, None)),
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
        Window.bind(on_resize=self.center_layout)

    def on_enter(self, *args):
        """Called when the screen is shown. Starts the combat loop."""
        app = App.get_running_app()
        self.combat_state = app.game_settings.get('combat_state')
        self.log_text = "Combat started.\n" # Clear log
        self.current_action = None
        self.is_player_turn = False
        self.active_combat_character = None

        if not all([self.combat_state, story_api, char_services, world_crud, self.map_view_widget]):
            logging.error("CombatScreen missing critical modules or combat_state.")
            self.turn_order_label.text = "Error: Failed to load."
            return

        # --- 1. Load Location and FULL PARTY Context ---
        try:
            loc_id = self.combat_state.get('location_id')

            # --- MODIFIED: Get party from main screen ---
            main_screen = app.root.get_screen('main_interface')
            self.party_contexts_list = main_screen.party_contexts
            if not self.party_contexts_list:
                raise Exception("No party contexts found in main interface.")
            # --- END MODIFIED ---

            with WorldSession() as world_db:
                self.location_context = world_crud.get_location_context(world_db, loc_id)

        except Exception as e:
            logging.exception(f"Failed to load context for combat scene: {e}")
            self.add_to_log(f"Error loading combat: {e}")
            return

        # --- 2. Build the Scene (pass full party) ---
        self.map_view_widget.build_scene(self.location_context, self.party_contexts_list)
        self.map_view_anchor.size = self.map_view_widget.size
        self.center_layout(None, self.width, self.height) # Center the map

        # --- 3. Start the Turn Loop ---
        self.check_turn()

    def center_layout(self, instance, width, height):
        if self.map_view_anchor:
            self.map_view_anchor.pos = (
                (self.width - self.map_view_anchor.width) / 2,
                (self.height - self.map_view_anchor.height) / 2
            )

    def check_turn(self):
        """The core combat loop. Checks whose turn it is and acts."""
        if not self.combat_state or self.combat_state.get('status') != 'active':
            return

        self.current_action = None
        self.close_ability_menu()
        self.close_item_menu()
        self.active_combat_character = None # Clear active char

        turn_order = self.combat_state.get('turn_order', [])
        current_index = self.combat_state.get('current_turn_index', 0)

        # ... (UI Turn List update is unchanged) ...
        ui_turn_list = []
        for i, actor_id in enumerate(turn_order):
            if i == current_index:
                ui_turn_list.append(f"> {actor_id} <")
            else:
                ui_turn_list.append(actor_id)
        self.turn_order_label.text = "Turn Order:\n\n" + "\n".join(ui_turn_list)

        current_actor_id = turn_order[current_index]

        if current_actor_id.startswith("player_"):
            self.is_player_turn = True

            # --- MODIFIED: Find the correct active player ---
            for char_context in self.party_contexts_list:
                if char_context.id == current_actor_id:
                    self.active_combat_character = char_context
                    break

            if self.active_combat_character:
                self.add_to_log(f"It's your turn, {self.active_combat_character.name}!")
                self.build_player_actions(current_actor_id)
            else:
                logging.error(f"Error: Could not find active player {current_actor_id} in party list.")
                self.add_to_log(f"Error: Could not find player {current_actor_id}.")
                Clock.schedule_once(lambda dt: self.handle_player_action(
                    current_actor_id,
                    story_schemas.PlayerActionRequest(action="wait")
                ), 0.1)
            # --- END MODIFIED ---

        elif current_actor_id.startswith("npc_"):
            self.is_player_turn = False
            self.add_to_log(f"It's {current_actor_id}'s turn...")
            self.action_bar.clear_widgets()
            self.action_bar.add_widget(Label(text=f"Waiting for {current_actor_id}..."))
            Clock.schedule_once(self.take_npc_turn, 0.5)

    def build_player_actions(self, player_id: str):
        # ... (this method is unchanged, but open_ability_menu will now work correctly) ...
        self.action_bar.clear_widgets()
        self.close_ability_menu()
        self.close_item_menu()

        attack_btn = Button(text='Attack', font_size='18sp')
        attack_btn.bind(on_release=lambda x: self.set_action_mode("attack"))

        ability_btn = Button(text='Ability', font_size='18sp')
        ability_btn.bind(on_release=self.open_ability_menu)

        item_btn = Button(text='Item', font_size='18sp')
        item_btn.bind(on_release=self.open_item_menu)

        wait_btn = Button(text='Wait', font_size='18sp')
        wait_btn.bind(on_release=lambda x: self.handle_player_action(
            player_id,
            story_schemas.PlayerActionRequest(action="wait")
        ))

        self.action_bar.add_widget(attack_btn)
        self.action_bar.add_widget(ability_btn)
        self.action_bar.add_widget(item_btn)
        self.action_bar.add_widget(wait_btn)

    def set_action_mode(self, action_name: str):
        self.current_action = action_name
        self.add_to_log(f"Action: {action_name}. Select a target on the map.")

    def take_npc_turn(self, *args):
        if not story_api: return
        try:
            combat_id = self.combat_state.get('id')
            response_dict = story_api.handle_npc_action(combat_id)
            self.process_action_response(response_dict)
        except Exception as e:
            logging.exception(f"Failed to take NPC turn: {e}")
            self.add_to_log(f"Error: {e}")

    def handle_player_action(self, actor_id: str, action: story_schemas.PlayerActionRequest):
        if not story_api: return
        try:
            combat_id = self.combat_state.get('id')
            response_dict = story_api.handle_player_action(combat_id, actor_id, action)
            self.process_action_response(response_dict)
        except Exception as e:
            logging.exception(f"Failed to handle player action: {e}")
            self.add_to_log(f"Error: {e}")

    def process_action_response(self, response: dict):
        """Handles the response from the monolith and advances the turn or ends combat."""
        # ... (log display is unchanged) ...
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

        # --- MODIFIED: Must refresh *all* contexts ---
        self.refresh_combat_context()
        self.check_turn() # Advance to next turn

    def add_to_log(self, message: str):
        logging.info(f"[CombatLog] {message}")
        self.log_text += f"\n- {message}"
        scroll_view = self.combat_log_label.parent
        if scroll_view:
            scroll_view.scroll_y = 0

    def end_combat(self, instance):
        """Called to leave the combat screen."""
        # --- MODIFIED: Must refresh main interface contexts on exit ---
        app = App.get_running_app()
        if 'combat_state' in app.game_settings:
            del app.game_settings['combat_state']

        # Manually refresh the main interface screen's data
        main_screen = app.root.get_screen('main_interface')
        main_screen.party_contexts = self.party_contexts_list
        main_screen.active_character_context = self.party_contexts_list[0]
        main_screen.party_list = self.party_contexts_list

        logging.info("Leaving combat screen.")
        app.root.current = 'main_interface'

    def refresh_combat_context(self):
        """
        Reloads the location and ALL party member contexts to show
        changes (like new HP values, dead NPCs, etc.)
        """
        try:
            with WorldSession() as world_db:
                self.location_context = world_crud.get_location_context(
                    world_db, self.location_context.get('id')
                )

            # --- MODIFIED: Loop and reload all party members ---
            with CharSession() as char_db:
                new_contexts: List[CharacterContextResponse] = []
                for char_context in self.party_contexts_list:
                    db_char = char_crud.get_character(char_db, char_context.id)
                    if db_char:
                        new_contexts.append(char_services.get_character_context(db_char))

                self.party_contexts_list = new_contexts
                # Also update the main interface screen's list
                main_screen = App.get_running_app().root.get_screen('main_interface')
                main_screen.party_contexts = new_contexts
            # --- END MODIFIED ---

            # Re-draw the scene with new data
            self.map_view_widget.build_scene(self.location_context, self.party_contexts_list)
        except Exception as e:
            logging.exception(f"Failed to refresh combat context: {e}")
            self.add_to_log("Error refreshing world state.")

    def get_target_at_coord(self, tile_x: int, tile_y: int) -> Optional[tuple[str, dict]]:
        """Finds an NPC or Player at the clicked tile."""
        # Check NPCs
        for npc in self.location_context.get('npcs', []):
            coords = npc.get('coordinates')
            if coords and coords[0] == tile_x and coords[1] == tile_y:
                if npc.get('current_hp', 0) > 0:
                    return "npc", npc

        # Check Player (self)
        if (self.player_context and
            self.player_context.position_x == tile_x and
            self.player_context.position_y == tile_y):
            # Return the dict version of the context
            return "player", self.player_context.model_dump()

        # TODO: Check other allied players in party_list

        return None

        # Check Players (self or allies)
        for char_context in self.party_contexts_list:
            if (char_context.position_x == tile_x and
                char_context.position_y == tile_y and
                char_context.current_hp > 0):
                return "player", char_context.model_dump()

        return None

    # --- Methods for the Ability Pop-up Menu ---
    def close_ability_menu(self, *args):
        if self.ability_menu:
            self.remove_widget(self.ability_menu)
            self.ability_menu = None

    def open_ability_menu(self, *args):
        """
        Reads the *active combat character's* abilities and shows a pop-up.
        """
        self.close_ability_menu()
        if not self.active_combat_character:
             return

        abilities = self.active_combat_character.abilities
        if not abilities:
            self.add_to_log("You have no abilities.")
            return

        self.ability_menu = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width='200dp',
            height=f"{len(abilities) * 44}dp",
            pos_hint={'center_x': 0.5, 'top': 2.5}
        )

        for ability_name in abilities:
            button_text = ability_name.split(':')[0]
            btn = Button(
                text=button_text,
                size_hint_y=None,
                height='44dp'
            )
            btn.bind(on_release=partial(self.select_ability, ability_name))
            self.ability_menu.add_widget(btn)

        self.add_widget(self.ability_menu)

    def select_ability(self, ability_id: str, *args):
        self.close_ability_menu()
        self.selected_ability_id = ability_id
        self.set_action_mode("use_ability")

    # --- Methods for the Item Menu ---
    def close_item_menu(self, *args):
        if self.item_menu:
            self.remove_widget(self.item_menu)
            self.item_menu = None

    def open_item_menu(self, *args):
        """
        Reads the *active combat character's* inventory and shows a pop-up.
        """
        self.close_ability_menu()
        self.close_item_menu()
        if not self.active_combat_character:
            return

        inventory = self.active_combat_character.inventory
        if not inventory:
            self.add_to_log("Your inventory is empty.")
            return

        self.item_menu = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width='200dp',
            height=f"{len(inventory) * 44}dp",
            pos_hint={'center_x': 0.5, 'top': 2.5}
        )

        for item_id, quantity in inventory.items():
            button_text = f"{item_id.replace('_', ' ').title()} (x{quantity})"
            btn = Button(
                text=button_text,
                size_hint_y=None,
                height='44dp'
            )
            btn.bind(on_release=partial(self.select_item, item_id))
            self.item_menu.add_widget(btn)

        self.add_widget(self.item_menu)

    def select_item(self, item_id: str, *args):
        self.close_item_menu()
        self.selected_item_id = item_id
        self.set_action_mode("use_item")

    def on_touch_down(self, touch):
        """Handle mouse clicks for targeting."""

        # ... (menu closing logic is unchanged) ...
        if self.ability_menu:
            if not self.ability_menu.collide_point(*touch.pos):
                self.close_ability_menu()
            return True
        if self.item_menu:
            if not self.item_menu.collide_point(*touch.pos):
                self.close_item_menu()
            return True

        if not self.is_player_turn or not self.current_action:
            return super().on_touch_down(touch)

        if not self.map_view_widget or not self.map_view_widget.collide_point(*touch.pos):
            self.add_to_log("Targeting cancelled. Click an action.")
            self.current_action = None
            self.selected_ability_id = None
            self.selected_item_id = None
            return super().on_touch_down(touch)

        local_pos = self.map_view_widget.to_local(*touch.pos)
        tile_x = int(local_pos[0] // TILE_SIZE)

        map_height = len(self.location_context.get('generated_map_data', []))
        if map_height == 0: return True

        tile_y = (map_height - 1) - int(local_pos[1] // TILE_SIZE)

        target = self.get_target_at_coord(tile_x, tile_y)

        # --- MODIFIED: Target Validation Logic ---
        if target:
            target_type, target_data = target

            # Define what a friendly action is
            is_friendly_action = (
                self.selected_item_id == "item_health_potion_small" or
                self.selected_ability_id == "Minor Heal"
            )

            # Case 1: Hostile action on an enemy (OK)
            if target_type == "npc" and not is_friendly_action:
                target_id = f"npc_{target_data.get('id')}"

            # Case 2: Friendly action on an ally (OK)
            elif target_type == "player" and is_friendly_action:
                target_id = target_data.get('id') # Already in "player_UUID" format

            # Case 3: Hostile action on an ally (BAD)
            elif target_type == "player" and not is_friendly_action:
                self.add_to_log("You can't attack an ally!")
                self.current_action = None
                return True # Consume touch

            # Case 4: Friendly action on an enemy (BAD)
            elif target_type == "npc" and is_friendly_action:
                self.add_to_log("You can't use that on an enemy!")
                self.current_action = None
                return True # Consume touch

            else:
                self.add_to_log("Invalid target.")
                self.current_action = None
                return True

            # --- If we got here, we have a valid target_id ---
            action_name = self.current_action
            ability_id = self.selected_ability_id if action_name == "use_ability" else None
            item_id = self.selected_item_id if action_name == "use_item" else None

            self.add_to_log(f"You use {action_name} on {target_id}!")

            action = story_schemas.PlayerActionRequest(
                action=action_name,
                target_id=target_id,
                ability_id=ability_id,
                item_id=item_id
            )

            self.handle_player_action(self.player_context.id, action)

            # Clear targeting mode
            self.current_action = None
            self.selected_ability_id = None
            self.selected_item_id = None

        else:
            self.add_to_log("You must target an enemy or ally.")
            self.current_action = None # Cancel targeting
            self.selected_ability_id = None
            self.selected_item_id = None

        return True # Consumed the touch
