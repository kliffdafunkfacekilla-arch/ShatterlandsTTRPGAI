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

# --- 2. MONOLITH IMPORTS ---
try:
    from monolith.orchestrator import Orchestrator
    from monolith.event_bus import get_event_bus
    from monolith.modules.rules_pkg.data_loader_enhanced import load_and_validate_all
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
from kivy.resources import resource_add_path

# Ensure Kivy can find assets
resource_add_path(str(APP_ROOT))

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
    
    # Global Context for Active Character
    active_character_context = ObjectProperty(None, force_dispatch=True)
    
    # Core game components (initialized in initialize_backend)
    orchestrator = None
    event_bus = None

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
        
        # Bind keyboard
        Window.bind(on_keyboard=self.on_keyboard)
        
        return self.sm

    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        """Global keyboard handler."""
        if key == 27: # ESC
            current = self.sm.current
            # If in a sub-menu of main interface, go back to main interface
            if current in ['character_sheet', 'inventory', 'quest_log', 'dialogue_screen', 'shop_screen', 'settings']:
                self.sm.current = 'main_interface'
                return True
            # If in main interface, maybe open pause menu (not implemented yet) or settings
            elif current == 'main_interface':
                self.sm.current = 'settings'
                return True
            # If in settings, go back to previous
            elif current == 'settings':
                # Settings screen handles its own back logic usually, but we can force it
                screen = self.sm.get_screen('settings')
                if hasattr(screen, 'go_back'):
                    screen.go_back()
                else:
                    self.sm.current = 'main_menu'
                return True
        return False

    def on_stop(self):
        """Called when the application is closing."""
        logging.info("Application stopping...")
        try:
            if self.orchestrator:
                # Clean shutdown of AI manager if present
                from monolith.modules.ai_dm_pkg.llm_handler_enhanced import get_ai_manager
                try:
                    get_ai_manager().shutdown()
                except:
                    pass
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")

    def initialize_backend(self):
        """
        Initialize the local game engine in a background thread.
        Updates the LoadingScreen via Clock.schedule_once.
        """
        try:
            # Create async event loop for this thread
            import asyncio
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            self.update_loading_status("Initializing Engine...", 10)
            
            # Initialize Event Bus
            self.update_loading_status("Setting up Event Bus...", 20)
            self.event_bus = get_event_bus()
            
            # Initialize Orchestrator
            self.update_loading_status("Initializing Orchestrator...", 30)
            self.orchestrator = Orchestrator()
            
            # Load and validate game rules (abilities, talents, etc.)
            self.update_loading_status("Loading Game Rules...", 50)
            try:
                rules_summary = load_and_validate_all()
                logger.info(f"Rules loaded: {rules_summary}")
            except Exception as e:
                logger.error(f"Failed to load rules: {e}")
                self.update_loading_status("ERROR: Failed to load game rules", 50)
                time.sleep(2)
                sys.exit(1)
            
            # Initialize engine (loads rules into orchestrator)
            self.update_loading_status("Initializing Game Engine...", 60)
            self.loop.run_until_complete(self.orchestrator.initialize_engine())
            
            # Asset Loading
            self.update_loading_status("Loading Assets...", 80)
            asset_loader.initialize_assets()
            
            # Settings Loading
            self.update_loading_status("Loading Settings...", 90)
            self.app_settings = settings_manager.load_settings()
            self.game_settings = {"session_start": time.time()} # Initialize session settings
            
            # Complete
            self.update_loading_status("Initialization Complete!", 100)
            time.sleep(0.5)
            
            # Initialize screens on main thread and switch
            Clock.schedule_once(self.initialize_screens_and_switch, 0)
            
            # Keep the loop running for async operations (Event Bus, AI DM)
            self.loop.run_forever()
            
        except Exception as e:
            logger.exception(f"FATAL: An error occurred during startup: {e}")
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
    try:
        ShatterlandsClientApp().run()
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}", exc_info=True)
        print(f"CRITICAL ERROR: {e}")
        # Try to show a native error dialog since Kivy might be dead
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Critical Error:\n{e}", "Shatterlands Crash", 0x10)
        except:
            pass
        sys.exit(1)
