"""
Functional Combat Screen
Handles the turn-based combat loop, displays the map,
and provides player actions.
"""
import logging
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.anchorlayout import AnchorLayout
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.clock import Clock
from functools import partial
from kivy.core.window import Window
from typing import Optional

# --- Monolith Imports ---
try:
    from monolith.modules import story as story_api
    from monolith.modules.story_pkg import schemas as story_schemas
    # We need character/world services to get context
    from monolith.modules.character_pkg import crud as char_crud
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
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
    from game_client import asset_loader
except ImportError as e:
    logging.error(f"COMBAT_SCREEN: Failed to import client modules: {e}")
    MapViewWidget = None
    asset_loader = None

# Constants
TILE_SIZE = 64 # Must match MapViewWidget

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

    current_action = StringProperty(None, allownone=True) # e.g., "attack"
    selected_ability_id = StringProperty(None, allownone=True) # For abilities
    ability_menu = ObjectProperty(None, allownone=True) # For ability pop-up
    selected_item_id = StringProperty(None, allownone=True) # <-- ADD THIS
    item_menu = ObjectProperty(None, allownone=True) # <-- ADD THIS
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

        if not all([self.combat_state, story_api, char_services, world_crud, self.map_view_widget]):
            logging.error("CombatScreen missing critical modules or combat_state.")
            self.turn_order_label.text = "Error: Failed to load."
            return

        # --- 1. Load Location and Player Context ---
        try:
            loc_id = self.combat_state.get('location_id')

            player_actor_id = None
            for p in self.combat_state.get('participants', []):
                if p.get('actor_type') == 'player':
                    player_actor_id = p.get('actor_id')
                    break

            if not player_actor_id:
                raise Exception("No player found in combat participants.")

            with CharSession() as char_db:
                # actor_id is 'player_UUID'. We must split off the 'player_' prefix
                player_uuid = player_actor_id.split('_', 1)[1]
                db_char = char_crud.get_character(char_db, player_uuid)
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
        self.center_layout(None, self.width, self.height) # Center the map

        # --- 3. Start the Turn Loop ---
        self.check_turn()

    def center_layout(self, instance, width, height):
        """Centers the map_view_anchor in the screen."""
        if self.map_view_anchor:
            self.map_view_anchor.pos = (
                (self.width - self.map_view_anchor.width) / 2,
                (self.height - self.map_view_anchor.height) / 2
            )

    def check_turn(self):
        """The core combat loop. Checks whose turn it is and acts."""
        if not self.combat_state or self.combat_state.get('status') != 'active':
            return

        self.current_action = None # Reset any pending actions
        self.close_ability_menu() # <-- ADD THIS
        self.close_item_menu() # <-- ADD THIS

        turn_order = self.combat_state.get('turn_order', [])
        current_index = self.combat_state.get('current_turn_index', 0)

        # Update UI
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
            self.add_to_log(f"It's your turn, {self.player_context.name}!")
            self.build_player_actions(current_actor_id)

        elif current_actor_id.startswith("npc_"):
            self.is_player_turn = False
            self.add_to_log(f"It's {current_actor_id}'s turn...")
            self.action_bar.clear_widgets()
            self.action_bar.add_widget(Label(text=f"Waiting for {current_actor_id}..."))
            Clock.schedule_once(self.take_npc_turn, 0.5)

    def build_player_actions(self, player_id: str):
        """Populates the action bar with buttons for the player."""
        self.action_bar.clear_widgets()
        self.close_ability_menu() # Ensure all menus
        self.close_item_menu() # are closed on new turn

        # --- Attack Button ---
        attack_btn = Button(text='Attack', font_size='18sp')
        attack_btn.bind(on_release=lambda x: self.set_action_mode("attack"))

        # --- Ability Button ---
        ability_btn = Button(text='Ability', font_size='18sp')
        ability_btn.bind(on_release=self.open_ability_menu)

        # --- Item Button ---
        item_btn = Button(text='Item', font_size='18sp')
        item_btn.bind(on_release=self.open_item_menu) # <-- HOOKED UP

        # --- Wait Button ---
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
        """Handles the response from the monolith and advances the turn or ends combat."""
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
        # We need to refresh our world/character context
        self.refresh_combat_context()
        self.check_turn() # Advance to next turn

    def add_to_log(self, message: str):
        """Appends a message to the combat log."""
        logging.info(f"[CombatLog] {message}")
        self.log_text += f"\n- {message}"
        scroll_view = self.combat_log_label.parent
        if scroll_view:
            scroll_view.scroll_y = 0

    def end_combat(self, instance):
        """Called to leave the combat screen."""
        app = App.get_running_app()
        if 'combat_state' in app.game_settings:
            del app.game_settings['combat_state']
        logging.info("Leaving combat screen.")
        app.root.current = 'main_interface'

    def refresh_combat_context(self):
        """
        Reloads the location and player context to show
        changes (like new HP values, dead NPCs, etc.)
        """
        try:
            with WorldSession() as world_db:
                self.location_context = world_crud.get_location_context(
                    world_db, self.location_context.get('id')
                )

            with CharSession() as char_db:
                player_uuid = self.player_context.id
                db_char = char_crud.get_character(char_db, player_uuid)
                self.player_context = char_services.get_character_context(db_char)

            # Re-draw the scene with new data
            self.map_view_widget.build_scene(self.location_context, self.player_context)
        except Exception as e:
            logging.exception(f"Failed to refresh combat context: {e}")
            self.add_to_log("Error refreshing world state.")

    def get_target_at_coord(self, tile_x: int, tile_y: int) -> Optional[tuple[str, dict]]:
        """Finds an NPC at the clicked tile."""
        for npc in self.location_context.get('npcs', []):
            coords = npc.get('coordinates')
            if coords and coords[0] == tile_x and coords[1] == tile_y:
                # Check if NPC is alive
                if npc.get('current_hp', 0) > 0:
                    return "npc", npc
        return None # Only care about living NPCs in combat

    # --- NEW: Methods for the Ability Pop-up Menu ---

    def close_ability_menu(self, *args):
        """Removes the ability pop-up menu if it exists."""
        if self.ability_menu:
            # We must remove it from its parent, which is the action_bar
            self.remove_widget(self.ability_menu)
            self.ability_menu = None

    def open_ability_menu(self, *args):
        """
        Reads the player's abilities and shows a pop-up menu.
        """
        self.close_ability_menu() # Close any old menu

        abilities = self.player_context.abilities
        if not abilities:
            self.add_to_log("You have no abilities to use.")
            return

        # Create the pop-up menu
        self.ability_menu = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width='200dp',
            height=f"{len(abilities) * 44}dp",
            pos_hint={'center_x': 0.5, 'top': 2.5} # Position it above the action bar
        )

        for ability_name in abilities:
            # The ability_name is the full description, e.g., "Minor Shove: ..."
            button_text = ability_name.split(':')[0]

            btn = Button(
                text=button_text,
                size_hint_y=None,
                height='44dp'
            )
            # Bind the button to call select_ability with the *full* ability name
            btn.bind(on_release=partial(self.select_ability, ability_name))
            self.ability_menu.add_widget(btn)

        # Add the menu to the main screen layout, *not* the action bar
        self.add_widget(self.ability_menu)

    def select_ability(self, ability_id: str, *args):
        """
        Called when an ability is chosen from the menu.
        Sets targeting mode.
        """
        self.close_ability_menu()
        self.selected_ability_id = ability_id # Store the chosen ability
        self.set_action_mode("use_ability") # Set targeting mode

    # --- Add these new methods for the Item Menu ---

    def close_item_menu(self, *args):
        """Removes the item pop-up menu if it exists."""
        if self.item_menu:
            # We must remove it from its parent (the main layout)
            self.remove_widget(self.item_menu)
            self.item_menu = None

    def open_item_menu(self, *args):
        """
        Reads the player's inventory and shows a pop-up menu.
        """
        self.close_ability_menu() # Close other menus
        self.close_item_menu() # Close self

        # inventory is a dict: {"item_id": quantity}
        inventory = self.player_context.inventory
        if not inventory:
            self.add_to_log("Your inventory is empty.")
            return

        # Create the pop-up menu
        self.item_menu = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width='200dp',
            height=f"{len(inventory) * 44}dp",
            pos_hint={'center_x': 0.5, 'top': 2.5} # Position it above the action bar
        )

        for item_id, quantity in inventory.items():
            button_text = f"{item_id.replace('_', ' ').title()} (x{quantity})"

            btn = Button(
                text=button_text,
                size_hint_y=None,
                height='44dp'
            )
            # Bind the button to call select_item
            btn.bind(on_release=partial(self.select_item, item_id))
            self.item_menu.add_widget(btn)

        self.add_widget(self.item_menu)

    def select_item(self, item_id: str, *args):
        """
        Called when an item is chosen from the menu.
        Sets targeting mode.
        """
        self.close_item_menu()

        # TODO: Check if item is usable in combat
        # For now, all items are usable

        self.selected_item_id = item_id # Store the chosen item
        self.set_action_mode("use_item") # Set targeting mode

    def on_touch_down(self, touch):
        """Handle mouse clicks for targeting."""

        # If a menu is open, a click outside it should close it.
        if self.ability_menu:
            if not self.ability_menu.collide_point(*touch.pos):
                self.close_ability_menu()
            return True # Consume the touch

        if self.item_menu:
            if not self.item_menu.collide_point(*touch.pos):
                self.close_item_menu()
            return True # Consume the touch

        # We only care about clicks if it's the player's turn
        # and they are in a targeting mode
        if not self.is_player_turn or not self.current_action:
            return super().on_touch_down(touch)

        # Check if click is on the map
        if not self.map_view_widget or not self.map_view_widget.collide_point(*touch.pos):
            self.add_to_log("Targeting cancelled. Click an action.")
            self.current_action = None
            self.selected_ability_id = None
            self.selected_item_id = None # <-- ADD THIS
            return super().on_touch_down(touch)

        # --- Click is on the map and player is targeting ---
        local_pos = self.map_view_widget.to_local(*touch.pos)
        tile_x = int(local_pos[0] // TILE_SIZE)

        map_height = len(self.location_context.get('generated_map_data', []))
        if map_height == 0: return True

        tile_y = (map_height - 1) - int(local_pos[1] // TILE_SIZE)

        target = self.get_target_at_coord(tile_x, tile_y)

        # TODO: Allow targeting self or allies for healing items

        if target:
            target_type, target_data = target
            if target_type == "npc":
                target_id = f"npc_{target_data.get('id')}"
                action_name = self.current_action
                ability_id = self.selected_ability_id if action_name == "use_ability" else None
                item_id = self.selected_item_id if action_name == "use_item" else None

                self.add_to_log(f"You target {target_id} with {action_name}!")

                # Create the action request
                action = story_schemas.PlayerActionRequest(
                    action=action_name,
                    target_id=target_id,
                    ability_id=ability_id,
                    item_id=item_id # <-- Pass the selected item
                )

                # Send it to the monolith
                self.handle_player_action(self.player_context.id, action)

                # Clear targeting mode
                self.current_action = None
                self.selected_ability_id = None
                self.selected_item_id = None
        else:
            self.add_to_log("You must target an enemy.")
            self.current_action = None # Cancel targeting
            self.selected_ability_id = None
            self.selected_item_id = None

        return True # Consumed the touch
