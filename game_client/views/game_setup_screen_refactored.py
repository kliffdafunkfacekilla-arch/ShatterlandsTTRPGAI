"""
Game Setup Screen - Refactored for Local Architecture

Simplified version that starts games using character JSON files
instead of database characters.
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.filechooser import FileChooserListView
from kivy.app import App
from kivy.factory import Factory
from kivy.clock import Clock
from pathlib import Path
import logging
import asyncio

# Import UI utilities
from game_client.ui_utils import show_loading, hide_loading, show_error, show_success

logger = logging.getLogger("game_client.game_setup")


class GameSetupScreen(Screen):
    """
    Simplified Game Setup Screen using character JSON files.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_char_files = []
        self.build_ui()
    
    def build_ui(self):
        # Root Layout
        root = Factory.DungeonBackground(orientation='vertical', padding='20dp', spacing='20dp')
        
        # Title
        title = Factory.DungeonLabel(
            text="New Game Setup",
            font_size='32sp',
            size_hint_y=None,
            height='60dp',
            bold=True,
            color=(0.9, 0.8, 0.6, 1)
        )
        root.add_widget(title)
        
        # Instructions
        instructions = Factory.ParchmentLabel(
            text="Select 2-4 character JSON files from the characters folder",
            size_hint_y=None,
            height='40dp',
            font_size='16sp'
        )
        root.add_widget(instructions)
        
        # File chooser for character JSON files
        file_chooser = FileChooserListView(
            path=str(Path.cwd() / "characters"),
            filters=["*.json"],
            multiselect=True
        )
        file_chooser.bind(selection=self.on_file_selection)
        root.add_widget(file_chooser)
        
        # Selected files display
        self.selected_label = Factory.ParchmentLabel(
            text="Selected: 0 characters",
            size_hint_y=None,
            height='40dp',
            font_size='14sp'
        )
        root.add_widget(self.selected_label)
        
        # Bottom buttons
        button_box = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height='60dp',
            spacing='20dp'
        )
        
        back_btn = Factory.DungeonButton(text="Back")
        back_btn.bind(on_release=self.go_to_main_menu)
        
        start_btn = Factory.DungeonButton(text="Start Adventure")
        start_btn.bind(on_release=self.start_game)
        
        button_box.add_widget(back_btn)
        button_box.add_widget(start_btn)
        root.add_widget(button_box)
        
        self.add_widget(root)
    
    def on_file_selection(self, instance, selection):
        """Called when file selection changes"""
        self.selected_char_files = selection
        count = len(selection)
        self.selected_label.text = f"Selected: {count} character{'s' if count != 1 else ''}"
        
        if count > 0:
            files_str = "\n".join([Path(f).name for f in selection[:3]])
            if count > 3:
                files_str += f"\n... and {count - 3} more"
            self.selected_label.text += f"\n{files_str}"
    
    def go_to_main_menu(self, instance):
        """Navigate back to main menu"""
        self.manager.current = 'main_menu'
    
    def start_game(self, instance):
        """Start game with selected character files"""
        # Validation
        if not self.selected_char_files:
            show_error(
                "No Characters Selected",
                "Please select at least 2 character files to start the game."
            )
            return
        
        if len(self.selected_char_files) < 2:
            show_error(
                "Not Enough Characters",
                f"You selected {len(self.selected_char_files)} character(s).\nPlease select at least 2 characters for hotseat play."
            )
            return
        
        if len(self.selected_char_files) > 4:
            show_error(
                "Too Many Characters",
                f"You selected {len(self.selected_char_files)} characters.\nMaximum 4 characters allowed."
            )
            return
        
        # Show loading
        show_loading("Starting new game...")
        
        # Start game asynchronously
        def do_start_game(dt):
            app = App.get_running_app()
            
            logger.info(f"Starting game with {len(self.selected_char_files)} characters")
            
            try:
                result = asyncio.run(
                    app.orchestrator.start_new_game(self.selected_char_files)
                )
                
                hide_loading()
                
                if result["success"]:
                    logger.info(f"Game started successfully: {result}")
                    
                    # Show success briefly before navigating
                    show_success("Game started successfully!")
                    
                    # Navigate after brief delay
                    Clock.schedule_once(
                        lambda dt: setattr(self.manager, 'current', 'main_interface'),
                        0.5
                    )
                else:
                    error_msg = result.get('error', 'Unknown error occurred')
                    logger.error(f"Failed to start game: {error_msg}")
                    show_error("Failed to Start Game", error_msg)
                    
            except Exception as e:
                hide_loading()
                logger.exception(f"Error starting game: {e}")
                show_error(
                    "Error Starting Game",
                    f"An unexpected error occurred:\n{str(e)}\n\nCheck console for details."
                )
        
        # Schedule on next frame to allow loading dialog to display
        Clock.schedule_once(do_start_game, 0.1)
