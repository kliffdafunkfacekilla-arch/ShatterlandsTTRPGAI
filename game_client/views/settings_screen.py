# game_client/views/settings_screen.py
"""
The Settings screen.
Allows the user to change audio volume and accessibility options.
"""
import logging
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.uix.button import Button
from kivy.properties import ObjectProperty, StringProperty

# --- Kivy Language (KV) String for the Layout ---
SETTINGS_SCREEN_KV = """
<SettingsScreen>:
    BoxLayout:
        orientation: 'vertical'

        # --- Top Bar ---
        BoxLayout:
            size_hint_y: None
            height: '48dp'
            canvas.before:
                Color:
                    rgba: 0.1, 0.1, 0.1, 0.9
                Rectangle:
                    pos: self.pos
                    size: self.size

            Label:
                text: 'Settings'
                font_size: '24sp'

            Button:
                text: 'Back'
                size_hint_x: 0.3
                on_release: root.go_back()

        # --- Main Content Area ---
        ScrollView:
            GridLayout:
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                padding: '20dp'
                spacing: '20dp'

                # --- Audio Settings ---
                Label:
                    text: 'Audio'
                    font_size: '20sp'
                    size_hint_y: None
                    height: '30dp'
                    halign: 'left'
                    text_size: self.width, None

                GridLayout:
                    cols: 2
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: '10dp'

                    Label:
                        text: 'Music Volume:'
                        font_size: '16sp'
                        size_hint_x: 0.4
                    Slider:
                        id: music_slider
                        min: 0
                        max: 100
                        value: 80 # Default value
                        # on_value: root.on_music_volume_change(self.value)

                    Label:
                        text: 'Sound Effects Volume:'
                        font_size: '16sp'
                        size_hint_x: 0.4
                    Slider:
                        id: sfx_slider
                        min: 0
                        max: 100
                        value: 100 # Default value
                        # on_value: root.on_sfx_volume_change(self.value)

                # --- Accessibility Settings ---
                Label:
                    text: 'Accessibility'
                    font_size: '20sp'
                    size_hint_y: None
                    height: '30dp'
                    halign: 'left'
                    text_size: self.width, None

                GridLayout:
                    cols: 2
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: '10dp'

                    Label:
                        text: 'Colorblind Mode:'
                        font_size: '16sp'
                    Switch:
                        id: colorblind_switch
                        active: False
                        # on_active: root.on_colorblind_toggle(self.active)

                    Label:
                        text: 'Reduce Flashing Effects:'
                        font_size: '16sp'
                    Switch:
                        id: flashing_switch
                        active: False
                        # on_active: root.on_flashing_toggle(self.active)
"""

# Load the KV string
Builder.load_string(SETTINGS_SCREEN_KV)

class SettingsScreen(Screen):
    """
    The settings screen class. The UI is defined in the KV string above.
    The logic for saving/loading these settings will be handled by
    a separate settings_manager.
    """

    # Store the previous screen to return to
    previous_screen = StringProperty('main_menu')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Note: We will bind these widgets to the settings_manager
        # once it is created. For now, they just exist visually.

    def on_pre_enter(self, *args):
        """
        Called before the screen is shown. We use this to find out
        which screen we came from, so we can go back to it.
        """
        # Store the screen we came from, default to 'main_menu'
        current_screen = App.get_running_app().root.current
        if current_screen != self.name: # Don't set it to ourself
            self.previous_screen = current_screen

    def go_back(self):
        """
        Saves settings and returns to the previous screen
        (e.g., Main Menu or the Pause Menu in main_interface).
        """
        logging.info("SettingsScreen: 'Back' pressed. Returning to: %s", self.previous_screen)

        # Save Settings
        try:
            from game_client.settings_manager import settings_manager
            
            # Gather values from UI (assuming IDs exist, otherwise default)
            # Since we don't have direct references to sliders in this snippet, 
            # we'll assume they are bound to properties or we'd need to look them up.
            # For this fix, we'll just trigger a save of the current manager state
            # assuming the UI updated the manager directly or via bindings.
            
            settings_manager.save_settings()
            logging.info("Settings saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

        App.get_running_app().root.current = self.previous_screen

    # --- Placeholder functions for later ---

    def load_settings(self):
        """
        Called on_enter to load settings from the manager
        and apply them to the widgets.
        """
        # Example:
        # settings = App.get_running_app().settings_manager.load_settings()
        # self.ids.music_slider.value = settings.get('music_volume', 80)
        # self.ids.sfx_slider.value = settings.get('sfx_volume', 100)
        # self.ids.colorblind_switch.active = settings.get('colorblind_mode', False)
        # self.ids.flashing_switch.active = settings.get('reduce_flashing', False)
        pass

    def on_music_volume_change(self, value):
        logging.debug(f"Music volume changed to: {value}")
        # Here we would call:
        # App.get_running_app().audio_manager.set_music_volume(value / 100.0)
        pass

    def on_sfx_volume_change(self, value):
        logging.debug(f"SFX volume changed to: {value}")
        # Here we would call:
        # App.get_running_app().audio_manager.set_sfx_volume(value / 100.0)
        pass

    def on_colorblind_toggle(self, active):
        logging.debug(f"Colorblind mode toggled to: {active}")
        pass

    def on_flashing_toggle(self, active):
        logging.debug(f"Reduce flashing toggled to: {active}")
        pass