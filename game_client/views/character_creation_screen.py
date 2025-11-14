"""
The multi-step Character Creation screen.
This screen guides the user through the 11-step creation process
and calls the monolith's character service to create the character.
"""
import logging
import asyncio
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.properties import ObjectProperty, ListProperty, DictProperty, NumericProperty, StringProperty
from kivy.clock import Clock
from functools import partial

# --- Direct Monolith Imports ---
try:
    from monolith.modules import rules as rules_api
    from monolith.modules import character as char_api
    from monolith.modules.character_pkg import schemas as char_schemas
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
except ImportError as e:
    logging.error(f"CHAR_CREATE: Failed to import monolith modules: {e}")
    # This screen is unusable without the monolith, but we set dummies
    # to prevent a hard crash on import.
    rules_api, char_api, char_schemas, char_services, CharSession = None, None, None, None, None

# --- Constants ---
KINGDOMS = ["Mammal", "Reptile", "Avian", "Aquatic", "Insect", "Plant"]
FEATURE_IDS = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]
BACKGROUND_STEPS = ["origin", "childhood", "coming_of_age", "training", "devotion"]
BASE_STATS = {
    "Might": 8, "Endurance": 8, "Finesse": 8, "Reflexes": 8, "Vitality": 8, "Fortitude": 8,
    "Knowledge": 8, "Logic": 8, "Awareness": 8, "Intuition": 8, "Charm": 8, "Willpower": 8
}

