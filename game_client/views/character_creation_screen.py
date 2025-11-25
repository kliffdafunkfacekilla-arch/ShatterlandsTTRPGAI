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

class CharacterCreationScreen(Screen):
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
        self.build_ui()

    def on_enter(self):
        """Called when the screen is displayed. Load initial data."""
        if rules_api:
            try:
                # Load Kingdoms
                kingdoms = rules_api.get_all_kingdoms()
                self.kingdom_spinner.values = tuple(kingdoms) if kingdoms else ('No Kingdoms Found',)
                
                # Load Ability Schools
                schools = rules_api.get_all_ability_schools()
                self.school_spinner.values = tuple(schools) if schools else ('No Schools Found',)
                
                # Load Background Choices
                self.origin_spinner.values = tuple(rules_api.get_origin_choices())
                self.childhood_spinner.values = tuple(rules_api.get_childhood_choices())
                self.coming_of_age_spinner.values = tuple(rules_api.get_coming_of_age_choices())
                self.training_spinner.values = tuple(rules_api.get_training_choices())
                self.devotion_spinner.values = tuple(rules_api.get_devotion_choices())

                # Load Talents
                talents_data = rules_api.get_all_talents_data()
                # Flatten talents map for the spinner
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
                
                self.talent_spinner.values = tuple(sorted(all_talents)) if all_talents else ('No Talents Found',)
                
            except Exception as e:
                logging.error(f"Failed to load initial rules data: {e}")

    # ---------------------------------------------------------------------
    # UI Construction
    # ---------------------------------------------------------------------
    def build_ui(self):
        self.clear_widgets()
        root = BoxLayout(orientation='vertical', padding='20dp', spacing='10dp')
        root.add_widget(Label(text="Create New Character", font_size='24sp', size_hint_y=0.1, color=(1, 1, 1, 1)))

        scroll = ScrollView(size_hint_y=0.8)
        form_layout = GridLayout(cols=1, spacing='15dp', size_hint_y=None, padding='10dp')
        form_layout.bind(minimum_height=form_layout.setter('height'))
        self.form_layout = form_layout  # keep reference for dynamic feature spinners

        # ----- Basic fields -----
        # Name
        form_layout.add_widget(Label(text="Name:", size_hint_y=None, height='30dp'))
        self.name_input = TextInput(multiline=False, size_hint_y=None, height='40dp')
        self.name_input.bind(text=self.on_name_change)
        form_layout.add_widget(self.name_input)

        # Kingdom
        form_layout.add_widget(Label(text="Kingdom:", size_hint_y=None, height='30dp'))
        self.kingdom_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.kingdom_spinner.bind(text=self.on_kingdom_select)
        form_layout.add_widget(self.kingdom_spinner)

        # Ability School
        form_layout.add_widget(Label(text="Ability School:", size_hint_y=None, height='30dp'))
        self.school_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.school_spinner.bind(text=self.on_school_select)
        form_layout.add_widget(self.school_spinner)

        # Origin
        form_layout.add_widget(Label(text="Origin:", size_hint_y=None, height='30dp'))
        self.origin_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.origin_spinner.bind(text=self.on_origin_select)
        form_layout.add_widget(self.origin_spinner)

        # Childhood
        form_layout.add_widget(Label(text="Childhood:", size_hint_y=None, height='30dp'))
        self.childhood_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.childhood_spinner.bind(text=self.on_childhood_select)
        form_layout.add_widget(self.childhood_spinner)

        # Coming of Age
        form_layout.add_widget(Label(text="Coming of Age:", size_hint_y=None, height='30dp'))
        self.coming_of_age_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.coming_of_age_spinner.bind(text=self.on_coming_of_age_select)
        form_layout.add_widget(self.coming_of_age_spinner)

        # Training
        form_layout.add_widget(Label(text="Training:", size_hint_y=None, height='30dp'))
        self.training_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.training_spinner.bind(text=self.on_training_select)
        form_layout.add_widget(self.training_spinner)

        # Devotion
        form_layout.add_widget(Label(text="Devotion:", size_hint_y=None, height='30dp'))
        self.devotion_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.devotion_spinner.bind(text=self.on_devotion_select)
        form_layout.add_widget(self.devotion_spinner)

        # Talent Choice
        form_layout.add_widget(Label(text="Starting Talent:", size_hint_y=None, height='30dp'))
        self.talent_spinner = Spinner(text='Select Talent...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.talent_spinner.bind(text=self.on_talent_select)
        form_layout.add_widget(self.talent_spinner)

        scroll.add_widget(form_layout)
        root.add_widget(scroll)

        # ----- Footer -----
        footer = BoxLayout(size_hint_y=0.1, spacing='10dp')
        back_btn = Button(text="Back")
        back_btn.bind(on_release=self.go_back)
        create_btn = Button(text="Create Character", background_color=(0.3, 0.8, 0.3, 1))
        create_btn.bind(on_release=self.submit_character)
        footer.add_widget(back_btn)
        footer.add_widget(create_btn)
        root.add_widget(footer)

        self.add_widget(root)

    def load_feature_spinners(self, kingdom):
        """Load spinners for each feature based on the selected kingdom."""
        # Clear any existing feature spinners
        for spinner in list(self.feature_spinners.values()):
            # Remove associated label (assumed to be just before spinner in layout)
            if spinner.parent:
                idx = self.form_layout.children.index(spinner)
                # Remove label if exists
                if idx + 1 < len(self.form_layout.children):
                    self.form_layout.remove_widget(self.form_layout.children[idx + 1])
                self.form_layout.remove_widget(spinner)
        self.feature_spinners.clear()
        # Fetch features from rules API
        try:
            features = rules_api.get_features_for_kingdom(kingdom)
        except Exception as e:
            logging.error(f"Error fetching features for kingdom {kingdom}: {e}")
            features = {}
        
        # Create spinners for each feature
        # Sort keys numerically (F1, F2, ... F10)
        def sort_key(item):
            key = item[0]
            if key.startswith("F") and key[1:].isdigit():
                return int(key[1:])
            return 999

        for f_key, options in sorted(features.items(), key=sort_key):
            # Label
            self.form_layout.add_widget(Label(text=f"{f_key}:", size_hint_y=None, height='30dp'))
            spinner = Spinner(text='Loading...', values=tuple(options) if options else ('None',), size_hint_y=None, height='44dp')
            spinner.bind(text=lambda inst, val, key=f_key: self.on_feature_select(key, val))
            self.form_layout.add_widget(spinner)
            self.feature_spinners[f_key] = spinner
            # Set default selection
            if options:
                self.selected_options["features"][f_key] = options[0]
            else:
                self.selected_options["features"][f_key] = None

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
            print("Name is required!")
            return
        try:
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
                with CharSession() as db:
                    res = char_services.create_character(db, new_char)
                    print(f"Character Created: {res.name} (ID: {res.id})")
                    app = App.get_running_app()
                    if not hasattr(app, 'game_settings') or app.game_settings is None:
                        app.game_settings = {}
                    app.game_settings['party_list'] = [res.name]
                    app.root.current = 'main_interface'
        except Exception as e:
            logging.exception(f"Creation failed: {e}")

    def go_back(self, instance):
        self.manager.current = 'main_menu'
