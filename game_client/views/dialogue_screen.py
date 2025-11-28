"""
The Dialogue screen for conversations.
"""
import logging
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.properties import StringProperty, ObjectProperty, ListProperty

# --- Monolith Imports ---
try:
    from monolith.modules import story as story_api
except ImportError as e:
    logging.error(f"DIALOGUE_SCREEN: Failed to import monolith modules: {e}")
    story_api = None

DIALOGUE_SCREEN_KV = """
<DialogueScreen>:
    dialogue_text_label: dialogue_text_label
    options_container: options_container

    BoxLayout:
        orientation: 'vertical'
        padding: '20dp'
        spacing: '20dp'

        Label:
            id: dialogue_text_label
            text: root.dialogue_text
            font_size: '18sp'
            size_hint_y: 0.6
            text_size: self.width, None

        ScrollView:
            size_hint_y: 0.4
            BoxLayout:
                id: options_container
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: '10dp'
"""
Builder.load_string(DIALOGUE_SCREEN_KV)

class DialogueScreen(Screen):
    dialogue_text = StringProperty("No dialogue loaded.")
    options = ListProperty([])

    dialogue_text_label = ObjectProperty(None)
    options_container = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialogue_id = None
        self.current_node_id = None

    def on_enter(self, *args):
        """Called when the screen is entered."""
        app = App.get_running_app()
        dialogue_info = app.game_settings.get('pending_dialogue')
        if not dialogue_info:
            logging.error("No pending dialogue found!")
            app.root.current = 'main_interface'
            return

        self.dialogue_id = dialogue_info.get('dialogue_id')
        start_node_id = dialogue_info.get('start_node_id', 'start_node')

        self.load_node(self.dialogue_id, start_node_id)

    def load_node(self, dialogue_id, node_id):
        """Loads and displays a specific dialogue node."""
        if not story_api:
            self.dialogue_text = "Error: Story API not available."
            return

        try:
            node_data = story_api.get_dialogue_node(dialogue_id, node_id)
            self.dialogue_text = node_data.get('text', '...')
            self.options = node_data.get('options', [])
            self.current_node_id = node_id
            self.dialogue_id = dialogue_id
            self.update_options_ui()

            if not self.options:
                # If there are no options, it's an end node.
                # Add a button to return to the game.
                end_button = Button(text="[End Conversation]", size_hint_y=None, height='44dp')
                end_button.bind(on_release=self.end_dialogue)
                self.options_container.add_widget(end_button)

        except Exception as e:
            logging.exception(f"Failed to load dialogue node: {e}")
            self.dialogue_text = f"Error loading dialogue: {e}"

    def update_options_ui(self):
        """Clears and rebuilds the option buttons."""
        self.options_container.clear_widgets()
        for option in self.options:
            btn = Button(
                text=option.get('text', '...'),
                size_hint_y=None,
                height='44dp'
            )
            btn.bind(on_release=lambda x, next_node=option.get('next_node_id'): self.on_option_select(next_node))
            self.options_container.add_widget(btn)

    def on_option_select(self, next_node_id):
        """Called when a player clicks a dialogue option."""
        if next_node_id:
            # 1. Notify Orchestrator (for side effects like quests)
            app = App.get_running_app()
            if app.orchestrator:
                # Fire and forget the action to the orchestrator
                import asyncio
                
                def send_action():
                    asyncio.run(
                        app.orchestrator.handle_player_action(
                            player_id=app.active_character_context.id if app.active_character_context else "unknown",
                            action_type="DIALOGUE",
                            dialogue_id=self.dialogue_id,
                            node_id=next_node_id,
                            npc_id="unknown" # TODO: Pass NPC ID if available
                        )
                    )
                
                # Run in background
                from threading import Thread
                Thread(target=send_action, daemon=True).start()

            # 2. Update UI immediately
            self.load_node(self.dialogue_id, next_node_id)
        else:
            self.end_dialogue()

    def end_dialogue(self, *args):
        """Returns to the main interface screen."""
        self.dialogue_id = None
        self.current_node_id = None
        app = App.get_running_app()
        app.game_settings['pending_dialogue'] = None
        app.root.current = 'main_interface'
