import logging
<<<<<<< Updated upstream
from functools import partial
=======
import random
>>>>>>> Stashed changes
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
    char_schemas, char_services, CharSession, rules_api = None, None, None, None

class CharacterCreationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Store all user choices state
        self.choices = {
            "name": "",
            "kingdom": "",
            "ability_school": "",
            "features": {}, # { "F1": "...", "F2": "..." }
            "backgrounds": {}, # { "origin": "...", ... }
            "ability_talent": None
        }
        self.step_ui_container = None
        self.feature_spinners = {}
        self.bg_spinners = {}

        self.build_base_layout()
        # Note: on_enter will trigger data loading

    def build_base_layout(self):
        self.clear_widgets()
        self.root_layout = BoxLayout(orientation='vertical', padding='15dp', spacing='10dp')

        # 1. Header
        self.title_label = Label(text="Character Creation: Step 1", font_size='24sp', size_hint_y=0.1)
        self.root_layout.add_widget(self.title_label)

        # 2. Dynamic Content Area (Scrollable)
        self.scroll_view = ScrollView(size_hint_y=0.8)
        self.step_ui_container = GridLayout(cols=1, spacing='10dp', size_hint_y=None, padding='10dp')
        self.step_ui_container.bind(minimum_height=self.step_ui_container.setter('height'))
        self.scroll_view.add_widget(self.step_ui_container)
        self.root_layout.add_widget(self.scroll_view)

        # 3. Footer
        self.footer = BoxLayout(size_hint_y=0.1, spacing='10dp')
        self.back_btn = Button(text="Back/Cancel", on_release=self.go_back)
        self.next_btn = Button(text="Next", background_color=(0.3, 0.8, 0.3, 1))
        # Binding for next_btn happens in the step build functions
        self.footer.add_widget(self.back_btn)
        self.footer.add_widget(self.next_btn)
        self.root_layout.add_widget(self.footer)

        self.add_widget(self.root_layout)

    def on_enter(self):
        """Reset and rebuild Step 1 when screen opens."""
        self.build_step_1()

    def build_step_1(self):
        """Builds Form: Identity, Biology, History, Class."""
        self.step_ui_container.clear_widgets()
        self.title_label.text = "Step 1: Body & History"
        self.next_btn.text = "Next: Calculate Stats"
        self.next_btn.unbind(on_release=self.submit_character)
        self.next_btn.bind(on_release=self.on_next_click)

        # --- A. Name ---
        self.step_ui_container.add_widget(Label(text="Name:", size_hint_y=None, height='30dp'))
        name_inp = TextInput(text=self.choices["name"], multiline=False, size_hint_y=None, height='40dp')
        name_inp.bind(text=lambda i, v: self.update_choice("name", v))
        self.step_ui_container.add_widget(name_inp)

        # --- B. Kingdom ---
        self.step_ui_container.add_widget(Label(text="Kingdom:", size_hint_y=None, height='30dp'))
        kingdoms = rules_api.get_all_kingdoms() if rules_api else ["Error: No Rules API"]
        k_val = self.choices.get("kingdom") or (kingdoms[0] if kingdoms else "")

        k_spinner = Spinner(text=k_val, values=tuple(kingdoms), size_hint_y=None, height='44dp')
        k_spinner.bind(text=self.on_kingdom_select)
        self.step_ui_container.add_widget(k_spinner)
        # Trigger initial feature load
        if k_val: self.on_kingdom_select(k_spinner, k_val)

        # --- C. Features (F1-F9) ---
        self.step_ui_container.add_widget(Label(text="--- Evolutionary Features ---", size_hint_y=None, height='40dp', color=(0.6, 1, 1, 1)))
        for i in range(1, 10):
            f_id = f"F{i}"
            label_text = f"Feature {i} (Capstone)" if i==9 else f"Feature {i}"
            self.step_ui_container.add_widget(Label(text=label_text, size_hint_y=None, height='30dp'))

            # Create Spinner (values populated by on_kingdom_select)
            current_val = self.choices["features"].get(f_id, "Loading...")
            spinner = Spinner(text=current_val, values=[], size_hint_y=None, height='44dp')
            spinner.bind(text=partial(self.update_feature, f_id))
            self.feature_spinners[f_id] = spinner
            self.step_ui_container.add_widget(spinner)

        # --- D. Backgrounds ---
        self.step_ui_container.add_widget(Label(text="--- Background History ---", size_hint_y=None, height='40dp', color=(0.6, 1, 1, 1)))

        bg_map = {
            "origin": (rules_api.get_origin_choices() if rules_api else [], "Origin"),
            "childhood": (rules_api.get_childhood_choices() if rules_api else [], "Childhood"),
            "coming_of_age": (rules_api.get_coming_of_age_choices() if rules_api else [], "Coming of Age"),
            "training": (rules_api.get_training_choices() if rules_api else [], "Training"),
            "devotion": (rules_api.get_devotion_choices() if rules_api else [], "Devotion")
        }

        for key, (data_list, display_name) in bg_map.items():
            self.step_ui_container.add_widget(Label(text=display_name, size_hint_y=None, height='30dp'))
            current_val = self.choices["backgrounds"].get(key) or (data_list[0] if data_list else "N/A")
            self.choices["backgrounds"][key] = current_val # Ensure default is saved

            spinner = Spinner(text=current_val, values=tuple(data_list), size_hint_y=None, height='44dp')
            spinner.bind(text=partial(self.update_background, key))
            self.step_ui_container.add_widget(spinner)

        # --- E. Class ---
        self.step_ui_container.add_widget(Label(text="--- Class ---", size_hint_y=None, height='40dp', color=(0.6, 1, 1, 1)))
        schools = rules_api.get_all_ability_schools() if rules_api else []
        curr_school = self.choices.get("ability_school") or (schools[0] if schools else "")
        self.choices["ability_school"] = curr_school

        s_spinner = Spinner(text=curr_school, values=tuple(schools), size_hint_y=None, height='44dp')
        s_spinner.bind(text=lambda i, v: self.update_choice("ability_school", v))
        self.step_ui_container.add_widget(s_spinner)

    def build_step_2(self, preview_data):
        """Step 2: Verify Stats & Pick Eligible Talent"""
        self.step_ui_container.clear_widgets()
        self.title_label.text = "Step 2: Verify & Finalize"
        self.next_btn.text = "Create Character"
        self.next_btn.unbind(on_release=self.on_next_click)
        self.next_btn.bind(on_release=self.submit_character)

        # 1. Display Calculated Stats
        self.step_ui_container.add_widget(Label(text="Projected Attributes:", size_hint_y=None, height='30dp', bold=True, color=(1, 1, 0.5, 1)))
        stats = preview_data.get("calculated_stats", {})

        # Create a nice grid for stats
        stat_grid = GridLayout(cols=2, size_hint_y=None, height='200dp', spacing='5dp')
        for k, v in stats.items():
            stat_grid.add_widget(Label(text=f"{k}: {v}", size_hint_y=None, height='30dp'))
        self.step_ui_container.add_widget(stat_grid)

        # 2. Talent Selection (Filtered by Eligibility)
        self.step_ui_container.add_widget(Label(text="Select Starting Talent:", size_hint_y=None, height='30dp', bold=True, color=(0.5, 1, 0.5, 1)))
        self.step_ui_container.add_widget(Label(text="(Based on your stats/skills)", size_hint_y=None, height='20dp', font_size='12sp'))

        talents_list = preview_data.get("eligible_talents", [])
        # Extract names safely
        t_names = []
        for t in talents_list:
            if isinstance(t, dict): t_names.append(t.get('name', 'Unknown'))
            elif hasattr(t, 'name'): t_names.append(t.name)

        if not t_names:
            t_names = ["No Eligible Talents"]

        # Default selection
        self.choices["ability_talent"] = t_names[0]

        t_spinner = Spinner(text=t_names[0], values=tuple(t_names), size_hint_y=None, height='44dp')
        t_spinner.bind(text=lambda i, v: self.update_choice("ability_talent", v))
        self.step_ui_container.add_widget(t_spinner)

    # --- Logic Handlers ---

    def update_choice(self, key, value): self.choices[key] = value
    def update_feature(self, f_id, instance, value): self.choices["features"][f_id] = value
    def update_background(self, key, instance, value): self.choices["backgrounds"][key] = value

    def on_kingdom_select(self, instance, value):
        self.choices["kingdom"] = value
        if not rules_api: return
        # Reload feature spinners based on new kingdom
        try:
            f_map = rules_api.get_features_for_kingdom(value)
            for f_id, options in f_map.items():
                if f_id in self.feature_spinners:
                    spinner = self.feature_spinners[f_id]
                    spinner.values = tuple(options)
                    if options:
                        spinner.text = options[0]
                        self.choices["features"][f_id] = options[0]
                    else:
                        spinner.text = "None"
                        self.choices["features"][f_id] = ""
        except Exception as e:
            logging.error(f"Error updating features: {e}")

    def on_next_click(self, instance):
        """Calculate stats and move to step 2"""
        if not self.choices["name"]:
            self.title_label.text = "Error: Name Required!"
            self.title_label.color = (1, 0, 0, 1)
            return

        if rules_api:
            try:
