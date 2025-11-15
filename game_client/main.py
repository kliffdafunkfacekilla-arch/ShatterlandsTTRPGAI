import kivy
kivy.require('2.1.0')

import os
import sys
import logging
from pathlib import Path

# --- 1. SET SYS.PATH (Unchanged) ---
APP_ROOT = Path(__file__).resolve().parent.parent
MONOLITH_PATH = APP_ROOT / "AI-TTRPG"
if str(MONOLITH_PATH) not in sys.path:
    sys.path.insert(0, str(MONOLITH_PATH))

# --- 2. IMPORT AND INITIALIZE THE MONOLITH (Unchanged) ---
try:
    from monolith.start_monolith import _run_migrations_for_module, ROOT
    from monolith.orchestrator import get_orchestrator
    from monolith.modules import register_all
except ImportError as e:
    print(f"FATAL: Could not import monolith modules.")
    print(f"Attempted to load from: {MONOLITH_PATH}")
    print(f"Error: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
logger = logging.getLogger("game_client")
logger.info("--- Shatterlands Client Starting ---")
logger.info("Running database migrations...")
_run_migrations_for_module("character", ROOT, "auto")
_run_migrations_for_module("world", ROOT, "auto")
_run_migrations_for_module("story", ROOT, "auto")
logger.info("Database migrations complete.")
logger.info("Registering all monolith modules...")
register_all(get_orchestrator())
logger.info("Monolith modules registered and data loaded.")

# --- 3. KIVY APPLICATION IMPORTS ---
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window

# --- 4. IMPORT OUR VIEW FILES ---
from views.main_menu_screen import MainMenuScreen
from views.game_setup_screen import GameSetupScreen
from views.character_creation_screen import CharacterCreationScreen
# --- IMPORT THE NEW SCREEN ---
from views.main_interface_screen import MainInterfaceScreen

# --- 5. INITIALIZE ASSET LOADER ---
# (Must be after monolith register so data is loaded)
try:
    from game_client import asset_loader
    asset_loader.initialize_assets()
    logger.info("Asset loader initialized.")
except Exception as e:
    logger.exception(f"FATAL: Could not initialize asset_loader: {e}")
    sys.exit(1)

# --- 6. THE MAIN APP CLASS (Updated) ---
class ShatterlandsClientApp(App):

    game_settings = {} # Stores settings from GameSetupScreen

    def build(self):
        Window.size = (1280, 720)
        self.title = "Shatterlands TTRPG Client"

        sm = ScreenManager()
        sm.add_widget(MainMenuScreen(name='main_menu'))
        sm.add_widget(GameSetupScreen(name='game_setup'))
        sm.add_widget(CharacterCreationScreen(name='character_creation'))

        # --- USE THE NEW, REAL SCREEN ---
        sm.add_widget(MainInterfaceScreen(name='main_interface'))

        sm.current = 'main_menu'
        return sm

# --- 7. RUN THE APP (Unchanged) ---
if __name__ == '__main__':
    ShatterlandsClientApp().run()
