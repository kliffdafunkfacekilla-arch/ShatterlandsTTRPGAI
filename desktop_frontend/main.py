
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

from ui_panels import (
    CharacterSheetPanel,
    InventoryPanel,
    MapPanel,
    NarrationPanel,
    SystemLogPanel,
    HUDPanel,
    ControlPanel
)
from ui_panels import LorePanel
from character_creation_panel import CharacterCreationPanel
from game_setup_panel import GameSetupPanel
from kivy.uix.screenmanager import ScreenManager, Screen



# Main menu screen

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(Label(text='Welcome to Shatterlands TTRPG!', font_size=32))
        setup_btn = Button(text='New Game', size_hint_y=0.2)
        create_btn = Button(text='Create Character', size_hint_y=0.2)
        layout.add_widget(setup_btn)
        layout.add_widget(create_btn)
        self.add_widget(layout)
        setup_btn.bind(on_release=self.open_game_setup)
        create_btn.bind(on_release=self.create_character)

    def open_game_setup(self, instance):
        self.manager.current = 'game_setup'

    def create_character(self, instance):
        self.manager.current = 'character_creation'
# MainInterface as before
class GameSetupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.panel = GameSetupPanel()
        self.add_widget(self.panel)

# Main game interface screen
class MainInterfaceScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interface = MainInterface()
        self.add_widget(self.interface)

# Character creation screen
class CharacterCreationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.panel = CharacterCreationPanel()
        self.add_widget(self.panel)

# MainInterface as before
class MainInterface(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
    # Example layout: HUD, Map, Lore, Character, Inventory, etc.
    hud = HUDPanel()
    map_panel = MapPanel()
    lore_panel = LorePanel()
    char_panel = CharacterSheetPanel()
    inv_panel = InventoryPanel()
    narration = NarrationPanel()
    syslog = SystemLogPanel()
    controls = ControlPanel()

    top_row = BoxLayout(orientation='horizontal', size_hint_y=0.3)
    top_row.add_widget(hud)
    top_row.add_widget(map_panel)
    top_row.add_widget(lore_panel)

    mid_row = BoxLayout(orientation='horizontal', size_hint_y=0.4)
    mid_row.add_widget(char_panel)
    mid_row.add_widget(inv_panel)

    bottom_row = BoxLayout(orientation='horizontal', size_hint_y=0.3)
    bottom_row.add_widget(narration)
    bottom_row.add_widget(syslog)
    bottom_row.add_widget(controls)

    self.add_widget(top_row)
    self.add_widget(mid_row)
    self.add_widget(bottom_row)

    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainMenuScreen(name='main_menu'))
        sm.add_widget(GameSetupScreen(name='game_setup'))
        sm.add_widget(MainInterfaceScreen(name='main_interface'))
        sm.add_widget(CharacterCreationScreen(name='character_creation'))
        sm.current = 'main_menu'
        return sm

class TTRPGApp(App):
    def build(self):
        return MainInterface()

if __name__ == '__main__':
    TTRPGApp().run()
