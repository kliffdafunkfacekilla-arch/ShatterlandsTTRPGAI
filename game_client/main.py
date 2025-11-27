import kivy
kivy.require('2.1.0')

import os
import sys
import logging
from pathlib import Path
import threading
import time

# --- 1. SET SYS.PATH ---
APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

MONOLITH_PATH = APP_ROOT / "AI-TTRPG"
if str(MONOLITH_PATH) not in sys.path:
    sys.path.insert(0, str(MONOLITH_PATH))

# --- 2. DELAYED MONOLITH & ASSET IMPORTS ---
try:
    from monolith.start_monolith import _run_migrations_for_module, ROOT
    from monolith.orchestrator import get_orchestrator
    from monolith.modules import register_all
    from game_client import asset_loader
    from game_client import settings_manager
except ImportError as e:
    print(f"FATAL: A critical module could not be imported. Check paths and dependencies.")
    print(f"Error: {e}")
    sys.exit(1)

# --- 3. KIVY APPLICATION IMPORTS ---
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import ObjectProperty
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder

# Load Theme
Builder.load_file(str(Path(__file__).parent / "views" / "theme.kv"))

# --- 4. VIEW IMPORTS ---
from views.loading_screen import LoadingScreen
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

# --- 5. LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
logger = logging.getLogger("game_client")

# --- 6. THE MAIN APP CLASS ---
class ShatterlandsClientApp(App):
    """
    The core Kivy application class for the Shatterlands Client.
    Manages the screen manager, global settings, and the application lifecycle.
    """
    game_settings = {}
    app_settings = {}
    
    # Global Context for Active Character (Section 2.1)
    active_character_context = ObjectProperty(None, force_dispatch=True)

    def build(self):
        """
        Builds the widget tree for the application.
        """
        Window.size = (1280, 720)
        self.title = "Shatterlands TTRPG Client"

        self.sm = ScreenManager()
        
        # Add Loading Screen first
        self.loading_screen = LoadingScreen(name='loading_screen')
        self.sm.add_widget(self.loading_screen)
        
        # Other screens will be added after backend initialization to prevent DB locks

        self.sm.current = 'loading_screen'
        
        # Start backend initialization in a separate thread
        threading.Thread(target=self.initialize_backend, daemon=True).start()
        
        return self.sm

    def on_stop(self):
        """Called when the application is closing."""
        logging.info("Application stopping...")
        try:
            from monolith.orchestrator import get_orchestrator
            get_orchestrator().shutdown()
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")

    def initialize_backend(self):
        """
        Runs database migrations and module registration in a background thread.
        Updates the LoadingScreen via Clock.schedule_once.
        """
        try:
            # Create a new event loop for this thread
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            self.update_loading_status("Initializing Logging...", 10)
            
            # Database Migrations
            self.update_loading_status("Running Database Migrations...", 20)
            _run_migrations_for_module("character", ROOT, "auto")
            _run_migrations_for_module("world", ROOT, "auto")
            _run_migrations_for_module("story", ROOT, "auto")
            
            # Module Registration
            self.update_loading_status("Registering Modules...", 50)
            # register_all uses asyncio.create_task, so it needs a loop
            register_all(get_orchestrator())
            
            # Asset Loading
            self.update_loading_status("Loading Assets...", 70)
            asset_loader.initialize_assets()
            
            # Settings Loading
            self.update_loading_status("Loading Settings...", 90)
            self.app_settings = settings_manager.load_settings()
            
            # Complete
            self.update_loading_status("Initialization Complete!", 100)
            time.sleep(0.5) # Brief pause to show 100%
            
            # Initialize screens on main thread and switch
            Clock.schedule_once(self.initialize_screens_and_switch, 0)
            
            # Keep the loop running for the event bus
            loop.run_forever()
            
        except Exception as e:
            logger.exception(f"FATAL: An error occurred during startup: {e}")
            # In a real app, we might show an error screen here
            sys.exit(1)

    def initialize_screens_and_switch(self, dt):
        """Initializes the rest of the application screens and switches to main menu."""
        # Add other screens now that backend is ready
        self.sm.add_widget(MainMenuScreen(name='main_menu'))
        self.sm.add_widget(GameSetupScreen(name='game_setup'))
        self.sm.add_widget(CharacterCreationScreen(name='character_creation'))
        self.sm.add_widget(LoadGameScreen(name='load_game'))
        self.sm.add_widget(MainInterfaceScreen(name='main_interface'))
        self.sm.add_widget(CombatScreen(name='combat_screen'))
        self.sm.add_widget(CharacterSheetScreen(name='character_sheet'))
        self.sm.add_widget(InventoryScreen(name='inventory'))
        self.sm.add_widget(QuestLogScreen(name='quest_log'))
        self.sm.add_widget(DialogueScreen(name='dialogue_screen'))
        self.sm.add_widget(ShopScreen(name='shop_screen'))
        self.sm.add_widget(SettingsScreen(name='settings'))
        
        self.sm.current = 'main_menu'

    def update_loading_status(self, message, progress):
        """Helper to update loading screen on main thread"""
        Clock.schedule_once(lambda dt: self.loading_screen.update_status(message, progress), 0)

    def show_error(self, title, message):
        """Displays a generic error popup."""
        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
        content.add_widget(Label(text=message, text_size=(380, None), halign='center', valign='middle'))
        close_btn = Button(text='Close', size_hint_y=None, height='44dp')
        content.add_widget(close_btn)
        
        popup = Popup(title=title, content=content, size_hint=(None, None), size=('400dp', '200dp'), auto_dismiss=False)
        close_btn.bind(on_release=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    ShatterlandsClientApp().run()
