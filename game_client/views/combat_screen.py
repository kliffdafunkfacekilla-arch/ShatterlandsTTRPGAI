"""
The Combat Screen for the Shatterlands client.
Displays the battlefield, turn order, and action menu.
"""
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ObjectProperty, ListProperty, StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.progressbar import ProgressBar
from functools import partial
import logging

# Use Kivy Language (KV) string for a clean layout.
COMBAT_SCREEN_KV = """
<CombatEntityWidget@BoxLayout>:
    orientation: 'vertical'
    size_hint: None, None
    size: '120dp', '160dp'
    padding: '5dp'
    spacing: '2dp'
    
    canvas.before:
        Color:
            rgba: (0, 0, 0, 0.5)
        Rectangle:
            pos: self.pos
            size: self.size

    Image:
        source: root.source
        size_hint_y: 0.7
        allow_stretch: True
        keep_ratio: True

    Label:
        text: root.entity_name
        font_size: '14sp'
        bold: True
        size_hint_y: 0.15
        color: 1, 1, 1, 1
        
    ProgressBar:
        max: root.max_hp
        value: root.current_hp
        size_hint_y: 0.15

<CombatScreen>:
    log_label: log_label
    turn_order_container: turn_order_container
    battlefield_container: battlefield_container
    action_menu: action_menu
    
    DungeonBackground:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '10dp'

        # --- Top Bar: Turn Order ---
        ParchmentPanel:
            size_hint_y: 0.15
            orientation: 'vertical'
            padding: '5dp'
            
            Label:
                text: "Turn Order"
                bold: True
                color: 0, 0, 0, 1
                size_hint_y: None
                height: '20dp'
                
            ScrollView:
                BoxLayout:
                    id: turn_order_container
                    orientation: 'horizontal'
                    size_hint_x: None
                    width: self.minimum_width
                    spacing: '10dp'

        # --- Middle: Battlefield & Log ---
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.65
            spacing: '10dp'
            
            # Battlefield (Left)
            ParchmentPanel:
                size_hint_x: 0.7
                id: battlefield_container
                orientation: 'vertical'
                padding: '20dp'
                
                Label:
                    text: "Battlefield"
                    bold: True
                    color: 0, 0, 0, 1
                    size_hint_y: None
                    height: '30dp'
                    
                # Dynamic content added here
                
            # Combat Log (Right)
            ParchmentPanel:
                size_hint_x: 0.3
                orientation: 'vertical'
                
                Label:
                    text: "Combat Log"
                    bold: True
                    color: 0, 0, 0, 1
                    size_hint_y: None
                    height: '30dp'
                    
                ScrollView:
                    Label:
                        id: log_label
                        text: "Combat started..."
                        color: 0, 0, 0, 1
                        size_hint_y: None
                        height: self.texture_size[1]
                        text_size: self.width, None
                        valign: 'top'
                        padding: '5dp'

        # --- Bottom: Action Menu ---
        ParchmentPanel:
            id: action_menu
            size_hint_y: 0.2
            orientation: 'horizontal'
            padding: '10dp'
            spacing: '20dp'
            
            # Actions are added dynamically based on turn
            Label:
                text: "Waiting for turn..."
                color: 0, 0, 0, 1
"""

Builder.load_string(COMBAT_SCREEN_KV)

class CombatEntityWidget(BoxLayout):
    source = StringProperty('')
    entity_name = StringProperty('')
    max_hp = ObjectProperty(10)
    current_hp = ObjectProperty(10)

