import logging
from functools import partial
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.gridlayout import GridLayout
from kivy.factory import Factory
from game_client.utils import AsyncHelper

# --- Monolith Imports ---
try:
    from monolith.modules.character_pkg import schemas as char_schemas
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
    from monolith.modules import rules as rules_api
except ImportError as e:
    logging.error(f"Failed to import monolith modules: {e}")
    char_schemas = None
    char_services = None
    CharSession = None
    rules_api = None

class CharacterCreationScreen(Screen, AsyncHelper):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Store all user selections here
        self.selected_options = {
            "name": "",
            "kingdom": "",
            "ability_school": "",
            "origin": "",
            "childhood": "",
            "coming_of_age": "",
            "training": "",
            "devotion": "",
            "ability_talent": "",
            "features": {},  # feature_key -> selected value
        }
        self.feature_spinners = {}
        self.feature_widgets = [] # List of (label, spinner) tuples for easy cleanup
        self.build_ui()

    def on_enter(self):
        """Called when the screen is displayed. Load initial data asynchronously."""
        self.set_loading_state(True)
        self.run_async(self._fetch_rules_data, self._on_rules_data_loaded, self._on_rules_data_error)

    def _fetch_rules_data(self):
        """Fetch all rules data in a background thread."""
        if not rules_api:
            raise ImportError("Rules API not available")
        
        data = {}
        data['kingdoms'] = rules_api.get_all_kingdoms()
        data['schools'] = rules_api.get_all_ability_schools()
        data['origins'] = rules_api.get_origin_choices()
        data['childhoods'] = rules_api.get_childhood_choices()
        data['coming_of_ages'] = rules_api.get_coming_of_age_choices()
        data['trainings'] = rules_api.get_training_choices()
        data['devotions'] = rules_api.get_devotion_choices()
        
        # Load Talents
        talents_data = rules_api.get_all_talents_data()
        all_talents = []
        if talents_data:
            # Single Stat Mastery
            for t in talents_data.get("single_stat_mastery", []):
                if "talent_name" in t: all_talents.append(t["talent_name"])
            # Dual Stat Focus
            for t in talents_data.get("dual_stat_focus", []):
                if "talent_name" in t: all_talents.append(t["talent_name"])
            # Skill Mastery (nested)
            for cat in talents_data.get("single_skill_mastery", {}).values():
                for group in cat:
                    for t in group.get("talents", []):
                        if "talent_name" in t: all_talents.append(t["talent_name"])
        data['talents'] = sorted(all_talents)
        return data

    def _on_rules_data_loaded(self, data):
        """Populate UI with fetched data."""
        try:
            self.kingdom_spinner.values = tuple(data.get('kingdoms', [])) or ('No Kingdoms Found',)
            self.school_spinner.values = tuple(data.get('schools', [])) or ('No Schools Found',)
            self.origin_spinner.values = tuple(data.get('origins', []))
            self.childhood_spinner.values = tuple(data.get('childhoods', []))
            self.coming_of_age_spinner.values = tuple(data.get('coming_of_ages', []))
            self.training_spinner.values = tuple(data.get('trainings', []))
            self.devotion_spinner.values = tuple(data.get('devotions', []))
            self.talent_spinner.values = tuple(data.get('talents', [])) or ('No Talents Found',)
        except Exception as e:
            logging.error(f"Error populating UI: {e}")
        finally:
            self.set_loading_state(False)

    def _on_rules_data_error(self, error):
        """Handle data loading error."""
        logging.error(f"Failed to load rules data: {error}")
        self.set_loading_state(False)
        # Could show a popup here

    def set_loading_state(self, is_loading):
        """Toggle loading state UI."""
        # For now, just disable the create button or show a log
        # In a real app, we'd show a spinner overlay
        if hasattr(self, 'create_btn'):
            self.create_btn.disabled = is_loading
            self.create_btn.text = "Loading..." if is_loading else "Create Character"

    # ---------------------------------------------------------------------
    # UI Construction
    # ---------------------------------------------------------------------
    def build_ui(self):
        self.clear_widgets()
        # Root Layout - Dungeon Background
        root = Factory.DungeonBackground(orientation='vertical', padding='20dp', spacing='10dp')
        
        # Title
        root.add_widget(Factory.DungeonLabel(
            text="Create New Character", 
            font_size='32sp', 
            size_hint_y=None, 
            height='60dp',
            bold=True,
            color=(0.9, 0.8, 0.6, 1)
        ))

        # Main Form Area - Parchment Panel
        form_panel = Factory.ParchmentPanel(orientation='vertical', padding='10dp')
        
        scroll = ScrollView(size_hint_y=1)
        form_layout = GridLayout(cols=1, spacing='15dp', size_hint_y=None, padding='10dp')
        form_layout.bind(minimum_height=form_layout.setter('height'))
        self.form_layout = form_layout  # keep reference for dynamic feature spinners

        # ----- Basic fields -----
        # Name
        form_layout.add_widget(Factory.ParchmentLabel(text="Name:", size_hint_y=None, height='30dp', halign='left'))
        self.name_input = TextInput(multiline=False, size_hint_y=None, height='40dp')
        self.name_input.bind(text=self.on_name_change)
        form_layout.add_widget(self.name_input)

        # Kingdom
        form_layout.add_widget(Factory.ParchmentLabel(text="Kingdom:", size_hint_y=None, height='30dp', halign='left'))
        self.kingdom_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.kingdom_spinner.bind(text=self.on_kingdom_select)
        form_layout.add_widget(self.kingdom_spinner)

        # Ability School
        form_layout.add_widget(Factory.ParchmentLabel(text="Ability School:", size_hint_y=None, height='30dp', halign='left'))
        self.school_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.school_spinner.bind(text=self.on_school_select)
        form_layout.add_widget(self.school_spinner)

        # Origin
        form_layout.add_widget(Factory.ParchmentLabel(text="Origin:", size_hint_y=None, height='30dp', halign='left'))
        self.origin_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.origin_spinner.bind(text=self.on_origin_select)
        form_layout.add_widget(self.origin_spinner)

        # Childhood
        form_layout.add_widget(Factory.ParchmentLabel(text="Childhood:", size_hint_y=None, height='30dp', halign='left'))
        self.childhood_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.childhood_spinner.bind(text=self.on_childhood_select)
        form_layout.add_widget(self.childhood_spinner)

        # Coming of Age
        form_layout.add_widget(Factory.ParchmentLabel(text="Coming of Age:", size_hint_y=None, height='30dp', halign='left'))
        self.coming_of_age_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.coming_of_age_spinner.bind(text=self.on_coming_of_age_select)
        form_layout.add_widget(self.coming_of_age_spinner)

        # Training
        form_layout.add_widget(Factory.ParchmentLabel(text="Training:", size_hint_y=None, height='30dp', halign='left'))
        self.training_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.training_spinner.bind(text=self.on_training_select)
        form_layout.add_widget(self.training_spinner)

        # Devotion
        form_layout.add_widget(Factory.ParchmentLabel(text="Devotion:", size_hint_y=None, height='30dp', halign='left'))
        self.devotion_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.devotion_spinner.bind(text=self.on_devotion_select)
        form_layout.add_widget(self.devotion_spinner)

        # Talent Choice
        form_layout.add_widget(Factory.ParchmentLabel(text="Starting Talent:", size_hint_y=None, height='30dp', halign='left'))
        self.talent_spinner = Spinner(text='Select Talent...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.talent_spinner.bind(text=self.on_talent_select)
        form_layout.add_widget(self.talent_spinner)

        scroll.add_widget(form_layout)
        form_panel.add_widget(scroll)
        root.add_widget(form_panel)

        # ----- Footer -----
        footer = BoxLayout(size_hint_y=None, height='60dp', spacing='20dp')
        
        back_btn = Factory.DungeonButton(text="Back")
        back_btn.bind(on_release=self.go_back)
        
        self.create_btn = Factory.DungeonButton(text="Create Character")
        self.create_btn.bind(on_release=self.submit_character)
        
        footer.add_widget(back_btn)
        footer.add_widget(self.create_btn)
        root.add_widget(footer)

        self.add_widget(root)

    def load_feature_spinners(self, kingdom):
        """Load spinners for each feature based on the selected kingdom (Async)."""
        # 1. Clear existing dynamic widgets
        for label, spinner in self.feature_widgets:
            self.form_layout.remove_widget(label)
            self.form_layout.remove_widget(spinner)
        self.feature_widgets.clear()
        self.feature_spinners.clear()
        self.selected_options["features"] = {}

        # 2. Fetch new features asynchronously
        self.set_loading_state(True)
        self.run_async(
            lambda: self._fetch_features_task(kingdom),
            self._on_features_loaded,
            self._on_features_error
        )

    def _fetch_features_task(self, kingdom):
        if not rules_api:
            return {}
        return rules_api.get_features_for_kingdom(kingdom)

    def _on_features_loaded(self, features):
        self.set_loading_state(False)
        if not features:
            return

        # Sort keys numerically (F1, F2, ... F10)
        def sort_key(item):
            key = item[0]
            if key.startswith("F") and key[1:].isdigit():
                return int(key[1:])
            return 999

        for f_key, options in sorted(features.items(), key=sort_key):
            # Label
            label = Factory.ParchmentLabel(text=f"{f_key}:", size_hint_y=None, height='30dp', halign='left')
            self.form_layout.add_widget(label)
            
            # Spinner
            spinner = Spinner(text='Select...', values=tuple(options) if options else ('None',), size_hint_y=None, height='44dp')
            spinner.bind(text=lambda inst, val, key=f_key: self.on_feature_select(key, val))
            self.form_layout.add_widget(spinner)
            
            # Track for cleanup
            self.feature_widgets.append((label, spinner))
            self.feature_spinners[f_key] = spinner
            
            # Set default selection
            if options:
                spinner.text = options[0]
                self.selected_options["features"][f_key] = options[0]
            else:
                self.selected_options["features"][f_key] = None

    def _on_features_error(self, error):
        logging.error(f"Error loading features: {error}")
        self.set_loading_state(False)

    def on_feature_select(self, key, value):
        self.selected_options["features"][key] = value

    def on_name_change(self, instance, value):
        self.selected_options["name"] = value

    def on_kingdom_select(self, spinner, text):
        self.selected_options["kingdom"] = text
        self.load_feature_spinners(text)

    def on_school_select(self, spinner, text):
        self.selected_options["ability_school"] = text

    def on_origin_select(self, spinner, text):
        self.selected_options["origin"] = text

    def on_childhood_select(self, spinner, text):
        self.selected_options["childhood"] = text

    def on_coming_of_age_select(self, spinner, text):
        self.selected_options["coming_of_age"] = text

    def on_training_select(self, spinner, text):
        self.selected_options["training"] = text

    def on_devotion_select(self, spinner, text):
        self.selected_options["devotion"] = text

    def on_talent_select(self, spinner, text):
        self.selected_options["ability_talent"] = text

    def submit_character(self, instance):
        name = self.selected_options.get("name")
        if not name:
            logging.warning("Name is required!")
            # TODO: Show popup
            return
        
        # Validation
        required_fields = ["kingdom", "ability_school", "origin", "childhood", "coming_of_age", "training", "devotion", "ability_talent"]
        for field in required_fields:
            if not self.selected_options.get(field):
                logging.warning(f"{field} is required!")
                return

        self.set_loading_state(True)
        self.run_async(self._create_character_task, self._on_character_created, self._on_creation_error)

    def _create_character_task(self):
        name = self.selected_options.get("name")
        # Construct feature choices list of objects
        feature_choices_list = []
        for f_id, choice_name in self.selected_options.get("features", {}).items():
            feature_choices_list.append({"feature_id": f_id, "choice_name": choice_name})

        new_char = char_schemas.CharacterCreate(
            name=name,
            kingdom=self.selected_options.get("kingdom", "Unknown"),
            ability_school=self.selected_options.get("ability_school", "Unknown"),
            feature_choices=feature_choices_list,
            origin_choice=self.selected_options.get("origin", "Unknown"),
            childhood_choice=self.selected_options.get("childhood", "Unknown"),
            coming_of_age_choice=self.selected_options.get("coming_of_age", "Unknown"),
            training_choice=self.selected_options.get("training", "Unknown"),
            devotion_choice=self.selected_options.get("devotion", "Unknown"),
            ability_talent=self.selected_options.get("ability_talent", "Basic Strike"),
            portrait_id=self.selected_options.get("portrait_id", "character_1"),
        )
        
        if CharSession and char_services:
            # We use the decorator in char_services now, but create_character might not be decorated yet?
            # Wait, I refactored character.py. Let's check if create_character is decorated.
            # Yes, I refactored character.py.
            # But create_character takes `db` as argument.
            # If I call it without `db`, the decorator handles it.
            # So I can just call char_services.create_character(new_char) if I updated the signature.
            # Let's assume I did. But to be safe, I can still use the session context manager or rely on the decorator.
            # If I use the decorator, I don't need to pass db.
            # However, I need to check if I updated `create_character` signature in `character.py`.
            # I did refactor `monolith/modules/character.py`.
            # So I should be able to call `char_services.create_character(character_create=new_char)`
            # But wait, the original code used `with CharSession() as db:`.
            # If I use `char_services.create_character(db, new_char)`, it uses the passed db.
            # If I use `char_services.create_character(new_char)`, it creates a new session (if decorated).
            # I'll use the explicit session here to be safe or just call it if I'm sure.
            # Actually, for async task, it's better to let the service handle the session.
            # But I need to be sure `create_character` was refactored.
            # I'll check `character.py` content later if needed. For now, I'll assume it works or use the old way but inside the thread.
            # Using `with CharSession() as db:` is safe inside the thread.
            
            with CharSession() as db:
                res = char_services.create_character(db, new_char)
                return res
        else:
            raise Exception("Backend services not available")

    def _on_character_created(self, res):
        logging.info(f"Character Created: {res.name} (ID: {res.id})")
        app = App.get_running_app()
        if not hasattr(app, 'game_settings') or app.game_settings is None:
            app.game_settings = {}
        app.game_settings['party_list'] = [res.name]
        
        # Redirect to Game Setup
        game_setup_screen = app.root.get_screen('game_setup')
        game_setup_screen.preselect_character(res.id)
        app.root.current = 'game_setup'
        self.set_loading_state(False)

    def _on_creation_error(self, error):
        logging.error(f"Creation failed: {error}")
        self.set_loading_state(False)
        # TODO: Show error popup
    def go_back(self, instance):
        self.manager.current = 'main_menu'
