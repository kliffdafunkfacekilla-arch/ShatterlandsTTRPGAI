"""
The Main Menu screen for the Shatterlands client.
"""
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.app import App

# Use Kivy Language (KV) string for a clean layout.
MAIN_MENU_KV = """
<MainMenuScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: '50dp'
        spacing: '20dp'

        Label:
            text: 'Shatterlands'
            font_size: '48sp'
            size_hint_y: 0.4

        Button:
            text: 'New Run'
            font_size: '24sp'
            size_hint_y: 0.15
            on_release: app.root.current = 'game_setup'

        Button:
            text: 'Character Creator'
            font_size: '24sp'
            size_hint_y: 0.15
            on_release: app.root.current = 'character_creation'

        Button:
            text: 'Load Game'
            font_size: '24sp'
            size_hint_y: 0.15
            disabled: False
            on_release: app.root.current = 'load_game'

        Button:
            text: 'Settings'
            font_size: '24sp'
            size_hint_y: 0.15
            on_release:
                app.root.get_screen('settings').previous_screen = 'main_menu'
                app.root.current = 'settings'

        Button:
            text: 'Quit'
            font_size: '24sp'
            size_hint_y: 0.15
            on_release: app.stop()
"""

# Load the KV string into Kivy's Builder
Builder.load_string(MAIN_MENU_KV)

class MainMenuScreen(Screen):
    """
    The main menu screen class. The UI is defined in the KV string above.
    """
    pass