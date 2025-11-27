from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.factory import Factory

class LoadingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use DungeonBackground for the layout
        self.layout = Factory.DungeonBackground(orientation='vertical', padding=50, spacing=20)
        
        self.status_label = Factory.DungeonLabel(text="Initializing...", font_size='20sp')
        # Standard ProgressBar is fine, or we could style it later
        self.progress = ProgressBar(max=100, value=0)
        
        self.layout.add_widget(Factory.DungeonLabel(text="Shatterlands", font_size='40sp', size_hint_y=0.5, color=(0.9, 0.8, 0.6, 1), bold=True))
        self.layout.add_widget(self.status_label)
        self.layout.add_widget(self.progress)
        self.add_widget(self.layout)

    def update_status(self, text, progress_val):
        self.status_label.text = text
        self.progress.value = progress_val
