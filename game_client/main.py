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

    from game_client import settings_manager

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
from views.load_game_screen import LoadGameScreen
from views.inventory_screen import InventoryScreen
from views.quest_log_screen import QuestLogScreen
from views.dialogue_screen import DialogueScreen
from views.shop_screen import ShopScreen
from views.settings_screen import SettingsScreen


# --- 6. THE MAIN APP CLASS (Unchanged from refactor) ---
class ShatterlandsClientApp(App):
    """
    The core Kivy application class for the Shatterlands Client.

    Manages the screen manager, global settings, and the application lifecycle.
    """
    game_settings = {}

    # Make settings and managers globally accessible via the app instance
    app_settings = {}
    # settings_manager will be assigned in main()
    # audio_manager will be assigned in Phase 4

    def build(self):
        """
        Builds the widget tree for the application.

        Sets the window size and title, initializes the ScreenManager,
        and adds all the application screens (views).

        Returns:
            ScreenManager: The root widget of the application.
        """
        Window.size = (1280, 720)
        self.title = "Shatterlands TTRPG Client"

        sm = ScreenManager()
        sm.add_widget(MainMenuScreen(name='main_menu'))
        sm.add_widget(GameSetupScreen(name='game_setup'))
        sm.add_widget(CharacterCreationScreen(name='character_creation'))
        sm.add_widget(LoadGameScreen(name='load_game'))
        sm.add_widget(MainInterfaceScreen(name='main_interface'))
        sm.add_widget(CombatScreen(name='combat_screen'))
        sm.add_widget(CharacterSheetScreen(name='character_sheet'))
        sm.add_widget(InventoryScreen(name='inventory'))
        sm.add_widget(QuestLogScreen(name='quest_log'))
        sm.add_widget(DialogueScreen(name='dialogue_screen'))
        sm.add_widget(ShopScreen(name='shop_screen'))

        sm.add_widget(SettingsScreen(name='settings'))

        sm.current = 'main_menu'
        return sm

# --- 7. ASYNC MAIN FUNCTION ---
async def main():
    """
    The asynchronous entry point for the application.

    Configures logging, initializes the backend monolith (database migrations,
    module registration), loads assets and settings, and launches the Kivy event loop.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
    logger = logging.getLogger("game_client")
    logger.info("--- Shatterlands Client Starting ---")

    app_instance = ShatterlandsClientApp()

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

        # --- Initialize Settings Manager (Synchronous) ---
        app_instance.app_settings = settings_manager.load_settings()
        logger.info("Settings manager initialized and settings loaded.")

    except Exception as e:
        logger.exception(f"FATAL: An error occurred during startup: {e}")
        sys.exit(1)


    # --- Run Kivy App (Asynchronous) ---
    logger.info("Starting Kivy application...")
    await app_instance.async_run(async_lib='asyncio')
    logger.info("Kivy application finished.")

# --- 8. RUN THE APP ---
if __name__ == '__main__':
    asyncio.run(main())
