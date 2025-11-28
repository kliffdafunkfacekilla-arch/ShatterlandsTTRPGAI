"""
The Load Game screen.
Lists all available save files and allows loading one.
"""
import logging
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.properties import ObjectProperty
from functools import partial
from kivy.uix.popup import Popup

# --- Direct Monolith Imports ---
try:
    from monolith.modules import save_manager
except ImportError as e:
    logging.error(f"LOAD_GAME: Failed to import save_manager: {e}")
    save_manager = None

class LoadGameScreen(Screen):
    save_list_container = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding='20dp', spacing='10dp')
        layout.add_widget(Label(text='Load Game', font_size='32sp', size_hint_y=0.15))

        scroll = ScrollView(size_hint_y=0.7)
        self.save_list_container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.save_list_container.bind(minimum_height=self.save_list_container.setter('height'))
        scroll.add_widget(self.save_list_container)
        layout.add_widget(scroll)

        back_btn = Button(text='Back to Menu', size_hint_y=0.1, height='44dp')
        back_btn.bind(on_release=lambda x: self.go_to_main_menu())
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def on_enter(self, *args):
        """Called when this screen is shown. Fetches the list of save games."""
        self.populate_save_list()

    def populate_save_list(self):
        """Populate list of save games from JSON files"""
        self.save_list_container.clear_widgets()
        if not save_manager:
            self.save_list_container.add_widget(Label(text="Error: Save module not loaded."))
            return

        try:
            saves = save_manager.scan_saves()
            
            if not saves:
                self.save_list_container.add_widget(Label(text="No save games found."))
                return

            for slot_name, save_file in saves.items():
                # Format display text
                save_time = save_file.save_time.strftime("%Y-%m-%d %H:%M")
                num_chars = len(save_file.data.characters)
                
                btn_text = f"{slot_name}\n({num_chars} characters - {save_time})"
                
                save_btn = Button(
                    text=btn_text,
                    size_hint_y=None,
                    height='60dp',
                    halign='center'
                )
                save_btn.bind(on_release=partial(self.load_selected_game, slot_name))
                self.save_list_container.add_widget(save_btn)

        except Exception as e:
            logging.exception(f"Failed to list save games: {e}")
            self.save_list_container.add_widget(Label(text="Error loading save list."))

    def load_selected_game(self, slot_name: str, *args):
        """Load game using orchestrator"""
        import asyncio
        
        logging.info(f"Attempting to load game: {slot_name}")
        if not save_manager:
            return

        try:
            app = App.get_running_app()
            
            # Call orchestrator to load game
            result = asyncio.run(app.orchestrator.load_game(slot_name))
            
            if not result.get("success"):
                raise Exception(result.get("error", "Unknown load error"))
            
            logging.info(f"Game loaded successfully: {slot_name}")
            
            # Navigate to main interface
            app.root.current = 'main_interface'

        except Exception as e:
            logging.exception(f"Failed to load game: {e}")

            # Show error popup
            content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
            content.add_widget(Label(text="Load Failed!", font_size='20sp'))
            content.add_widget(Label(text=str(e), font_size='14sp', size_hint_y=None))
            close_btn = Button(text="OK", size_hint_y=None, height='44dp')
            content.add_widget(close_btn)

            popup = Popup(title='Error', content=content, size_hint=(0.6, 0.4))
            close_btn.bind(on_release=popup.dismiss)
            popup.open()

    def go_to_main_menu(self):
        App.get_running_app().root.current = 'main_menu'