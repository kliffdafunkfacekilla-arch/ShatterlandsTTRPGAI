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

# --- Direct Monolith Imports ---
try:
    from monolith.modules import story as story_api
except ImportError as e:
    logging.error(f"QUEST_LOG: Failed to import story_api: {e}")
    story_api = None

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

        if not story_api:
            container.add_widget(Label(text="Error: Story module not loaded."))
            return

        quests = story_api.get_all_quests(1)
        if not quests:
            container.add_widget(Label(text="No active quests."))
            return

        for quest in quests:
            title = Label(
                text=quest['title'],
                font_size='20sp',
                bold=True,
                size_hint_y=None,
                height=self.texture_size[1]
            )
            description = Label(
                text=quest['description'],
                font_size='14sp',
                size_hint_y=None,
                height=self.texture_size[1]
            )
            container.add_widget(title)
            container.add_widget(description)

            for i, step_text in enumerate(quest['steps']):
                is_current = (i + 1) == quest['current_step']
                step_label = Label(
                    text=f"  - {step_text}",
                    bold=is_current,
                    size_hint_y=None,
                    height=self.texture_size[1]
                )
                container.add_widget(step_label)
