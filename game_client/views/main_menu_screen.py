"""
The Main Menu screen for the Shatterlands client.
"""
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.app import App

# Use Kivy Language (KV) string for a clean layout.
MAIN_MENU_KV = """
<MainMenuScreen>:
    DungeonBackground:
        orientation: 'vertical'
        padding: '50dp'
        spacing: '20dp'

        DungeonLabel:
            text: 'Shatterlands'
            font_size: '64sp'
            size_hint_y: 0.4
            color: 0.9, 0.8, 0.6, 1
            bold: True

        DungeonButton:
            text: 'New Game'
            font_size: '24sp'
            size_hint_y: 0.15
            on_release: app.root.current = 'game_setup'

        DungeonButton:
            text: 'Load Game'
            font_size: '24sp'
            size_hint_y: 0.15
            disabled: False
            on_release: app.root.current = 'load_game'

        DungeonButton:
            text: 'Settings'
            font_size: '24sp'
            size_hint_y: 0.15
            on_release: app.root.current = 'settings'

        DungeonButton:
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