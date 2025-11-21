import logging
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
        self.selected_options = {
            "name": "",
            "kingdom": "",
            "ability_school": "",
            "features": {} 
        }
        self.feature_spinners = {}
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()
        root = BoxLayout(orientation='vertical', padding='20dp', spacing='10dp')
        
        # Header
        root.add_widget(Label(text="Create New Character", font_size='24sp', size_hint_y=0.1, color=(1,1,1,1)))

        # Scrollable Form
        scroll = ScrollView(size_hint_y=0.8)
        form_layout = GridLayout(cols=1, spacing='15dp', size_hint_y=None, padding='10dp')
        form_layout.bind(minimum_height=form_layout.setter('height'))

        # 1. Name
        form_layout.add_widget(Label(text="Name:", size_hint_y=None, height='30dp'))
        self.name_input = TextInput(multiline=False, size_hint_y=None, height='40dp')
        self.name_input.bind(text=self.on_name_change)
        form_layout.add_widget(self.name_input)

        # 2. Kingdom
        form_layout.add_widget(Label(text="Kingdom:", size_hint_y=None, height='30dp'))
        self.kingdom_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.kingdom_spinner.bind(text=self.on_kingdom_select)
        form_layout.add_widget(self.kingdom_spinner)

        # 3. Ability School
        form_layout.add_widget(Label(text="Ability School:", size_hint_y=None, height='30dp'))
        self.school_spinner = Spinner(text='Loading...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.school_spinner.bind(text=self.on_school_select)
        form_layout.add_widget(self.school_spinner)
        
        scroll.add_widget(form_layout)
        root.add_widget(scroll)

        # Footer
        footer = BoxLayout(size_hint_y=0.1, spacing='10dp')
        create_btn = Button(text="Create Character", background_color=(0.3, 0.8, 0.3, 1))
        create_btn.bind(on_release=self.submit_character)
        back_btn = Button(text="Back")
        back_btn.bind(on_release=self.go_back)
        
        footer.add_widget(back_btn)
        footer.add_widget(create_btn)
        root.add_widget(footer)
        
        self.add_widget(root)

    def on_enter(self):
        """Load data from Rules API when screen opens."""
        if not rules_api: return
        
        # Load Kingdoms
        try:
            kingdoms = rules_api.get_all_kingdoms()
            if kingdoms:
                self.kingdom_spinner.values = tuple(kingdoms)
                self.kingdom_spinner.text = kingdoms[0]
                self.selected_options["kingdom"] = kingdoms[0]
        except Exception as e:
            print(f"Error loading kingdoms: {e}")

        # Load Schools
        try:
            schools = rules_api.get_all_ability_schools()
            if schools:
                self.school_spinner.values = tuple(schools)
                self.school_spinner.text = schools[0]
                self.selected_options["ability_school"] = schools[0]
        except Exception as e:
             print(f"Error loading schools: {e}")

    def on_name_change(self, instance, value):
        self.selected_options["name"] = value

    def on_kingdom_select(self, instance, value):
        self.selected_options["kingdom"] = value

    def on_school_select(self, instance, value):
        self.selected_options["ability_school"] = value

    def submit_character(self, instance):
        name = self.selected_options.get("name")
        if not name:
            print("Name is required!")
            return

        try:
            # Construct valid schema
            # Note: We use placeholders for the detailed history to get it working first
            new_char = char_schemas.CharacterCreate(
                name=name,
                kingdom=self.selected_options["kingdom"],
                ability_school=self.selected_options["ability_school"],
                feature_choices=[], 
                origin_choice="Unknown",
                childhood_choice="Unknown",
                coming_of_age_choice="Unknown",
                training_choice="Unknown",
                devotion_choice="Unknown",
                ability_talent="Basic Strike", # Default so combat works
                portrait_id="character_1"
            )
            
            if CharSession and char_services:
                with CharSession() as db:
                    res = char_services.create_character(db, new_char)
                    print(f"Character Created: {res.name} (ID: {res.id})")
                    
                    # Set as active party and go to game
                    app = App.get_running_app()
                    if not app.game_settings: app.game_settings = {}
                    app.game_settings['party_list'] = [res.name]
                    app.root.current = 'main_interface'
        except Exception as e:
            logging.exception(f"Creation failed: {e}")

    def go_back(self, instance):
        self.manager.current = 'main_menu'