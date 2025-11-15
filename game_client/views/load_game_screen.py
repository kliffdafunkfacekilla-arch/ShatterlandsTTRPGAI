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

# --- Direct Monolith Imports ---
try:
    from monolith.modules import save_api
except ImportError as e:
    logging.error(f"LOAD_GAME: Failed to import save_api: {e}")
    save_api = None

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
        self.save_list_container.clear_widgets()
        if not save_api:
            self.save_list_container.add_widget(Label(text="Error: Save module not loaded."))
            return

        try:
            saves = save_api.list_save_games()
            if not saves:
                self.save_list_container.add_widget(Label(text="No save games found."))
                return

            for save in saves:
                save_name = save.get('name', 'Unknown Save')
                char_name = save.get('char', 'Unknown Char')
                save_time = save.get('time', 'Unknown Time')

                btn_text = f"{save_name}\n(Character: {char_name} - Time: {save_time})"
                save_btn = Button(
                    text=btn_text,
                    size_hint_y=None,
                    height='60dp',
                    halign='center'
                )
                save_btn.bind(on_release=partial(self.load_selected_game, save_name))
                self.save_list_container.add_widget(save_btn)

        except Exception as e:
            logging.exception(f"Failed to list save games: {e}")
            self.save_list_container.add_widget(Label(text="Error loading save list."))

    def load_selected_game(self, slot_name: str, *args):
        """Calls the save_api to load the game and transitions to the interface."""
        logging.info(f"Attempting to load game: {slot_name}")
        if not save_api:
            return

        try:
            result = save_api.load_game(slot_name)
            if not result.get("success"):
                raise Exception(result.get("error", "Unknown load error"))

            app = App.get_running_app()

            # CRITICAL: We must set the active character name so the
            # main_interface_screen knows who to load.
            app.game_settings = {
                'selected_character_name': result.get('active_character_name'),
                'difficulty': 'Normal' # Placeholder, could store this in save
            }

            app.root.current = 'main_interface'

        except Exception as e:
            logging.exception(f"Failed to load game: {e}")
            # TODO: Show a popup to the user
            pass

    def go_to_main_menu(self):
        App.get_running_app().root.current = 'main_menu'
