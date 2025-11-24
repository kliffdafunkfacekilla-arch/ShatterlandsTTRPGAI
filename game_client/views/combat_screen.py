"""
Functional Combat Screen
Handles the turn-based combat loop, displays the map,
and provides player actions with AI-Optimized Flavor Text.
"""
import logging
import random
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, ListProperty, StringProperty
from typing import Optional, List


# --- Monolith Imports ---
try:
    from monolith.modules import story as story_api
    from monolith.modules import rules as rules_api
    from monolith.modules.story_pkg import schemas as story_schemas
    from monolith.modules.character_pkg import crud as char_crud
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
    from monolith.modules.world_pkg import crud as world_crud
    from monolith.modules.world_pkg.database import SessionLocal as WorldSession
    from monolith.modules.character_pkg.schemas import CharacterContextResponse
except ImportError as e:
    logging.error(f"COMBAT_SCREEN: Failed to import monolith modules: {e}")
    CharacterContextResponse = None
    story_api, story_schemas = None, None
    char_crud, char_services, CharSession = None, None, None
    rules_api = None
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
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from functools import partial
from kivy.core.window import Window

# Constants
TILE_SIZE = 64 

class CombatScreen(Screen):
    # --- UI References ---
    turn_order_label = ObjectProperty(None)
    combat_log_label = ObjectProperty(None)
    action_bar = ObjectProperty(None)
    map_view_anchor = ObjectProperty(None)
    map_view_widget = ObjectProperty(None)
    narrative_label = ObjectProperty(None) # For AI Narration

    # --- State ---
    combat_state = ObjectProperty(None)
    location_context = ObjectProperty(None)

    # --- Party-based state ---
    party_contexts_list = ListProperty([])
    active_combat_character = ObjectProperty(None, allownone=True) 

    log_text = StringProperty("Combat started.\n")
    current_action = StringProperty(None, allownone=True)
    selected_ability_id = StringProperty(None, allownone=True)
    ability_menu = ObjectProperty(None, allownone=True)
    selected_item_id = StringProperty(None, allownone=True)
    item_menu = ObjectProperty(None, allownone=True)
    is_player_turn = ObjectProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # --- Main Layout ---
        layout = BoxLayout(orientation='vertical', padding='10dp', spacing='5dp')
        
        # 1. Narrative Box (Replacing simple title)
        self.narrative_label = Label(
            text="The battle begins...", 
            font_size='16sp', 
            italic=True,
            size_hint_y=0.15,
            text_size=(Window.width - 40, None),
            halign='center',
            valign='middle',
            color=(0.9, 0.9, 1, 1)
        )
        self.narrative_label.bind(size=self._update_text_size)

        # 2. Center Content (Map & Turn Order)
        center_layout = BoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=0.65)

        self.map_view_anchor = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_x=0.7)
        if MapViewWidget:
            self.map_view_widget = MapViewWidget()
            self.map_view_anchor.add_widget(self.map_view_widget)

        self.turn_order_label = Label(
            text='Turn Order:\n[loading...]',
            font_size='14sp',
            size_hint_x=0.3
        )

        center_layout.add_widget(self.map_view_anchor)
        center_layout.add_widget(self.turn_order_label)

        # 3. Combat Log
        log_scroll = ScrollView(size_hint_y=0.1)
        self.combat_log_label = Label(
            text=self.log_text, font_size='12sp', size_hint_y=None,
            padding='5dp'
        )
        self.combat_log_label.bind(
            width=lambda *x: self.combat_log_label.setter('text_size')(self, (self.combat_log_label.width, None)),
            texture_size=self.combat_log_label.setter('size'),
            text=self.setter('log_text')
        )
        log_scroll.add_widget(self.combat_log_label)

        # 4. Action Bar
        self.action_bar = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing='10dp')

        layout.add_widget(self.narrative_label)
        layout.add_widget(center_layout)
        layout.add_widget(log_scroll)
        layout.add_widget(self.action_bar)

        self.add_widget(layout)
        Window.bind(on_resize=self.center_layout)
        
    def center_layout(self, *args):
        # Kivy's window binding expects this method to exist.
        # Add widget positioning logic here later.
        pass

    def _update_text_size(self, instance, value):
        instance.text_size = (instance.width - 20, None)

    def on_enter(self, *args):
        """Called when the screen is shown. Starts the combat loop."""
        app = App.get_running_app()
        try:
            main_screen = app.root.get_screen('main_interface')
            # Ensure we have party contexts
            if not main_screen.party_contexts:
                 logging.error("No party contexts found to start combat.")
                 app.root.current = 'main_interface'
                 return

            player_ids = [p.id for p in main_screen.party_contexts]
            npc_ids = app.game_settings.get('pending_combat_npcs', ['goblin_scout'])
            loc_id = main_screen.active_character_context.current_location_id

            start_req = story_schemas.CombatStartRequest(
                location_id=loc_id,
                player_ids=player_ids,
                npc_template_ids=npc_ids
            )
            self.combat_state = story_api.start_combat(start_req)
            app.game_settings['combat_state'] = self.combat_state 

        except Exception as e:
            logging.exception(f"Failed to start combat: {e}")
            self.add_to_log(f"Error starting combat: {e}")
            app.root.current = 'main_interface'
            return

        self.log_text = "Combat started.\n"
        self.current_action = None
        self.is_player_turn = False
        self.active_combat_character = None
        self.party_contexts_list.clear()

        if not all([self.combat_state, story_api, char_services, world_crud, self.map_view_widget, rules_api, char_crud]):
            logging.error("CombatScreen missing critical modules or combat_state.")
            self.turn_order_label.text = "Error: Failed to load."
            return

        # Load Contexts
        try:
            loc_id = self.combat_state.get('location_id')
            main_screen = app.root.get_screen('main_interface')

            with CharSession() as char_db:
                for char_ctx in main_screen.party_contexts:
                    char_uuid = char_ctx.id.split('_')[-1]
                    db_char = char_crud.get_character(char_db, char_uuid)
                    if db_char:
                        self.party_contexts_list.append(char_services.get_character_context(db_char))

            with WorldSession() as world_db:
                self.location_context = world_crud.get_location_context(world_db, loc_id)
                # Try to set initial narrative description from map context
                if self.location_context:
                    # If 'flavor_context' was saved in ai_annotations or map data
                    flavor = self.location_context.get('ai_annotations', {}).get('flavor_context')
                    if flavor and 'environment_description' in flavor:
                        self.narrative_label.text = flavor['environment_description']

        except Exception as e:
            logging.exception(f"Failed to load context for combat scene: {e}")
            self.add_to_log(f"Error loading combat: {e}")
            return

        self.map_view_widget.build_scene(self.location_context, self.party_contexts_list)
        self.map_view_anchor.size = self.map_view_widget.size
        self.center_layout(None, self.width, self.height)

        self.check_turn()

    def center_layout(self, instance, width, height):
        if self.map_view_anchor:
            self.map_view_anchor.pos = (
                (self.width - self.map_view_anchor.width) / 2,
                (self.height - self.map_view_anchor.height) / 2
            )

    def check_turn(self):
        """The core combat loop."""
        if not self.combat_state or self.combat_state.get('status') != 'active':
            return

        self.current_action = None
        self.close_ability_menu()
        self.close_item_menu()
        self.active_combat_character = None

        turn_order = self.combat_state.get('turn_order', [])
        current_index = self.combat_state.get('current_turn_index', 0)

        ui_turn_list = []
        current_actor_id = turn_order[current_index]

        for i, actor_id in enumerate(turn_order):
            actor_name = actor_id
            if actor_id.startswith("player_"):
                for p in self.party_contexts_list:
                    if p.id == actor_id:
                        actor_name = p.name
                        break
            elif actor_id.startswith("npc_"):
                for n in self.location_context.get('npcs', []):
                    if f"npc_{n.get('id')}" == actor_id:
                        actor_name = n.get('template_id', actor_id).replace("_", " ").title()
                        break

            if i == current_index:
                ui_turn_list.append(f"> {actor_name} <")
            else:
                ui_turn_list.append(actor_name)

        self.turn_order_label.text = "Turn Order:\n\n" + "\n".join(ui_turn_list)

        if current_actor_id.startswith("player_"):
            self.is_player_turn = True
            for char_context in self.party_contexts_list:
                if char_context.id == current_actor_id:
                    self.active_combat_character = char_context
                    break

            if self.active_combat_character:
                self.add_to_log(f"It's your turn, {self.active_combat_character.name}!")
                self.build_player_actions(current_actor_id)
            else:
                logging.error(f"Error: Could not find active player {current_actor_id}")
                Clock.schedule_once(lambda dt: self.handle_player_action(
                    current_actor_id,
                    story_schemas.PlayerActionRequest(action="wait")
                ), 0.1)

        elif current_actor_id.startswith("npc_"):
            self.is_player_turn = False
            self.add_to_log(f"It's {actor_name}'s turn...")
            self.action_bar.clear_widgets()
            self.action_bar.add_widget(Label(text=f"Waiting for {actor_name}..."))
            Clock.schedule_once(self.take_npc_turn, 0.5)

    def build_player_actions(self, player_id: str):
        self.action_bar.clear_widgets()
        self.close_ability_menu()
        self.close_item_menu()

        attack_btn = Button(text='Attack', font_size='18sp')
        attack_btn.bind(on_release=lambda x: self.set_action_mode("attack"))

        move_btn = Button(text='Move', font_size='18sp')
        move_btn.bind(on_release=lambda x: self.set_action_mode("move"))

        ability_btn = Button(text='Ability', font_size='18sp')
        ability_btn.bind(on_release=self.open_ability_menu)

        item_btn = Button(text='Item', font_size='18sp')
        item_btn.bind(on_release=self.open_item_menu)

        ready_btn = Button(text='Ready', font_size='18sp')
        ready_btn.bind(on_release=lambda x: self.handle_player_action(
            player_id,
            story_schemas.PlayerActionRequest(action="ready")
        ))

        wait_btn = Button(text='Wait', font_size='18sp')
        wait_btn.bind(on_release=lambda x: self.handle_player_action(
            player_id,
            story_schemas.PlayerActionRequest(action="wait")
        ))

        self.action_bar.add_widget(attack_btn)
        self.action_bar.add_widget(move_btn)
        self.action_bar.add_widget(ability_btn)
        self.action_bar.add_widget(item_btn)
        self.action_bar.add_widget(ready_btn)
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
            self.combat_state['current_turn_index'] = (self.combat_state['current_turn_index'] + 1) % len(self.combat_state['turn_order'])
            self.check_turn()

    def handle_player_action(self, actor_id: str, action: "story_schemas.PlayerActionRequest"):
        if not story_api: return
        try:
            combat_id = self.combat_state.get('id')
            response_dict = story_api.handle_player_action(combat_id, actor_id, action)
            self.process_action_response(response_dict)
        except Exception as e:
            logging.exception(f"Failed to handle player action: {e}")
            self.add_to_log(f"Error: {e}")

    # --- NEW: Flavor Text Optimization ---
    def get_flavor_text(self, action_type: str) -> str:
        """
        Returns instant flavor text from the pre-baked MapFlavorContext.
        action_type options: 'hit', 'miss', 'spell', 'enemy_intro'
        """
        # 1. Try to get flavor context from location data
        flavor = None
        if self.location_context and self.location_context.get('flavor_context'):
             # If flavor_context is a dict (from JSON) or object
             flavor = self.location_context.get('flavor_context')
        elif self.location_context and self.location_context.get('ai_annotations'):
             flavor = self.location_context.get('ai_annotations', {}).get('flavor_context')

        if not flavor:
            return "" # Fallback to nothing if no flavor

        # 2. Pick a random string from the correct list
        # Handle flavor being either a dict or Pydantic model
        options = []
        if isinstance(flavor, dict):
            if action_type == "hit": options = flavor.get('combat_hits', [])
            elif action_type == "miss": options = flavor.get('combat_misses', [])
            elif action_type == "spell": options = flavor.get('spell_casts', [])
            elif action_type == "enemy_intro": options = flavor.get('enemy_intros', [])
        else: # Pydantic model
            if action_type == "hit": options = flavor.combat_hits
            elif action_type == "miss": options = flavor.combat_misses
            elif action_type == "spell": options = flavor.spell_casts
            elif action_type == "enemy_intro": options = flavor.enemy_intros

        if options:
            return random.choice(options)
        return ""

    def process_action_response(self, response: dict):
        # 1. Log Update
        recent_logs = []
        hit_occurred = False
        miss_occurred = False

        for log_entry in response.get('log', []):
            self.add_to_log(log_entry)
            recent_logs.append(log_entry)
            # Simple heuristic to detect hit/miss for flavor
            if "hits" in log_entry.lower(): hit_occurred = True
            if "misses" in log_entry.lower(): miss_occurred = True

        # --- NEW: CHECK FOR REACTION ---
        reaction_opp = response.get("reaction_opportunity")
        if reaction_opp:
            self.show_reaction_popup(reaction_opp)
            return
        # -------------------------------

        # 2. Instant Flavor Update (Optimization)
        flavor_text = ""
        if hit_occurred:
             flavor_text = self.get_flavor_text("hit")
        elif miss_occurred:
             flavor_text = self.get_flavor_text("miss")

        if flavor_text:
            self.narrative_label.text = flavor_text

        # 3. Background AI Narration (Optional - can be disabled if flavor text is enough)
        # Only trigger if no instant flavor was found, or randomly to add variety
        elif recent_logs and random.random() > 0.7:
            try:
                from monolith.modules import ai_dm as ai_dm_api
                if ai_dm_api:
                     Clock.schedule_once(lambda dt: self.update_narrative(recent_logs, ai_dm_api), 0.1)
            except ImportError:
                pass

        if response.get('combat_over', False):
            self.narrative_label.text = "Silence falls as the battle ends..."
            self.add_to_log("Combat has ended!")
            self.action_bar.clear_widgets()
            exit_btn = Button(text='Return to Exploration')
            exit_btn.bind(on_release=self.end_combat)
            self.action_bar.add_widget(exit_btn)
            return
        # Auto scroll logic would go here

    def end_combat(self, instance):
        app = App.get_running_app()
        if 'combat_state' in app.game_settings:
            del app.game_settings['combat_state']

        # Refresh main screen state
        main_screen = app.root.get_screen('main_interface')
        if main_screen and self.party_contexts_list:
            main_screen.party_contexts = self.party_contexts_list
            main_screen.active_character_context = self.party_contexts_list[0]
            main_screen.party_list = self.party_contexts_list

        logging.info("Leaving combat screen.")
        app.root.current = 'main_interface'

    def refresh_combat_context(self):
        try:
            with WorldSession() as world_db:
                self.location_context = world_crud.get_location_context(
                    world_db, self.location_context.get('id')
                )

            with CharSession() as char_db:
                new_contexts = []
                for char_context in self.party_contexts_list:
                    char_uuid = char_context.id.split('_')[-1]
                    db_char = char_crud.get_character(char_db, char_uuid)
                    if db_char:
                        new_contexts.append(char_services.get_character_context(db_char))

                self.party_contexts_list = new_contexts
                main_screen = App.get_running_app().root.get_screen('main_interface')
                main_screen.party_contexts = new_contexts

            self.map_view_widget.build_scene(self.location_context, self.party_contexts_list)
        except Exception as e:
            logging.exception(f"Failed to refresh combat context: {e}")

    def get_target_at_coord(self, tile_x: int, tile_y: int) -> Optional[tuple[str, dict]]:
        for npc in self.location_context.get('npcs', []):
            coords = npc.get('coordinates')
            if coords and coords[0] == tile_x and coords[1] == tile_y:
                if npc.get('current_hp', 0) > 0:
                    return "npc", npc

        for char_context in self.party_contexts_list:
            if (
                char_context.position_x == tile_x and
                char_context.position_y == tile_y and
                char_context.current_hp > 0
            ):
                return "player", char_context.model_dump()
        return None

    def close_ability_menu(self, *args):
        if self.ability_menu:
            self.remove_widget(self.ability_menu)
            self.ability_menu = None

    def open_ability_menu(self, *args):
        self.close_ability_menu()
        if not self.active_combat_character: return

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
            # Simple button for now
            btn = Button(text=ability_name, size_hint_y=None, height='44dp')
            btn.bind(on_release=partial(self.select_ability, ability_name))
            self.ability_menu.add_widget(btn)

        self.add_widget(self.ability_menu)

    def select_ability(self, ability_id: str, *args):
        self.close_ability_menu()
        self.selected_ability_id = ability_id
        self.set_action_mode("use_ability")

    def close_item_menu(self, *args):
        if self.item_menu:
            self.remove_widget(self.item_menu)
            self.item_menu = None

    def open_item_menu(self, *args):
        self.close_ability_menu()
        self.close_item_menu()
        if not self.active_combat_character: return

        inventory = self.active_combat_character.inventory
        if not inventory:
            self.add_to_log("Your inventory is empty.")
            return

        self.item_menu = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width='200dp',
            height=f"{min(len(inventory) * 44, 220)}dp",
            pos_hint={'center_x': 0.5, 'top': 2.5}
        )

        scroll = ScrollView(size_hint_y=1)
        scroll_content = BoxLayout(orientation='vertical', size_hint_y=None)
        scroll_content.bind(minimum_height=scroll_content.setter('height'))

        for item_id, quantity in inventory.items():
            btn = Button(text=f"{item_id} (x{quantity})", size_hint_y=None, height='44dp')
            btn.bind(on_release=partial(self.select_item, item_id))
            scroll_content.add_widget(btn)

        scroll.add_widget(scroll_content)
        self.item_menu.add_widget(scroll)
        self.add_widget(self.item_menu)

    def show_reaction_popup(self, data):
        reactor = data.get('reactor_id')
        trigger = data.get('trigger_id')
        name = data.get('reaction_name')

        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        content.add_widget(Label(text=f"{reactor}! {trigger} is moving past you.", font_size='16sp'))
        content.add_widget(Label(text=f"Use {name}?", font_size='20sp', bold=True))

        btns = BoxLayout(size_hint_y=0.4, spacing='10dp')

        yes_btn = Button(text="Strike! (Yes)", background_color=(0, 1, 0, 1))
        yes_btn.bind(on_release=lambda x: self.send_reaction_response("execute", data))

        no_btn = Button(text="Ignore (No)", background_color=(1, 0, 0, 1))
        no_btn.bind(on_release=lambda x: self.send_reaction_response("skip", data))

        btns.add_widget(yes_btn)
        btns.add_widget(no_btn)
        content.add_widget(btns)

        self.reaction_popup = Popup(title="Reaction Opportunity", content=content, size_hint=(0.6, 0.4), auto_dismiss=False)
        self.reaction_popup.open()

    def send_reaction_response(self, decision, data):
        if hasattr(self, 'reaction_popup'):
            self.reaction_popup.dismiss()

        action = story_schemas.PlayerActionRequest(
            action="resolve_reaction",
            ready_action_details={"decision": decision}
        )

        reactor_id = data.get('reactor_id')
        self.handle_player_action(reactor_id, action)

    def select_item(self, item_id: str, *args):
        self.close_item_menu()
        self.selected_item_id = item_id
        self.set_action_mode("use_item")

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
            
        # 0=Grass, 3=Stone Floor (Passable), others impassable
        if tile_id in [0, 3]:
            return True
        return False

    def on_touch_down(self, touch):
        # Check Popups first
        if self.ability_menu:
            if not self.ability_menu.collide_point(*touch.pos):
                self.close_ability_menu()
            return True
        if self.item_menu:
            if not self.item_menu.collide_point(*touch.pos):
                self.close_item_menu()
            return True

        if not self.is_player_turn or not self.current_action or not self.active_combat_character:
            return super().on_touch_down(touch)

        if not self.map_view_widget or not self.map_view_widget.collide_point(*touch.pos):
            self.add_to_log("Targeting cancelled.")
            self.current_action = None
            return super().on_touch_down(touch)

        local_pos = self.map_view_widget.to_local(*touch.pos)
        tile_x = int(local_pos[0] // TILE_SIZE)
        map_height = len(self.location_context.get('generated_map_data', []))
        if map_height == 0: return True
        tile_y = (map_height - 1) - int(local_pos[1] // TILE_SIZE)

        # --- Move Action ---
        if self.current_action == "move":
            if not self.is_tile_passable(tile_x, tile_y):
                self.add_to_log("You can't move there (Blocked).")
                self.current_action = None
                return True

            # --- Distance Check ---
            curr_x = self.active_combat_character.position_x
            curr_y = self.active_combat_character.position_y
            distance = max(abs(tile_x - curr_x), abs(tile_y - curr_y))
            speed = self.active_combat_character.stats.get("Speed", 6)

            if distance > speed:
                self.add_to_log(f"Too far! {distance}m > {speed}m.")
                self.current_action = None
                return True
            # ----------------------

            # If we pass, send the action
            self.add_to_log(f"{self.active_combat_character.name} moves to ({tile_x}, {tile_y}).")
            action = story_schemas.PlayerActionRequest(
                action="move", coordinates=[tile_x, tile_y]
            )
            self.handle_player_action(self.active_combat_character.id, action)
            self.current_action = None
            return True
        # --- END FIX ---

        target = self.get_target_at_coord(tile_x, tile_y)
        
        # Determine if action is friendly
        is_friendly_action = False
        if self.current_action == "use_item" and "potion" in str(self.selected_item_id):
            is_friendly_action = True
        elif self.current_action == "use_ability" and "Heal" in str(self.selected_ability_id):
            is_friendly_action = True
        
        target_id = None
        if target:
            t_type, t_data = target
            
            if t_type == "npc" and not is_friendly_action:
                target_id = f"npc_{t_data.get('id')}"
            elif t_type == "player" and is_friendly_action:
                target_id = t_data.get('id')
            elif t_type == "player" and not is_friendly_action:
                 self.add_to_log("Cannot attack ally.")
                 return True
            elif t_type == "npc" and is_friendly_action:
                 self.add_to_log("Cannot heal enemy.")
                 return True
        else:
            self.add_to_log("Invalid target.")
            return True

        if target_id:
            ability_id = self.selected_ability_id if self.current_action == "use_ability" else None
            item_id = self.selected_item_id if self.current_action == "use_item" else None
            
            action = story_schemas.PlayerActionRequest(
                action=self.current_action,
                target_id=target_id,
                ability_id=ability_id,
                item_id=item_id
            )
            self.handle_player_action(self.active_combat_character.id, action)
            self.current_action = None
            self.selected_ability_id = None
            self.selected_item_id = None

        return True