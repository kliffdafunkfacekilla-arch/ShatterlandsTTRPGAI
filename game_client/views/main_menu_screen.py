"""
The Main Menu screen for the Shatterlands client.
"""
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen

# Use Kivy Language (KV) string for a clean layout.
# This is the same layout from main.py.
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
            text: 'New Game'
            font_size: '24sp'
            size_hint_y: 0.15 # Adjusted height
            on_release: app.root.current = 'game_setup' # Change screen

        Button:
            text: 'Load Game'
            font_size: '24sp'
            size_hint_y: 0.15 # Adjusted height
            disabled: False
            on_release: app.root.current = 'load_game'

        # --- ADDED THIS BUTTON ---
        Button:
            text: 'Settings'
            font_size: '24sp'
            size_hint_y: 0.15 # Adjusted height
            on_release:
                app.root.get_screen('settings').previous_screen = 'main_menu'
                app.root.current = 'settings'
        # --- END ADD ---

        Button:
            text: 'Quit'
            font_size: '24sp'
            size_hint_y: 0.15 # Adjusted height
            on_release: app.stop() # Quit the application
"""

# Load the KV string into Kivy's Builder
Builder.load_string(MAIN_MENU_KV)

class MainMenuScreen(Screen):
    """
    The main menu screen class. The UI is defined in the KV string above.
    """
    pass
