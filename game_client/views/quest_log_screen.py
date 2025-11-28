# game_client/views/quest_log_screen.py
import logging
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import ObjectProperty

QUEST_LOG_KV = """
<QuestLogScreen>:
    BoxLayout:
        orientation: 'vertical'

        # --- Top Bar ---
        BoxLayout:
            size_hint_y: None
            height: '48dp'
            Label:
                text: 'Quest Log'
                font_size: '24sp'
            Button:
                text: 'Back to Game'
                size_hint_x: 0.3
                on_release: app.root.current = 'main_interface'

        # --- Main Content Area ---
        ScrollView:
            GridLayout:
                id: quest_list_container
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                padding: '10dp'
                spacing: '15dp'
"""

Builder.load_string(QUEST_LOG_KV)

class QuestLogScreen(Screen):
    quest_list_container = ObjectProperty(None)

    def on_enter(self, *args):
        container = self.ids.quest_list_container
        container.clear_widgets()
        
        app = App.get_running_app()
        if not app.orchestrator:
            container.add_widget(Label(text="Error: Orchestrator not loaded."))
            return

        state = app.orchestrator.get_current_state()
        if not state or not state.quests:
            container.add_widget(Label(text="No active quests."))
            return

        for quest in state.quests:
            # Quest object might be a Pydantic model or dict depending on how it's accessed
            # SaveGameData uses Pydantic models
            
            title_text = getattr(quest, 'title', 'Unknown Quest')
            desc_text = getattr(quest, 'description', 'No description.')
            steps = getattr(quest, 'steps', [])
            current_step = getattr(quest, 'current_step', 1)
            
            title = Label(
                text=title_text,
                font_size='20sp',
                bold=True,
                size_hint_y=None,
                height='40dp'
            )
            description = Label(
                text=desc_text,
                font_size='14sp',
                size_hint_y=None,
                height='60dp',
                text_size=(self.width - 40, None),
                halign='left',
                valign='top'
            )
            container.add_widget(title)
            container.add_widget(description)

            for i, step_text in enumerate(steps):
                is_current = (i + 1) == current_step
                prefix = ">> " if is_current else "   "
                step_label = Label(
                    text=f"{prefix}{step_text}",
                    bold=is_current,
                    color=(1, 1, 0, 1) if is_current else (0.8, 0.8, 0.8, 1),
                    size_hint_y=None,
                    height='30dp',
                    text_size=(self.width - 60, None),
                    halign='left'
                )
                container.add_widget(step_label)
            
            # Separator
            container.add_widget(Label(size_hint_y=None, height='20dp'))
