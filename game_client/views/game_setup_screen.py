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
        
        # Main Content Area (Horizontal split)
        content = BoxLayout(orientation='horizontal', spacing='20dp')
        
        # Left: File Chooser
        left_panel = BoxLayout(orientation='vertical', spacing='10dp', size_hint_x=0.5)
        left_panel.add_widget(Factory.ParchmentLabel(text="Available Characters", size_hint_y=None, height='30dp', bold=True))
        
        self.file_chooser = FileChooserListView(
            path=str(Path.cwd() / "characters"),
            filters=["*.json"],
            multiselect=False # Changed to single select for explicit adding
        )
        left_panel.add_widget(self.file_chooser)
        
        add_btn = Factory.DungeonButton(text="Add to Party ->", size_hint_y=None, height='44dp')
        add_btn.bind(on_release=self.add_selected_character)
        left_panel.add_widget(add_btn)
        
        content.add_widget(left_panel)
        
        # Right: Party List
        right_panel = BoxLayout(orientation='vertical', spacing='10dp', size_hint_x=0.5)
        right_panel.add_widget(Factory.ParchmentLabel(text="Current Party (2-4)", size_hint_y=None, height='30dp', bold=True))
        
        self.party_container = BoxLayout(orientation='vertical', spacing='5dp', size_hint_y=None)
        self.party_container.bind(minimum_height=self.party_container.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.party_container)
        right_panel.add_widget(scroll)
        
        # Clear Button
        clear_btn = Factory.DungeonButton(text="Clear Party", size_hint_y=None, height='44dp')
        clear_btn.bind(on_release=self.clear_party)
        right_panel.add_widget(clear_btn)
        
        content.add_widget(right_panel)
        root.add_widget(content)
        
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
    
    def add_selected_character(self, instance):
        """Add the currently selected file to the party list."""
        if not self.file_chooser.selection:
            return
            
        file_path = self.file_chooser.selection[0]
        
        # Check if already added
        if file_path in self.selected_char_files:
            show_error("Already Added", "This character is already in the party.")
            return
            
        if len(self.selected_char_files) >= 4:
            show_error("Party Full", "Maximum 4 party members allowed.")
            return
            
        self.selected_char_files.append(file_path)
        self.refresh_party_list()
        
    def remove_character(self, file_path):
        """Remove a character from the party list."""
        if file_path in self.selected_char_files:
            self.selected_char_files.remove(file_path)
            self.refresh_party_list()
            
    def clear_party(self, instance):
        self.selected_char_files = []
        self.refresh_party_list()
        
    def refresh_party_list(self):
        """Rebuild the party list UI."""
        self.party_container.clear_widgets()
        
        for file_path in self.selected_char_files:
            name = Path(file_path).stem
            
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp', spacing='5dp')
            lbl = Label(text=name, color=(0,0,0,1), size_hint_x=0.7, halign='left', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            
            rem_btn = Button(text="X", size_hint_x=0.3, background_color=(0.8, 0.2, 0.2, 1))
            rem_btn.bind(on_release=lambda x, fp=file_path: self.remove_character(fp))
            
            row.add_widget(lbl)
            row.add_widget(rem_btn)
            self.party_container.add_widget(row)

    def on_file_selection(self, instance, selection):
        pass # No longer needed for label update, handled by add button

    def go_to_main_menu(self, instance):
        """Navigate back to main menu"""
        self.manager.current = 'main_menu'
    
    def start_game(self, instance):
        """Start game with selected character files"""
        # Validation
        if len(self.selected_char_files) < 2:
            show_error(
                "Not Enough Characters",
                f"You have {len(self.selected_char_files)} character(s) in the party.\nPlease add at least 2 characters for hotseat play."
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
