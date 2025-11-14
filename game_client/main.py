import logging
import sys
from pathlib import Path

# --- 1. SET SYS.PATH TO FIND THE MONOLITH ---
# This finds the parent directory (ShatterlandsTTRPGAI-c98c20e4...)
# and then appends the 'AI-TTRPG' folder to the path.
APP_ROOT = Path(__file__).resolve().parent.parent
MONOLITH_PATH = APP_ROOT / "AI-TTRPG"
if str(MONOLITH_PATH) not in sys.path:
    sys.path.insert(0, str(MONOLITH_PATH))

# --- 2. IMPORT AND INITIALIZE THE MONOLITH ---
try:
    from monolith.start_monolith import _run_migrations_for_module, ROOT, register_all, get_orchestrator
except ImportError as e:
    print(f"FATAL: Could not import from 'monolith'. Is the AI-TTRPG directory in the path?")
    print(f"Attempted to add '{MONOLITH_PATH}' to the path.")
    print(f"Error: {e}")
    sys.exit(1)

# --- 2b. IMPORT AND INITIALIZE ASSETS ---
try:
    from asset_loader import initialize_assets
except ImportError as e:
    print(f"FATAL: Could not import asset_loader.py. Is it in the 'game_client' folder?")
    print(f"Error: {e}")
    sys.exit(1)

# --- 3. CONFIGURE LOGGING & RUN MIGRATIONS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
logger = logging.getLogger("game_client")

logger.info("--- Shatterlands Client Starting ---")
# Run monolith init
logger.info("Running database migrations...")
_run_migrations_for_module("character", ROOT, "auto")
_run_migrations_for_module("world", ROOT, "auto")
_run_migrations_for_module("story", ROOT, "auto")
logger.info("Database migrations complete.")

logger.info("Registering all monolith modules...")
register_all(get_orchestrator())
logger.info("Monolith modules registered and data loaded.")

# --- ADD THIS CALL ---
logger.info("Initializing game assets...")
initialize_assets()
logger.info("Game assets initialized.")
# --- END ADD ---

# --- 4. KIVY APPLICATION IMPORTS ---
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from views.character_creation_screen import CharacterCreationScreen

class GameSetupScreen(Screen):
    pass

class ShatterlandsApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(GameSetupScreen(name='game_setup'))
        sm.add_widget(CharacterCreationScreen(name='character_creation'))
        sm.current = 'character_creation'
        return sm

if __name__ == '__main__':
    ShatterlandsApp().run()
