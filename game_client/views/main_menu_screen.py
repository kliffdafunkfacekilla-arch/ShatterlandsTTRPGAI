"""
The Main Menu screen for the Shatterlands client.
"""
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.app import App
import logging

# --- Monolith Imports ---
try:
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal
except ImportError as e:
    logging.error(f"MainMenu: Failed to import monolith modules: {e}")
    char_services = None
    SessionLocal = None

# Use Kivy Language (KV) string for a clean layout.
MAIN_MENU_KV = """
<MainMenuScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: '50dp'
        spacing: '20dp'

        Label:
            text: 'Shatterlands'
            font_size: '48sp'
            size_hint_y: 0.4

        Button:
            text: 'New Game'
            font_size: '24sp'
            size_hint_y: 0.15 # Adjusted height
            on_release: root.start_new_game()

        Button:
            text: 'Load Game'
            font_size: '24sp'
            size_hint_y: 0.15 # Adjusted height
            disabled: False
            on_release: app.root.current = 'load_game'

        # --- ADDED THIS BUTTON ---
        Button:
            text: 'Settings'
            font_size: '24sp'
            size_hint_y: 0.15 # Adjusted height
            on_release:
                app.root.get_screen('settings').previous_screen = 'main_menu'
                app.root.current = 'settings'
        # --- END ADD ---

        Button:
            text: 'Quit'
            font_size: '24sp'
            size_hint_y: 0.15 # Adjusted height
            on_release: app.stop() # Quit the application
"""

# Load the KV string into Kivy's Builder
Builder.load_string(MAIN_MENU_KV)

class MainMenuScreen(Screen):
    """
    The main menu screen class. The UI is defined in the KV string above.
    """
    def start_new_game(self):
        """
        Checks if characters exist. If so, goes to game setup.
        If not, goes to character creation.
        """
        if not char_services or not SessionLocal:
            logging.error("Character services not available. Cannot start new game.")
            # Optionally, show a popup to the user
            return

        try:
            with SessionLocal() as db:
                characters = char_services.get_characters(db, skip=0, limit=1)
                if characters:
                    App.get_running_app().root.current = 'game_setup'
                else:
                    App.get_running_app().root.current = 'character_creation'
        except Exception as e:
            logging.exception(f"Error checking for existing characters: {e}")
            # Fallback to character creation if the check fails
            App.get_running_app().root.current = 'character_creation'