<<<<<<< Updated upstream
                # Perform the Dry Run
                preview = rules_api.calculate_creation_preview(self.choices)
                self.title_label.color = (1, 1, 1, 1) # Reset color
                self.build_step_2(preview)
            except Exception as e:
                logging.exception(f"Preview calculation failed: {e}")
                self.title_label.text = "Error Calculating Stats"
=======
                # Load Kingdoms
                kingdoms = rules_api.get_all_kingdoms()
                self.kingdom_spinner.values = tuple(kingdoms) if kingdoms else ('No Kingdoms Found',)
                
                # Load Ability Schools
                schools = rules_api.get_all_ability_schools()
                self.school_spinner.values = tuple(schools) if schools else ('No Schools Found',)
                
                # Load Background Choices
                self.origin_spinner.values = tuple(item['name'] for item in rules_api.get_origin_choices())
                self.childhood_spinner.values = tuple(item['name'] for item in rules_api.get_childhood_choices())
                self.coming_of_age_spinner.values = tuple(item['name'] for item in rules_api.get_coming_of_age_choices())
                self.training_spinner.values = tuple(item['name'] for item in rules_api.get_training_choices())
                self.devotion_spinner.values = tuple(item['name'] for item in rules_api.get_devotion_choices())

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

        # Placeholder for dynamic feature spinners – they will be added to self.form_layout later
        # Feature spinners will be loaded dynamically based on selected kingdom


        scroll.add_widget(form_layout)
        root.add_widget(scroll)

        # ----- Footer -----
        footer = BoxLayout(size_hint_y=0.1, spacing='10dp')
        back_btn = Button(text="Back")
        back_btn.bind(on_release=self.go_back)
        
        random_btn = Button(text="Random")
        random_btn.bind(on_release=self.randomize_character)

        create_btn = Button(text="Create Character", background_color=(0.3, 0.8, 0.3, 1))
        create_btn.bind(on_release=self.submit_character)
        
        footer.add_widget(back_btn)
        footer.add_widget(random_btn)
        footer.add_widget(create_btn)
        root.add_widget(footer)

        self.add_widget(root)

    def randomize_character(self, instance):
        """Randomly selects values for all character options."""
        # Random Name
        names = ["Arion", "Lyra", "Kael", "Seraphina", "Ronan", "Elara"]
        self.name_input.text = f"{random.choice(names)}{random.randint(10, 99)}"

        # Random Kingdom
        if self.kingdom_spinner.values and self.kingdom_spinner.values[0] != 'Loading...':
            self.kingdom_spinner.text = random.choice(self.kingdom_spinner.values)

        # Random Ability School
        if self.school_spinner.values and self.school_spinner.values[0] != 'Loading...':
            self.school_spinner.text = random.choice(self.school_spinner.values)

        # Random Origin
        if self.origin_spinner.values and self.origin_spinner.values[0] != 'Loading...':
            self.origin_spinner.text = random.choice(self.origin_spinner.values)

        # Random Childhood
        if self.childhood_spinner.values and self.childhood_spinner.values[0] != 'Loading...':
            self.childhood_spinner.text = random.choice(self.childhood_spinner.values)

        # Random Coming of Age
        if self.coming_of_age_spinner.values and self.coming_of_age_spinner.values[0] != 'Loading...':
            self.coming_of_age_spinner.text = random.choice(self.coming_of_age_spinner.values)

        # Random Training
        if self.training_spinner.values and self.training_spinner.values[0] != 'Loading...':
            self.training_spinner.text = random.choice(self.training_spinner.values)

        # Random Devotion
        if self.devotion_spinner.values and self.devotion_spinner.values[0] != 'Loading...':
            self.devotion_spinner.text = random.choice(self.devotion_spinner.values)

        # Random Talent
        if self.talent_spinner.values and self.talent_spinner.values[0] != 'Loading...':
            self.talent_spinner.text = random.choice(self.talent_spinner.values)
            
        # Random Features
        for f_key, spinner in self.feature_spinners.items():
            if spinner.values and spinner.values[0] != 'Loading...':
                spinner.text = random.choice(spinner.values)

    # ---------------------------------------------------------------------
    # ---------------------------------------------------------------------
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
>>>>>>> Stashed changes

    def submit_character(self, instance):
        """Final Commit to DB"""
        # Reformat features for Schema
        f_list = [{"feature_id": k, "choice_name": v} for k,v in self.choices["features"].items()]
        bg = self.choices["backgrounds"]

        try:
            new_char = char_schemas.CharacterCreate(
                name=self.choices["name"],
                kingdom=self.choices["kingdom"],
                ability_school=self.choices["ability_school"],
                feature_choices=f_list,
                origin_choice=bg.get("origin", ""),
                childhood_choice=bg.get("childhood", ""),
                coming_of_age_choice=bg.get("coming_of_age", ""),
                training_choice=bg.get("training", ""),
                devotion_choice=bg.get("devotion", ""),
                ability_talent=self.choices.get("ability_talent", ""),
                portrait_id="character_1"
            )

            if CharSession and char_services:
                with CharSession() as db:
                    res = char_services.create_character(db, new_char, rules_data=None)
                    logging.info(f"Created character {res.name}")

                    # Switch to Game
                    app = App.get_running_app()
                    if not app.game_settings: app.game_settings = {}
                    app.game_settings['party_list'] = [res.name]
                    app.root.current = 'main_interface'
        except Exception as e:
            logging.exception(f"Submit failed: {e}")

    def go_back(self, instance):
        if self.next_btn.text == "Create Character":
            # If in Step 2, go back to Step 1
            self.build_step_1()
        else:
            # If in Step 1, exit
            self.manager.current = 'main_menu'
