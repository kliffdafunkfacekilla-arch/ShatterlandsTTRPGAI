"""
Quest Log Screen
Displays all active quests and their steps.
"""
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

# --- Monolith Imports ---
try:
    from monolith.modules import story as story_api
except ImportError as e:
    logging.error(f"QUEST_LOG: Failed to import story_api: {e}")
    story_api = None

# --- Kivy Language (KV) String ---
QUEST_LOG_KV = """
<QuestLogScreen>:
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

# Load the KV string
Builder.load_string(QUEST_LOG_KV)

class QuestLogScreen(Screen):
    quest_list_container = ObjectProperty(None)

    def on_enter(self, *args):
        """Called when this screen is shown. Fetches quests."""
        if not self.ids or not story_api:
            return

        container = self.ids.quest_list_container
        container.clear_widgets()

        try:
            # Hardcoding campaign 1 for now
            quests = story_api.get_all_quests(1)

            if not quests:
                container.add_widget(Label(text="No active quests.", font_size='16sp'))
                return

            for quest in quests:
                # Add Title
                title = Label(
                    text=quest.get('title', 'Unknown Quest'),
                    font_size='20sp',
                    bold=True,
                    size_hint_y=None,
                    height='44dp'
                )
                container.add_widget(title)

                # Add Description
                desc = Label(
                    text=quest.get('description', '...'),
                    font_size='14sp',
                    size_hint_y=None
                )
                desc.bind(texture_size=desc.setter('size'))
                container.add_widget(desc)

                # Add Steps
                current_step_num = quest.get('current_step', 1)
                for i, step_text in enumerate(quest.get('steps', [])):
                    is_active_step = (i + 1) == current_step_num

                    step_label = Label(
                        text=f"  - {step_text}",
                        font_size='14sp',
                        bold=is_active_step,
                        color=(1, 1, 1, 1) if is_active_step else (0.7, 0.7, 0.7, 1),
                        size_hint_y=None,
                        height='30dp'
                    )
                    container.add_widget(step_label)

        except Exception as e:
            logging.exception(f"Failed to load quests: {e}")
            container.add_widget(Label(text="Error loading quests."))