class CharacterCreationScreen(Screen):
    """
    A multi-step screen for character creation.
    Uses a ScrollView to ensure content fits.
    """

    # --- Kivy Properties ---
    # Holds the main layout for the current step
    step_ui_container = ObjectProperty(None)
    # Holds all loaded rules data
    rules_data = DictProperty({})
    # Holds the user's selections
    choices = DictProperty({})
    # Holds the dynamically calculated stats
    calculated_stats = DictProperty(BASE_STATS.copy())
    # Holds the dynamically calculated skills
    calculated_skills = ListProperty([])
    # Holds the talents returned from the rules engine
    eligible_talents = ListProperty(['- Select a Talent -'])
    # Tracks the current step
    current_step_name = StringProperty('kingdom')

    # Our step definition
    STEP_ORDER = [
        'kingdom', 'features', 'backgrounds', 'school',
        'talent', 'name', 'review'
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
        # Asynchronously load all the rules data when the screen is first created
        # We use Clock.schedule_once to run this *after* the Kivy app loop has started
        Clock.schedule_once(self.load_all_rules_data)

    def build_ui(self):
        """Builds the static UI shell for the screen."""
        root_layout = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')

        # --- Title ---
        self.title_label = Label(text="Character Creation", font_size='32sp', size_hint_y=0.1)
        root_layout.add_widget(self.title_label)

        # --- ScrollView for dynamic content ---
        scroll_view = ScrollView(size_hint_y=0.8, do_scroll_x=False)
        # This container will be cleared and rebuilt for each step
        self.step_ui_container = BoxLayout(orientation='vertical', spacing='5dp', size_hint_y=None)
        self.step_ui_container.bind(minimum_height=self.step_ui_container.setter('height'))
        scroll_view.add_widget(self.step_ui_container)
        root_layout.add_widget(scroll_view)

        # --- Navigation ---
        nav_layout = BoxLayout(size_hint_y=0.1, spacing='10dp')
        self.prev_btn = Button(text='Back')
        self.prev_btn.bind(on_release=self.prev_step)
        nav_layout.add_widget(self.prev_btn)

        self.next_btn = Button(text='Next')
        self.next_btn.bind(on_release=self.next_step)
        nav_layout.add_widget(self.next_btn)

        root_layout.add_widget(nav_layout)
        self.add_widget(root_layout)

    def on_enter(self, *args):
        """Called when the screen is displayed."""
        self.reset_creation()
        self.rebuild_step_ui()

    def reset_creation(self):
        """Resets all choices to their defaults."""
        self.choices = {
            "kingdom": None,
            "feature_choices": [],
            "origin_choice": None,
            "childhood_choice": None,
            "coming_of_age_choice": None,
            "training_choice": None,
            "devotion_choice": None,
            "ability_school": None,
            "ability_talent": None,
            "name": "",
            "capstone_choice": None
        }
        self.calculated_stats = BASE_STATS.copy()
        self.calculated_skills = []
        self.eligible_talents = ['- Select a Talent -']
        self.current_step_name = 'kingdom'

    def rebuild_step_ui(self, *args):
        """Clears and rebuilds the UI for the current step."""
        if not self.step_ui_container:
            return # UI not ready yet

        self.step_ui_container.clear_widgets()

        step_builder = getattr(self, f"build_step_{self.current_step_name}", None)

        if step_builder:
            step_builder()
        else:
            self.step_ui_container.add_widget(Label(text=f"Unknown step: {self.current_step_name}"))

        # Update button states
        current_index = self.STEP_ORDER.index(self.current_step_name)
        self.prev_btn.disabled = (current_index == 0)
        self.next_btn.text = "Next"
        self.next_btn.disabled = False

        if self.current_step_name == 'review':
            self.next_btn.text = "Create Character"

        self.validate_step() # Check if 'Next' should be disabled

    # --- NAVIGATION ---

    def next_step(self, instance):
        """Moves to the next step or submits the character."""
        if self.current_step_name == 'review':
            self.submit_character()
            return

        current_index = self.STEP_ORDER.index(self.current_step_name)
        if current_index < len(self.STEP_ORDER) - 1:
            self.current_step_name = self.STEP_ORDER[current_index + 1]
            self.rebuild_step_ui()

    def prev_step(self, instance):
        """Moves to the previous step."""
        current_index = self.STEP_ORDER.index(self.current_step_name)
        if current_index > 0:
            self.current_step_name = self.STEP_ORDER[current_index - 1]
            self.rebuild_step_ui()
        elif current_index == 0:
            # First step, go back to game setup
            App.get_running_app().root.current = 'game_setup'

    def validate_step(self, *args):
        """Checks if the current step is complete and enables/disables 'Next'."""
        is_valid = False
        step = self.current_step_name
        if step == 'kingdom':
            is_valid = self.choices.get('kingdom') is not None
        elif step == 'features':
            is_valid = len(self.choices.get('feature_choices', [])) == len(FEATURE_IDS)
        elif step == 'backgrounds':
            is_valid = all(self.choices.get(f"{bg}_choice") for bg in BACKGROUND_STEPS)
        elif step == 'school':
            is_valid = self.choices.get('ability_school') is not None
        elif step == 'talent':
            is_valid = self.choices.get('ability_talent') is not None
        elif step == 'name':
            is_valid = len(self.choices.get('name', '')) > 1
        elif step == 'review':
            is_valid = self.choices.get('capstone_choice') is not None

        self.next_btn.disabled = not is_valid

    # --- DATA LOADING ---

    def load_all_rules_data(self, *args):
        """Loads all creation data from the monolith's rules module."""
        if not rules_api:
            self.step_ui_container.add_widget(Label(text="FATAL: Rules Module not loaded."))
            return

        logging.info("CHAR_CREATE: Loading all rules data...")
        try:
            # These are direct, synchronous calls to the loaded rules module
            # The 'async' functions in rules.py are stubs; we call the *real* functions.
            self.rules_data = {
                "kingdom_features": rules_api._get_data("kingdom_features_data"),
                "ability_schools": list(rules_api._get_data("ability_data").keys()),
                "origin_choices": rules_api._get_data("origin_choices"),
                "childhood_choices": rules_api._get_data("childhood_choices"),
                "coming_of_age_choices": rules_api._get_data("coming_of_age_choices"),
                "training_choices": rules_api._get_data("training_choices"),
                "devotion_choices": rules_api._get_data("devotion_choices"),
                "all_skills_map": rules_api._get_data("all_skills"),
                "talent_data": rules_api._get_data("talent_data"),
                "stats_list": rules_api._get_data("stats_list")
            }
            logging.info(f"CHAR_CREATE: Loaded {len(self.rules_data['kingdom_features'])} features.")
            logging.info(f"CHAR_CREATE: Loaded {len(self.rules_data['ability_schools'])} schools.")

            # Now that data is loaded, rebuild the UI for the first step
            self.rebuild_step_ui()

        except Exception as e:
            logging.exception(f"CHAR_CREATE: Failed to load rules data: {e}")
            self.step_ui_container.add_widget(Label(text=f"Error: Could not load rules data.\n{e}"))

    # --- UI BUILDERS FOR EACH STEP ---

    def build_step_kingdom(self):
        self.title_label.text = "Step 1: Choose Kingdom"
        self.step_ui_container.add_widget(Label(text="Select your character's kingdom:"))

        for kingdom in KINGDOMS:
            btn = Button(text=kingdom, size_hint_y=None, height='44dp')
            btn.bind(on_release=partial(self.select_choice, 'kingdom', kingdom))
            # Highlight if selected
            if self.choices.get('kingdom') == kingdom:
                btn.background_color = (0, 1, 0, 1) # Green
            self.step_ui_container.add_widget(btn)

    def build_step_features(self):
        self.title_label.text = "Step 2: Choose Features (F1-F8)"
        if not self.choices.get('kingdom'):
            self.step_ui_container.add_widget(Label(text="Please go back and select a kingdom first."))
            return

        kingdom = self.choices['kingdom']
        all_features = self.rules_data.get('kingdom_features', {})

        for f_id in FEATURE_IDS:
            feature_set = all_features.get(f_id, {}).get(kingdom, [])
            if not feature_set:
                logging.warning(f"No feature data for {f_id}/{kingdom}")
                continue

            feature_names = [f['name'] for f in feature_set]
            current_choice_name = self.get_current_feature_choice(f_id)

            self.step_ui_container.add_widget(Label(text=f"Feature {f_id}:", font_size='18sp'))
            spinner = Spinner(
                text=current_choice_name if current_choice_name else f'- Select {f_id} -',
                values=feature_names,
                size_hint_y=None,
                height='44dp'
            )
            spinner.option_cls.height = '44dp' # Make dropdown items taller
            spinner.bind(text=partial(self.select_feature, f_id))
            self.step_ui_container.add_widget(spinner)

    def build_step_backgrounds(self):
        self.title_label.text = "Step 3: Choose Background"

        for step_name in BACKGROUND_STEPS:
            self.step_ui_container.add_widget(Label(text=f"Choose {step_name.replace('_', ' ').title()}:", font_size='18sp'))
            choices_list = self.rules_data.get(f"{step_name}_choices", [])
            choice_names = [c['name'] for c in choices_list]

            current_choice = self.choices.get(f"{step_name}_choice")

            spinner = Spinner(
                text=current_choice if current_choice else f'- Select {step_name.title()} -',
                values=choice_names,
                size_hint_y=None,
                height='44dp'
            )
            spinner.option_cls.height = '44dp'
            spinner.bind(text=partial(self.select_choice, f"{step_name}_choice"))
            self.step_ui_container.add_widget(spinner)

    def build_step_school(self):
        self.title_label.text = "Step 4: Choose Ability School"
        self.step_ui_container.add_widget(Label(text="Select your starting Ability School:"))

        school_names = self.rules_data.get('ability_schools', [])
        current_choice = self.choices.get('ability_school')

        spinner = Spinner(
            text=current_choice if current_choice else '- Select a School -',
            values=school_names,
            size_hint_y=None,
            height='44dp'
        )
        spinner.option_cls.height = '44dp'
        spinner.bind(text=partial(self.select_choice, 'ability_school'))
        self.step_ui_container.add_widget(spinner)

    def build_step_talent(self):
        self.title_label.text = "Step 5: Choose Ability Talent"
        self.step_ui_container.add_widget(Label(text="Select your starting Talent:"))

        current_choice = self.choices.get('ability_talent')

        # This spinner's values are set by self.eligible_talents property
        self.talent_spinner = Spinner(
            text=current_choice if current_choice else '- Select a Talent -',
            values=self.eligible_talents,
            size_hint_y=None,
            height='44dp'
        )
        self.talent_spinner.option_cls.height = '44dp'
        self.talent_spinner.bind(text=partial(self.select_choice, 'ability_talent'))
        self.step_ui_container.add_widget(self.talent_spinner)

        # This step is special: it needs to fetch dynamic data
        self.fetch_eligible_talents()

    def build_step_name(self):
        self.title_label.text = "Step 6: Choose Name"
        self.step_ui_container.add_widget(Label(text="Enter your character's name:"))

        name_input = TextInput(
            text=self.choices.get('name', ''),
            size_hint_y=None,
            height='44dp',
            font_size='18sp',
            multiline=False
        )
        name_input.bind(text=partial(self.select_choice, 'name'))
        self.step_ui_container.add_widget(name_input)

    def build_step_review(self):
        self.title_label.text = "Step 7: Review"

        # --- Capstone (F9) Selection ---
        self.step_ui_container.add_widget(Label(text="Choose Capstone (F9):", font_size='18sp'))
        all_features = self.rules_data.get('kingdom_features', {})
        capstone_set = all_features.get('F9', {}).get('All', [])
        capstone_names = [f['name'] for f in capstone_set]
        current_capstone = self.choices.get('capstone_choice')

        capstone_spinner = Spinner(
            text=current_capstone if current_capstone else '- Select Capstone -',
            values=capstone_names,
            size_hint_y=None,
            height='44dp'
        )
        capstone_spinner.option_cls.height = '44dp'
        capstone_spinner.bind(text=partial(self.select_choice, 'capstone_choice'))
        self.step_ui_container.add_widget(capstone_spinner)

        # --- Summary ---
        self.step_ui_container.add_widget(Label(text="Review Your Character:", font_size='18sp', padding=('10dp', '10dp')))
        summary_text = f"""
Name: {self.choices.get('name')}
Kingdom: {self.choices.get('kingdom')}
Features: {len(self.choices.get('feature_choices', []))} selected
Origin: {self.choices.get('origin_choice')}
School: {self.choices.get('ability_school')}
Talent: {self.choices.get('ability_talent')}
Capstone: {self.choices.get('capstone_choice')}
"""
        self.step_ui_container.add_widget(Label(text=summary_text, halign='left', valign='top'))
        self.next_btn.text = "Create Character"

    # --- EVENT HANDLERS & LOGIC ---

    def select_choice(self, key, value, instance, *args):
        """Generic handler for simple choices."""
        self.choices[key] = value
        self.validate_step()

        # If the choice affects stats or skills, recalculate
        if key in ['kingdom', 'origin_choice', 'childhood_choice', 'coming_of_age_choice', 'training_choice', 'devotion_choice']:
            self.update_calculated_stats_and_skills()

    def select_feature(self, f_id, instance, value):
        """Handler for feature spinners."""
        new_choice = {"feature_id": f_id, "choice_name": value}

        # Remove old choice for this F_ID, if any
        self.choices['feature_choices'] = [
            c for c in self.choices['feature_choices'] if c['feature_id'] != f_id
        ]
        # Add the new one
        self.choices['feature_choices'].append(new_choice)

        self.update_calculated_stats_and_skills()
        self.validate_step()

    def get_current_feature_choice(self, f_id):
        """Finds the name of the selected choice for a given F_ID."""
        for choice in self.choices['feature_choices']:
            if choice['feature_id'] == f_id:
                return choice['choice_name']
        return None

    def update_calculated_stats_and_skills(self):
        """Recalculates stats and skills based on current choices."""
        logging.debug("Recalculating stats and skills...")
        new_stats = BASE_STATS.copy()
        new_skills = set() # Use a set for unique skills

        # 1. Apply Feature mods
        all_features = self.rules_data.get('kingdom_features', {})
        kingdom = self.choices.get('kingdom')
        if kingdom:
            for f_choice in self.choices['feature_choices']:
                f_id = f_choice['feature_id']
                f_name = f_choice['choice_name']
                feature_set = all_features.get(f_id, {}).get(kingdom, [])
                mod_data = next((item for item in feature_set if item.get("name") == f_name), None)

                if mod_data and 'mods' in mod_data:
                    rules_api.rules_core._apply_mods(new_stats, mod_data['mods']) # Call helper

        # 2. Apply Background Skills
        for step_name in BACKGROUND_STEPS:
            choice_name = self.choices.get(f"{step_name}_choice")
            if choice_name:
                choices_list = self.rules_data.get(f"{step_name}_choices", [])
                choice_data = next((c for c in choices_list if c['name'] == choice_name), None)
                if choice_data:
                    for skill in choice_data.get('skills', []):
                        new_skills.add(skill)

        self.calculated_stats = new_stats
        self.calculated_skills = list(new_skills)
        logging.debug(f"New Stats: {self.calculated_stats}")
        logging.debug(f"New Skills: {self.calculated_skills}")

        # If we are on the talent step, re-fetch talents
        if self.current_step_name == 'talent':
            self.fetch_eligible_talents()

    def fetch_eligible_talents(self):
        """
        Calls the rules engine to get talents.
        This is tricky because the monolith function is async.
        """
        if not rules_api: return

        self.talent_spinner.values = ['Fetching talents...']
        self.talent_spinner.text = 'Fetching talents...'
        self.next_btn.disabled = True

        # Convert skill list to skill rank map
        skill_ranks = {skill: 0 for skill in self.rules_data.get('all_skills_map', {})}
        for skill_name in self.calculated_skills:
            if skill_name in skill_ranks:
                skill_ranks[skill_name] = 1 # All background skills are Rank 1

        payload = {
            "stats": self.calculated_stats,
            "skills": skill_ranks
        }

        # We must run the async function in a separate thread/loop
        # and use Clock.schedule_once to update the Kivy UI
        async def do_fetch():
            try:
                talents = await rules_api.find_eligible_talents_api(None, payload)
                Clock.schedule_once(partial(self.update_talent_spinner, talents))
            except Exception as e:
                logging.exception(f"Failed to fetch talents: {e}")
                Clock.schedule_once(partial(self.update_talent_spinner, [], str(e)))

        asyncio.run(do_fetch()) # Run the async task

    def update_talent_spinner(self, talents, error_msg=None, *args):
        """Callback to update the talent spinner from the main Kivy thread."""
        if error_msg:
            self.eligible_talents = [f'Error: {error_msg}']
        elif not talents:
            self.eligible_talents = ['- No eligible talents found -']
        else:
            self.eligible_talents = ['- Select a Talent -'] + [t['name'] for t in talents]

        self.talent_spinner.values = self.eligible_talents
        self.talent_spinner.text = self.eligible_talents[0]
        self.choices['ability_talent'] = None # Reset choice
        self.validate_step()

    # --- FINAL SUBMISSION ---

    def submit_character(self):
        """Final step. Validates, builds the schema, and calls the monolith."""
        logging.info("CHAR_CREATE: Submitting character...")
        self.next_btn.disabled = True
        self.next_btn.text = "Creating..."

        # 1. Add the F9 Capstone choice to the feature list
        final_feature_choices = self.choices['feature_choices']
        final_feature_choices.append({
            "feature_id": "F9",
            "choice_name": self.choices['capstone_choice']
        })

        # 2. Build the Pydantic schema
        try:
            payload = char_schemas.CharacterCreate(
                name=self.choices['name'],
                kingdom=self.choices['kingdom'],
                feature_choices=final_feature_choices,
                origin_choice=self.choices['origin_choice'],
                childhood_choice=self.choices['childhood_choice'],
                coming_of_age_choice=self.choices['coming_of_age_choice'],
                training_choice=self.choices['training_choice'],
                devotion_choice=self.choices['devotion_choice'],
                ability_school=self.choices['ability_school'],
                ability_talent=self.choices['ability_talent']
            )
        except Exception as e:
            logging.error(f"Failed to create schema: {e}")
            self.next_btn.text = f"Error: {e}"
            # Do not re-enable button, data is bad
            return

        # 3. Call the monolith service (which is async)
        async def do_create():
            db = None
            try:
                db = CharSession()
                # We pass 'rules_data' to avoid re-fetching it
                new_char_context = await char_services.create_character(
                    db=db,
                    character=payload,
                    rules_data=self.rules_data
                )
                # Use Clock to update UI on success
                Clock.schedule_once(
                    partial(self.on_creation_success, new_char_context.name)
                )
            except Exception as e:
                logging.exception("Character creation failed in service.")
                if db:
                    db.rollback()
                # Use Clock to update UI on failure
                Clock.schedule_once(
                    partial(self.on_creation_failure, str(e))
                )
            finally:
                if db:
                    db.close()

        asyncio.run(do_create()) # Run the async task

    def on_creation_success(self, char_name, *args):
        """Callback on successful creation."""
        logging.info(f"Successfully created character: {char_name}")
        # Go back to game setup screen
        App.get_running_app().root.current = 'game_setup'

    def on_creation_failure(self, error_msg, *args):
        """Callback on failed creation."""
        logging.error(f"Creation failed: {error_msg}")
        self.next_btn.disabled = False
        self.next_btn.text = "Create Character"
        # We could show a popup here
