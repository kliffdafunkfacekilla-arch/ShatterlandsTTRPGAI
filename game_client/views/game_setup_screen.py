"""
The Game Setup screen.
Allows party selection, new character creation, and game settings.
This replaces the old 'game_setup_panel.py' and uses direct
monolith imports instead of API calls.
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.app import App
from kivy.properties import ObjectProperty, ListProperty
from typing import List
import logging

# --- Direct Monolith Imports ---
# We can do this because main.py already set up the sys.path
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
    party_spinner = ObjectProperty(None)
    character_names = ListProperty(['Loading characters...'])

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

        # This spinner will be populated by load_characters()
        self.party_spinner = Spinner(
            text='Select a Character',
            values=self.character_names,
            size_hint_y=None,
            height='44dp'
        )
        # Bind the values property so it updates when self.character_names changes
        self.bind(character_names=self.party_spinner.setter('values'))
        layout.add_widget(self.party_spinner)

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
        if self.character_names:
            self.party_spinner.text = self.character_names[0]

    def load_characters(self):
        """
        Opening the ttrpgai outline..txt file. Opening the AI-TTRPG/monolith/modules/character_pkg/crud.py file. Opening the AI-TTRPG/monolith/modules/character_pkg/services.py file.
        Fetches the character list directly from the database.
        This REPLACES the old requests.get() call.
        """
        if not CharSession or not char_crud or not char_services:
            self.character_names = ["Error: Monolith not loaded"]
            return
        char_names = ['No characters found']
        db = None
        try:
            db = CharSession()
            # 1. Call the CRUD function to get DB models
            db_chars = char_crud.list_characters(db)

            if db_chars:
                # 2. Convert models to the context dicts using the service
                char_contexts = [char_services.get_character_context(c) for c in db_chars]
                # 3. Get the names
                char_names = [c.name for c in char_contexts if c]
                if not char_names:
                    char_names = ['No characters found']

            self.character_names = char_names
        except Exception as e:
            logging.error(f"GAME_SETUP: Failed to load character list: {e}")
            self.character_names = [f'Error: Could not load characters']
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
        # We'll need to store this data in the App or a game_state module
        selected_char = self.party_spinner.text
        difficulty = self.difficulty_spinner.text

        if selected_char == 'No characters found' or 'Error' in selected_char:
            logging.warning("GAME_SETUP: Cannot start game, no valid character selected.")
            return

        logging.info(f"Starting game with {selected_char} at {difficulty} difficulty.")

        # Store settings in the app
        app = App.get_running_app()
        app.game_settings = {
            'selected_character_name': selected_char,
            'difficulty': difficulty
        }

        app.root.current = 'main_interface'