class CombatScreen(Screen):
    """
    The main combat screen.
    """
    log_label = ObjectProperty(None)
    turn_order_container = ObjectProperty(None)
    battlefield_container = ObjectProperty(None)
    action_menu = ObjectProperty(None)
    
    combat_state = ObjectProperty(None, allownone=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        Clock.schedule_once(self._subscribe_events, 1)

    def _subscribe_events(self, dt):
        if hasattr(self.app, 'event_bus'):
            self.app.event_bus.subscribe("combat.started", self.on_combat_update)
            self.app.event_bus.subscribe("combat.updated", self.on_combat_update)
            self.app.event_bus.subscribe("combat.ended", self.on_combat_end)

    def on_enter(self):
        """Called when screen is shown."""
        # Refresh state if available
        if hasattr(self.app, 'orchestrator') and self.app.orchestrator.combat_manager:
            self.on_combat_update(self.app.orchestrator.combat_manager.get_state_dict())

    def on_combat_update(self, state):
        """Updates the UI based on combat state."""
        self.combat_state = state
        
        # Update Log
        if 'log' in state:
            self.log_label.text = "\\n".join(state['log'][-20:]) # Show last 20 lines
            
        # Update Turn Order
        self._update_turn_order(state)
        
        # Update Battlefield
        self._update_battlefield(state)
        
        # Update Actions
        self._update_actions(state)

    def on_combat_end(self, result):
        """Handle combat end."""
        from game_client.ui_utils import show_success, show_error
        
        outcome = result.get('result')
        if outcome == 'victory':
            show_success("Victory!", "You have defeated all enemies!", 
                         on_dismiss=lambda: setattr(self.app.root, 'current', 'main_interface'))
        elif outcome == 'defeat':
            show_error("Defeat", "Your party has fallen...", 
                       on_dismiss=lambda: setattr(self.app.root, 'current', 'main_menu'))
        elif outcome == 'fled':
            show_success("Escaped", "You fled from combat.", 
                         on_dismiss=lambda: setattr(self.app.root, 'current', 'main_interface'))

    def _update_turn_order(self, state):
        self.turn_order_container.clear_widgets()
        
        participants = state.get('participants', [])
        turn_order = state.get('turn_order', [])
        current_idx = state.get('current_turn_index', 0)
        
        for i, pid in enumerate(turn_order):
            p = next((x for x in participants if x['id'] == pid), None)
            if not p: continue
            
            # Highlight current turn
            is_active = (i == current_idx)
            color = (0.2, 0.8, 0.2, 1) if is_active else (0.5, 0.5, 0.5, 1)
            
            btn = Button(
                text=f"{p['name']}\\nInit: {p['initiative']}",
                size_hint=(None, 1),
                width='100dp',
                background_color=color
            )
            self.turn_order_container.add_widget(btn)

    def _get_entity_image(self, entity_data):
        """Resolves image path based on entity data."""
        if entity_data.get('is_player'):
            return 'game_client/assets/graphics/entities/hero.png'
        elif 'goblin' in entity_data.get('id', '').lower():
            return 'game_client/assets/graphics/entities/goblin.png'
        else:
            # Default fallback
            return 'game_client/assets/graphics/entities/goblin.png'

    def _update_battlefield(self, state):
        # Clear dynamic widgets (keep title)
        title = self.battlefield_container.children[-1] # Keep the last child (which is top in kv)
        self.battlefield_container.clear_widgets()
        self.battlefield_container.add_widget(title)
        
        # Simple list view for now
        participants = state.get('participants', [])
        
        # Split into teams
        players = [p for p in participants if p['is_player']]
        enemies = [p for p in participants if not p['is_player']]
        
        # Layout
        field = BoxLayout(orientation='horizontal', spacing='50dp')
        
        # Player Side
        p_box = BoxLayout(orientation='vertical', spacing='10dp')
        p_box.add_widget(Label(text="HEROES", color=(0,0,1,1), bold=True))
        for p in players:
            widget = CombatEntityWidget(
                source=self._get_entity_image(p),
                entity_name=p['name'],
                max_hp=p['max_hp'],
                current_hp=p['hp']
            )
            p_box.add_widget(widget)
        field.add_widget(p_box)
        
        # VS
        field.add_widget(Label(text="VS", font_size='24sp', bold=True, color=(0,0,0,1)))
        
        # Enemy Side
        e_box = BoxLayout(orientation='vertical', spacing='10dp')
        e_box.add_widget(Label(text="ENEMIES", color=(1,0,0,1), bold=True))
        for e in enemies:
            widget = CombatEntityWidget(
                source=self._get_entity_image(e),
                entity_name=e['name'],
                max_hp=e['max_hp'],
                current_hp=e['hp']
            )
            
            # Hacky click handler
            def on_click(instance, touch, eid=e['id']):
                if instance.collide_point(*touch.pos):
                    self._on_enemy_click(eid, instance)
                    return True
            
            widget.bind(on_touch_down=on_click)
            e_box.add_widget(widget)
            
        field.add_widget(e_box)
        
        self.battlefield_container.add_widget(field)

    def _update_actions(self, state):
        self.action_menu.clear_widgets()
        
        turn_order = state.get('turn_order', [])
        current_idx = state.get('current_turn_index', 0)
        
        if not turn_order: return
        
        active_id = turn_order[current_idx]
        participants = state.get('participants', [])
        active_actor = next((p for p in participants if p['id'] == active_id), None)
        
        # Check if it's a local player's turn
        # For now, assume all 'is_player' are local
        if active_actor and active_actor['is_player']:
            self.action_menu.add_widget(Label(text=f"It is {active_actor['name']}'s turn!", color=(0,0,0,1), bold=True))
            
            # Attack Button (Target selection handled via click for now, or default)
            atk_btn = Button(text="Attack", size_hint=(None, 1), width='120dp')
            atk_btn.bind(on_release=lambda x: self._show_target_selection(active_id, participants))
            self.action_menu.add_widget(atk_btn)
            
            # Flee
            flee_btn = Button(text="Flee", size_hint=(None, 1), width='120dp')
            flee_btn.bind(on_release=lambda x: self._perform_action(active_id, "FLEE", {}))
            self.action_menu.add_widget(flee_btn)
            
            # End Turn
            end_btn = Button(text="End Turn", size_hint=(None, 1), width='120dp')
            end_btn.bind(on_release=lambda x: self._perform_action(active_id, "END_TURN", {}))
            self.action_menu.add_widget(end_btn)
            
        else:
            self.action_menu.add_widget(Label(text=f"Waiting for {active_actor['name']}...", color=(0,0,0,1)))

    def _show_target_selection(self, attacker_id, participants):
        # For simplicity, just attack the first living enemy for now
        # Or show a toast "Click an enemy to attack!"
        from game_client.ui_utils import show_success
        show_success("Select Target", "Click on an enemy in the battlefield to attack!")
        self.pending_attacker_id = attacker_id

    def _on_enemy_click(self, target_id, instance):
        if hasattr(self, 'pending_attacker_id'):
            self._perform_action(self.pending_attacker_id, "ATTACK", {"target_id": target_id})
            del self.pending_attacker_id

    def _perform_action(self, player_id, action_type, data):
        import asyncio
        # We need to run async method from sync callback
        # Best way is to use orchestrator directly if possible, or fire-and-forget
        
        # Since we are in UI thread, we can call orchestrator directly but it's async
        # We'll use a helper or just schedule it
        
        async def send_action():
            await self.app.orchestrator.handle_player_action(player_id, action_type, **data)
            
        # Create task in the running loop
        loop = asyncio.get_event_loop()
        loop.create_task(send_action())