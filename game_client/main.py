import kivy
kivy.require('2.1.0')

import os
import sys
import logging
import asyncio
from pathlib import Path

# --- 1. SET SYS.PATH ---
APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

MONOLITH_PATH = APP_ROOT / "AI-TTRPG"
if str(MONOLITH_PATH) not in sys.path:
    sys.path.insert(0, str(MONOLITH_PATH))

# --- 2. KIVY IMPORTS ---
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty

# --- 3. VIEW IMPORTS ---
# Delayed imports to avoid circular dependencies or premature loading
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

# --- 4. MONOLITH IMPORTS ---
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

# --- 5. LOADING SCREEN ---
Builder.load_string("""
<LoadingScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: '50dp'
        spacing: '20dp'
        
        Label:
            text: 'Shatterlands TTRPG'
            font_size: '48sp'
            halign: 'center'
            valign: 'middle'
            size_hint_y: 0.6
            
        Label:
            text: root.loading_text
            font_size: '24sp'
            halign: 'center'
            valign: 'middle'
            size_hint_y: 0.2
            
        ProgressBar:
            id: progress
            max: 100
            value: 0 # Indeterminate for now or update manually
            size_hint_y: 0.1
            size_hint_x: 0.8
            pos_hint: {'center_x': 0.5}
""")

class LoadingScreen(Screen):
    loading_text = StringProperty("Initializing...")

# --- 6. MAIN APP CLASS ---
class ShatterlandsClientApp(App):
    """
    The core Kivy application class for the Shatterlands Client.
    Manages the screen manager, global settings, and the application lifecycle.
    """
    app_settings = {}

    def build(self):
        """Builds the widget tree for the application."""
        Window.size = (1280, 720)
        self.title = "Shatterlands TTRPG Client"

        sm = ScreenManager()
        sm.add_widget(LoadingScreen(name='loading'))
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

        sm.current = 'loading'
        return sm

    def on_start(self):
        """Called when the application starts. Triggers async initialization."""
        asyncio.create_task(self.initialize_app())

    async def initialize_app(self):
        """Performs backend initialization tasks asynchronously."""
        logger = logging.getLogger("game_client")
        loading_screen = self.root.get_screen('loading')
        
        try:
            # 1. Database Migrations (Blocking I/O -> Thread)
            loading_screen.loading_text = "Checking Database..."
            logger.info("Running database migrations...")
            
            # Run migrations for each module in a thread to avoid blocking UI
            await asyncio.to_thread(_run_migrations_for_module, "character", ROOT, "auto")
            await asyncio.to_thread(_run_migrations_for_module, "world", ROOT, "auto")
            await asyncio.to_thread(_run_migrations_for_module, "story", ROOT, "auto")
            logger.info("Database migrations complete.")

            # 2. Register Modules
            loading_screen.loading_text = "Loading Game Modules..."
            logger.info("Registering all monolith modules...")
            register_all(get_orchestrator())
            logger.info("Monolith modules registered.")

            # 3. Load Assets
            loading_screen.loading_text = "Loading Assets..."
            logger.info("Initializing asset loader...")
            # asset_loader.initialize_assets might be blocking, run in thread if needed
            # Assuming it's fast enough or we can thread it
            await asyncio.to_thread(asset_loader.initialize_assets)
            logger.info("Asset loader initialized.")

            # 4. Load Settings
            loading_screen.loading_text = "Loading Settings..."
            logger.info("Loading settings...")
            self.app_settings = settings_manager.load_settings()
            logger.info("Settings loaded.")

            # 5. Complete
            loading_screen.loading_text = "Ready!"
            await asyncio.sleep(0.5) # Brief pause to show "Ready!"
            
            # Switch to Main Menu
            self.root.current = 'main_menu'

        except Exception as e:
            logger.exception(f"FATAL: An error occurred during startup: {e}")
            loading_screen.loading_text = f"Error: {e}"
            # In a real app, we might want to show a popup or keep the error visible
            # For now, we just log it and stay on the loading screen with the error message

# --- 7. MAIN ENTRY POINT ---
async def main():
    """The asynchronous entry point for the application."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
    logger = logging.getLogger("game_client")
    logger.info("--- Shatterlands Client Starting ---")

    app_instance = ShatterlandsClientApp()
    await app_instance.async_run(async_lib='asyncio')

if __name__ == '__main__':
    asyncio.run(main())
