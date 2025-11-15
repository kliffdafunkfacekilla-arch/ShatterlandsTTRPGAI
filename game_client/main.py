import kivy
kivy.require('2.1.0')

import os
import sys
import logging
from pathlib import Path
import asyncio

# --- 1. SET SYS.PATH ---
APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
MONOLITH_PATH = APP_ROOT / "AI-TTRPG"
if str(MONOLITH_PATH) not in sys.path:
    sys.path.insert(0, str(MONOLITH_PATH))

# --- 2. DELAYED MONOLITH & ASSET IMPORTS ---
# Initialization is moved into the async main() function.
try:
    from monolith.start_monolith import _run_migrations_for_module, ROOT
    from monolith.orchestrator import get_orchestrator
    from monolith.modules import register_all
    from game_client import asset_loader
except ImportError as e:
    # We can't log here yet, as logging isn't configured.
    print(f"FATAL: A critical module could not be imported. Check paths and dependencies.")
    print(f"Error: {e}")
    sys.exit(1)

# --- 3. KIVY APPLICATION IMPORTS ---
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window

# --- 4. VIEW IMPORTS ---
from views.main_menu_screen import MainMenuScreen
from views.game_setup_screen import GameSetupScreen
from views.character_creation_screen import CharacterCreationScreen
from views.main_interface_screen import MainInterfaceScreen
from views.combat_screen import CombatScreen
from views.character_sheet_screen import CharacterSheetScreen
from views.load_game_screen import LoadGameScreen # <-- ADD THIS IMPORT
from views.inventory_screen import InventoryScreen
from views.quest_log_screen import QuestLogScreen

# --- 6. THE MAIN APP CLASS (Unchanged from refactor) ---
class ShatterlandsClientApp(App):
    game_settings = {}

    def build(self):
        Window.size = (1280, 720)
        self.title = "Shatterlands TTRPG Client"

        sm = ScreenManager()
        sm.add_widget(MainMenuScreen(name='main_menu'))
        sm.add_widget(GameSetupScreen(name='game_setup'))
        sm.add_widget(CharacterCreationScreen(name='character_creation'))
        sm.add_widget(LoadGameScreen(name='load_game')) # <-- ADD THIS LINE
        sm.add_widget(MainInterfaceScreen(name='main_interface'))
        sm.add_widget(CombatScreen(name='combat_screen'))
        sm.add_widget(CharacterSheetScreen(name='character_sheet'))
        sm.add_widget(InventoryScreen(name='inventory'))
        sm.add_widget(QuestLogScreen(name='quest_log'))

        sm.current = 'main_menu'
        return sm

# --- 7. ASYNC MAIN FUNCTION ---
async def main():
    """
    Configures logging, runs monolith setup, and then starts the Kivy app.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
    logger = logging.getLogger("game_client")
    logger.info("--- Shatterlands Client Starting ---")

    try:
        # --- Run Monolith Startup (Synchronous parts) ---
        logger.info("Running database migrations...")
        _run_migrations_for_module("character", ROOT, "auto")
        _run_migrations_for_module("world", ROOT, "auto")
        _run_migrations_for_module("story", ROOT, "auto")
        logger.info("Database migrations complete.")

        logger.info("Registering all monolith modules...")
        register_all(get_orchestrator())
        logger.info("Monolith modules registered.")

        # --- Initialize Asset Loader (Synchronous) ---
        asset_loader.initialize_assets()
        logger.info("Asset loader initialized.")

    except Exception as e:
        logger.exception(f"FATAL: An error occurred during startup: {e}")
        sys.exit(1)


    # --- Run Kivy App (Asynchronous) ---
    logger.info("Starting Kivy application...")
    app = ShatterlandsClientApp()
    await app.async_run(async_lib='asyncio')
    logger.info("Kivy application finished.")

# --- 8. RUN THE APP ---
if __name__ == '__main__':
    asyncio.run(main())
