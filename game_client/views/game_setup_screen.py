"""
The Game Setup screen.
Allows party selection, new character creation, and game settings.
This replaces the old 'game_setup_panel.py' and uses direct
monolith imports instead of API calls.
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.app import App
from kivy.properties import ObjectProperty, ListProperty
from typing import List, Dict
import logging
from kivy.factory import Factory

# --- Direct Monolith Imports ---
try:
    from monolith.modules.character_pkg import crud as char_crud
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
    from monolith.modules.character_pkg import schemas as char_schemas
    from monolith.modules import rules as rules_api
except ImportError as e:
    logging.error(f"GAME_SETUP: Failed to import monolith modules: {e}")
    # Create dummy fallbacks so the app doesn't crash on import
    char_crud = None
    char_services = None
    CharSession = None
    char_schemas = None
    rules_api = None

import random
import uuid

class GameSetupScreen(Screen):
    """
    Screen for setting up a new game.
    Manages character selection and game settings.
    """

    # Kivy properties to hold our dynamic data
    character_select_list = ObjectProperty(None)
    difficulty_spinner = ObjectProperty(None) # Added missing property

    # This will hold the mapping of {char_name: CheckBox_widget}
    character_toggles: Dict[str, CheckBox] = {}
    character_toggles_by_id: Dict[str, CheckBox] = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        # Root Layout - Dungeon Background
        root = Factory.DungeonBackground(orientation='vertical', padding='20dp', spacing='20dp')

        # Title
        title = Factory.DungeonLabel(
            text="New Game Setup",
            font_size='32sp',
            size_hint_y=None,
            height='60dp',
            bold=True,
            color=(0.9, 0.8, 0.6, 1)
        )
        root.add_widget(title)

        # Main Content Area (Split: Left=Party, Right=Settings)
        content = BoxLayout(orientation='horizontal', spacing='20dp')

        # --- Left Column: Party Selection ---
        party_panel = Factory.ParchmentPanel(orientation='vertical', padding='10dp', spacing='10dp')
        
        party_label = Factory.ParchmentLabel(
            text="Select Party Members",
            size_hint_y=None,
            height='30dp',
            bold=True,
            font_size='18sp'
        )
        party_panel.add_widget(party_label)

        # Scrollable Character List
        scroll = ScrollView()
        self.character_select_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing='5dp')
        self.character_select_list.bind(minimum_height=self.character_select_list.setter('height'))
        scroll.add_widget(self.character_select_list)
        party_panel.add_widget(scroll)

        # Create New Character Button
        create_char_btn = Factory.DungeonButton(
            text="Create New Character",
            size_hint_y=None,
            height='44dp'
        )
        create_char_btn.bind(on_release=self.go_to_character_creation)
        party_panel.add_widget(create_char_btn)

        # Quick Start Button
        quick_start_btn = Factory.DungeonButton(
            text="Quick Start (Random)",
            size_hint_y=None,
            height='44dp'
        )
        quick_start_btn.bind(on_release=self.on_quick_start)
        party_panel.add_widget(quick_start_btn)

        content.add_widget(party_panel)

        # --- Right Column: Game Settings ---
        settings_panel = Factory.ParchmentPanel(orientation='vertical', padding='10dp', spacing='10dp', size_hint_x=0.6)
        
        settings_label = Factory.ParchmentLabel(
            text="Game Settings",
            size_hint_y=None,
            height='30dp',
            bold=True,
            font_size='18sp'
        )
        settings_panel.add_widget(settings_label)

        # Difficulty
        diff_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='44dp')
        diff_label = Factory.ParchmentLabel(text="Difficulty:", size_hint_x=0.4, halign='left')
        self.difficulty_spinner = Spinner(
            text='Normal',
            values=('Story', 'Normal', 'Hard', 'Deadly'),
            size_hint_x=0.6
        )
        diff_box.add_widget(diff_label)
        diff_box.add_widget(self.difficulty_spinner)
        settings_panel.add_widget(diff_box)

        # Spacer
        settings_panel.add_widget(Label())

        content.add_widget(settings_panel)
        root.add_widget(content)

        # Bottom Bar: Back and Start
        bottom_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing='20dp')
        
        back_btn = Factory.DungeonButton(text="Back")
        back_btn.bind(on_release=self.go_to_main_menu)
        
        start_btn = Factory.DungeonButton(text="Start Adventure")
        start_btn.bind(on_release=self.start_game)

        bottom_bar.add_widget(back_btn)
        bottom_bar.add_widget(start_btn)
        root.add_widget(bottom_bar)

        self.add_widget(root)

    def on_enter(self, *args):
        self.load_characters()

    def load_characters(self):
        """
        Fetches the character list directly from the database
        and populates the checkbox list.
        """
        if not CharSession or not char_crud or not char_services:
            self.character_select_list.clear_widgets()
            self.character_select_list.add_widget(Label(text="Error: Monolith not loaded"))
            return

        self.character_select_list.clear_widgets()
        self.character_toggles.clear()
        self.character_toggles_by_id.clear()

        db = None
        try:
            db = CharSession()
            db_chars = char_crud.list_characters(db)

            if db_chars:
                # 2. Convert models to the context dicts using the service
                char_contexts = [char_services.get_character_context(c) for c in db_chars]

                if not char_contexts:
                    self.character_select_list.add_widget(Label(text="No characters found."))
                    return

                # --- NEW: Populate Checkbox List ---
                for char_context in char_contexts:
                    char_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='44dp')

                    # Container for checkbox with dark background to make it visible
                    check_container = BoxLayout(size_hint_x=0.2, padding='10dp')
                    with check_container.canvas.before:
                        from kivy.graphics import Color, Rectangle
                        Color(0.2, 0.15, 0.1, 1) # Dark brown background for checkbox area
                        Rectangle(pos=check_container.pos, size=check_container.size)
                    # Bind canvas update
                    def update_rect(instance, value):
                        instance.canvas.before.children[2].pos = instance.pos
                        instance.canvas.before.children[2].size = instance.size
                    check_container.bind(pos=update_rect, size=update_rect)

                    checkbox = CheckBox(color=(1, 1, 1, 1)) # White checkmark
                    check_container.add_widget(checkbox)

                    # High contrast label (Black text)
                    label = Label(
                        text=char_context.name, 
                        size_hint_x=0.8, 
                        halign='left', 
                        valign='middle',
                        color=(0, 0, 0, 1), # Black text
                        font_size='18sp',
                        bold=True
                    )
                    label.bind(size=label.setter('text_size')) 

                    char_box.add_widget(check_container)
                    char_box.add_widget(label)

                    self.character_select_list.add_widget(char_box)
                    self.character_toggles[char_context.name] = checkbox
                    self.character_toggles_by_id[char_context.id] = checkbox
                # --- END NEW ---

            else:
                self.character_select_list.add_widget(Label(text="No characters found."))

        except Exception as e:
            logging.error(f"GAME_SETUP: Failed to load character list: {e}")
            self.character_select_list.clear_widgets()
            self.character_select_list.add_widget(Label(text="Error: Could not load characters."))
        finally:
            if db:
                db.close() # Always close the session

    def preselect_character(self, char_id):
        """Selects the checkbox for the given character ID."""
        # Ensure characters are loaded first
        self.load_characters()
        if char_id in self.character_toggles_by_id:
            self.character_toggles_by_id[char_id].active = True

    def go_to_main_menu(self, instance):
        """Navigates back to the main menu."""
        App.get_running_app().root.current = 'main_menu'

    def go_to_character_creation(self, instance):
        """Navigates to the character creation screen."""
        App.get_running_app().root.current = 'character_creation'

    def start_game(self, instance):
        """Collects settings and navigates to the main game screen."""

        # --- MODIFIED: Get all selected characters ---
        selected_character_names = []
        for name, checkbox in self.character_toggles.items():
            if checkbox.active:
                selected_character_names.append(name)

        difficulty = self.difficulty_spinner.text

        if not selected_character_names:
            logging.warning("GAME_SETUP: Cannot start game, no character selected.")
            # TODO: Show a popup to the user
            return
        # --- END MODIFIED ---

        logging.info(f"Starting game with party: {selected_character_names} at {difficulty} difficulty.")

        # Store settings in the app
        app = App.get_running_app()
        app.game_settings = {
            'party_list': selected_character_names, # <-- Use new list
            'difficulty': difficulty
        }

        app.root.current = 'main_interface'

    def on_quick_start(self, instance):
        """Generates a random character and starts the game immediately."""
        if not rules_api or not char_services or not CharSession:
            logging.error("Cannot quick start: Monolith not loaded.")
            return

        logging.info("Quick Start initiated. Generating random character...")
        
        # 1. Fetch Rules Data
        rules_data = {
            "kingdoms": rules_api.get_all_kingdoms(),
            "schools": rules_api.get_all_ability_schools(),
            "origins": rules_api.get_origin_choices(),
            "childhoods": rules_api.get_childhood_choices(),
            "coming_of_ages": rules_api.get_coming_of_age_choices(),
            "trainings": rules_api.get_training_choices(),
            "devotions": rules_api.get_devotion_choices(),
            "talents": ["Basic Strike"], # Simplified
            "kingdom_features_data": rules_api.get_data("kingdom_features_data"),
            "stats_list": rules_api.get_all_stats(),
            "all_skills": rules_api.get_all_skills()
        }

        # 2. Random Selections
        kingdom = random.choice(rules_data["kingdoms"])
        school = random.choice(rules_data["schools"])
        
        # Features
        feature_choices = []
        kf_data = rules_data["kingdom_features_data"]
        for i in range(1, 9):
            f_key = f"F{i}"
            f_data = kf_data.get(f_key, {})
            options = f_data.get(kingdom, [])
            if not options and "All" in f_data: options = f_data["All"]
            
            if options:
                choice = random.choice(options)
                feature_choices.append({"feature_id": f_key, "choice_name": choice.get("name")})

        # Backgrounds
        def pick_bg(key):
            opts = rules_data.get(key, [])
            return random.choice(opts)["name"] if opts else "None"

        new_char = char_schemas.CharacterCreate(
            name=f"Random_{str(uuid.uuid4())[:4]}",
            kingdom=kingdom,
            ability_school=school,
            feature_choices=feature_choices,
            origin_choice=pick_bg("origins"),
            childhood_choice=pick_bg("childhoods"),
            coming_of_age_choice=pick_bg("coming_of_ages"),
            training_choice=pick_bg("trainings"),
            devotion_choice=pick_bg("devotions"),
            ability_talent="Basic Strike",
            portrait_id="character_1"
        )

        # 3. Create Character
        try:
            with CharSession() as db:
                res = char_services.create_character(db, new_char, rules_data=rules_data)
                logging.info(f"Random Character Created: {res.name}")
                
                # 4. Start Game
                app = App.get_running_app()
                app.game_settings = {
                    'party_list': [res.name],
                    'difficulty': self.difficulty_spinner.text
                }
                app.root.current = 'main_interface'
        except Exception as e:
            logging.error(f"Quick Start Failed: {e}")
            # TODO: Show popup

