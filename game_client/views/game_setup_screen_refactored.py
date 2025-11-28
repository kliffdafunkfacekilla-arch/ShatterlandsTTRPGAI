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
from pathlib import Path
import logging
import asyncio

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
        if not self.selected_char_files:
            logger.warning("No characters selected")
            # TODO: Show error popup
            return
        
        if len(self.selected_char_files) < 2:
            logger.warning("Need at least 2 characters")
            # TODO: Show error popup  
            return
        
        if len(self.selected_char_files) > 4:
            logger.warning("Maximum 4 characters allowed")
            # TODO: Show error popup
            return
        
        app = App.get_running_app()
        
        logger.info(f"Starting game with {len(self.selected_char_files)} characters")
        
        # Call orchestrator to start game
        try:
            result = asyncio.run(
                app.orchestrator.start_new_game(self.selected_char_files)
            )
            
            if result["success"]:
                logger.info(f"Game started successfully: {result}")
                
                # Navigate to main interface
                self.manager.current = 'main_interface'
            else:
                logger.error(f"Failed to start game: {result.get('error')}")
                # TODO: Show error popup
                
        except Exception as e:
            logger.exception(f"Error starting game: {e}")
            # TODO: Show error popup
