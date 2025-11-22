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

# --- Direct Monolith Imports ---
# ... (imports are unchanged) ...
try:
    from monolith.modules.character_pkg import crud as char_crud
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
except ImportError as e:
    logging.error(f"GAME_SETUP: Failed to import monolith modules: {e}")
    # Create dummy fallbacks so the app doesn't crash on import
    char_crud = None
    char_services = None
    CharSession = None

class GameSetupScreen(Screen):
    """
    Screen for setting up a new game.
    Manages character selection and game settings.
    """

    # Kivy properties to hold our dynamic data
    character_select_list = ObjectProperty(None)

    # This will hold the mapping of {char_name: CheckBox_widget}
    character_toggles: Dict[str, CheckBox] = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
        self.load_characters() # Load characters when the screen is created

    def build_ui(self):
        """Constructs the Kivy widget layout for this screen."""
        layout = BoxLayout(orientation='vertical', padding='20dp', spacing='10dp')

        layout.add_widget(Label(text='Game Setup', font_size='32sp', size_hint_y=0.15))

        # --- Party Selection ---
        layout.add_widget(Label(text='Select Party Members', size_hint_y=0.1))

        # --- NEW: ScrollView for Character Checkboxes ---
        scroll_view = ScrollView(size_hint_y=0.3)
        self.character_select_list = GridLayout(
            cols=1,
            size_hint_y=None,
            spacing='5dp'
        )
        self.character_select_list.bind(minimum_height=self.character_select_list.setter('height'))
        scroll_view.add_widget(self.character_select_list)
        layout.add_widget(scroll_view)
        # --- END NEW ---

        # Button to go to character creation
        create_char_btn = Button(
            text='Create New Character',
            size_hint_y=None,
            height='44dp'
        )
        create_char_btn.bind(on_release=self.go_to_character_creation)
        layout.add_widget(create_char_btn)

        # --- Game Settings (as defined in your outline) ---
        layout.add_widget(Label(text='Difficulty', size_hint_y=0.1))
        self.difficulty_spinner = Spinner(
            text='Normal',
            values=['Easy', 'Normal', 'Hard', 'Nightmare'],
            size_hint_y=None, height='44dp'
        )
        layout.add_widget(self.difficulty_spinner)

        # ... (Add other spinners for Style, Combat, etc. here) ...

        # Spacer
        layout.add_widget(BoxLayout(size_hint_y=0.1))

        # --- Start/Back Buttons ---
        button_layout = BoxLayout(size_hint_y=0.1, spacing='10dp')

        back_btn = Button(text='Back to Menu')
        back_btn.bind(on_release=self.go_to_main_menu)
        button_layout.add_widget(back_btn)

        start_btn = Button(text='Start Game')
        start_btn.bind(on_release=self.start_game)
        button_layout.add_widget(start_btn)

        layout.add_widget(button_layout)
        self.add_widget(layout)

    def on_enter(self, *args):
        """Kivy function that runs when this screen is shown."""
        # Refresh the character list every time we enter this screen
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

        char_names = ['No characters found']
        self.character_select_list.clear_widgets()
        self.character_toggles.clear()

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

                    checkbox = CheckBox(size_hint_x=0.2)
                    label = Label(text=char_context.name, size_hint_x=0.8, halign='left')
                    label.bind(size=label.setter('text_size')) # for alignment

                    char_box.add_widget(checkbox)
                    char_box.add_widget(label)

                    self.character_select_list.add_widget(char_box)
                    self.character_toggles[char_context.name] = checkbox
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
