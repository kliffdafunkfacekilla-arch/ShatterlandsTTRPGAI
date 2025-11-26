from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock

class LoadingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'loading_screen'
        
        layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        
        self.status_label = Label(
            text="Initializing...",
            font_size='24sp',
            size_hint_y=None,
            height=50
        )
        
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=30
        )
        
        layout.add_widget(self.status_label)
        layout.add_widget(self.progress_bar)
        
        self.add_widget(layout)

    def update_status(self, message, progress):
        self.status_label.text = message
        self.progress_bar.value = progress
