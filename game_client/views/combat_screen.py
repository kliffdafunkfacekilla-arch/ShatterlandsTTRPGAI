"""
Placeholder for the Combat Screen.
"""
import logging
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

class CombatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation='vertical', padding='50dp', spacing='20dp')

        title = Label(
            text='COMBAT MODE',
            font_size='32sp',
            size_hint_y=0.3
        )

        # We'll display the turn order for debugging
        self.turn_order_label = Label(
            text='Turn Order: [loading...]',
            font_size='18sp',
            size_hint_y=0.4
        )

        exit_btn = Button(
            text='End Combat (DEBUG)',
            font_size='20sp',
            size_hint_y=0.2
        )
        exit_btn.bind(on_release=self.end_combat)

        layout.add_widget(title)
        layout.add_widget(self.turn_order_label)
        layout.add_widget(exit_btn)

        self.add_widget(layout)

    def on_enter(self, *args):
        """Called when the screen is shown."""
        app = App.get_running_app()
        combat_state = app.game_settings.get('combat_state')

        if combat_state:
            logging.info(f"Entered combat: {combat_state.get('combat_id')}")
            turn_order = combat_state.get('turn_order', [])
            self.turn_order_label.text = f"Turn Order: {', '.join(turn_order)}"
        else:
            logging.warning("Entered CombatScreen with no combat_state.")
            self.turn_order_label.text = "Error: No combat state found."

    def end_combat(self, instance):
        """Debug function to return to the exploration screen."""
        app = App.get_running_app()

        # Clear the combat state
        if 'combat_state' in app.game_settings:
            del app.game_settings['combat_state']

        logging.info("DEBUG: Forcing end of combat.")
        app.root.current = 'main_interface'
