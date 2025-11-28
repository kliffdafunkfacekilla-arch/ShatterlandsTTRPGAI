"""
Event Bus Integration Pattern for Main Interface Screen

This shows how to add Event Bus subscriptions to existing screens.
Copy this pattern into main_interface_screen.py's __init__ and on_enter methods.
"""

class MainInterfaceScreen(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # ... existing init code ...
        
        # NEW: Subscribe to Event Bus events
        from kivy.clock import Clock
        Clock.schedule_once(self._subscribe_to_events, 0)
    
    def _subscribe_to_events(self, dt):
        """Subscribe to game events"""
        app = App.get_running_app()
        
        if app.event_bus:
            # Subscribe to turn changes
            app.event_bus.subscribe("player.turn_start", self.on_turn_changed)
            
            # Subscribe to ability results
            app.event_bus.subscribe("action.ability", self.on_ability_used)
            
            # Subscribe to state updates
            app.event_bus.subscribe("game.state_updated", self.on_state_updated)
            
            # Subscribe to narratives (if AI DM enabled)
            app.event_bus.subscribe("narrative.received", self.on_narrative_received)
            
            logger.info("Main Interface subscribed to Event Bus")
    
    # Event handlers
    def on_turn_changed(self, player_id, player_name, **kwargs):
        """Called when hotseat turn changes"""
        self.update_log(f"It's {player_name}'s turn!")
        
        # Update active character if in party
        for char in self.party_contexts:
            if char.id == player_id:
                self.active_character_context = char
                break
    
    def on_ability_used(self, result, player_id, **kwargs):
        """Called when an ability is used"""
        if result.get("success"):
            narrative = result.get("narrative", "")
            if narrative:
                self.update_narration(narrative)
            
            # Show effects
            effects = result.get("effects_applied", [])
            for effect in effects:
                self.update_log(f"Effect: {effect.get('type')}")
    
    def on_state_updated(self, **kwargs):
        """Called when game state changes"""
        # Refresh display from orchestrator
        app = App.get_running_app()
        state = app.orchestrator.get_current_state()
        
        if state:
            # Update party from state
            self.party_contexts = list(state.characters)
            self.party_list = self.party_contexts
    
    def on_narrative_received(self, text, **kwargs):
        """Called when AI DM generates narrative"""
        self.update_narration(text)


# ============================================================================
# SIMPLIFIED ACTION EXAMPLE
# ============================================================================

def example_action_with_orchestrator(self):
    """Example: Using Orchestrator for actions instead of HTTP"""
    import asyncio
    from kivy.app import App
    
    app = App.get_running_app()
    player = app.orchestrator.get_active_player()
    
    # Call orchestrator directly
    result = asyncio.run(
        app.orchestrator.handle_player_action(
            player_id=player.id,
            action_type="ABILITY",
            ability_id="fireball",
            target_id="enemy1"
        )
    )
    
    # Event Bus will notify subscribers automatically
    # No need to manually update UI here


# ============================================================================
# MINIMAL CHANGES NEEDED
# ============================================================================

# 1. Add _subscribe_to_events() method
# 2. Add event handler methods (on_turn_changed, on_ability_used, etc.)  
# 3. Replace any HTTP calls with orchestrator calls
# 4. The screen will reactively update via Event Bus callbacks

# That's it! The full refactor of main_interface_screen.py can be done
# incrementally following this pattern.
