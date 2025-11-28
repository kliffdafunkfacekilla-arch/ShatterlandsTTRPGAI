"""
Combat Screen Placeholder
Temporary replacement for the combat screen to prevent crashes due to 
database dependencies during the refactoring process.
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.app import App

class CombatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding='20dp', spacing='20dp')
        
        # Title
        layout.add_widget(Label(
            text="Combat System Under Maintenance", 
            font_size='24sp', 
            color=(1, 0.3, 0.3, 1),
            size_hint_y=None, 
            height='50dp'
        ))
        
        # Message
        layout.add_widget(Label(
            text="The combat system is currently being updated to the new local-first architecture.\nPlease check back later!", 
            halign='center',
            valign='middle'
        ))
        
        # Back Button
        back_btn = Button(
            text="Return to Game",
            size_hint=(None, None),
            size=('200dp', '50dp'),
            pos_hint={'center_x': 0.5}
        )
        back_btn.bind(on_release=self.go_back)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

    def go_back(self, *args):
        app = App.get_running_app()
        app.root.current = 'main_interface'