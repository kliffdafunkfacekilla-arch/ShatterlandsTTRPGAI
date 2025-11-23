"""Orchestrator: coordinates high-level flow inside the monolith.

Responsibilities:
- maintain a simple global state store
- receive commands from UI or external callers
- invoke modules synchronously when needed and listen to events
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Dict, Any
import asyncio

from .modules.world_pkg.models import GameState
from .modules.story_pkg.schemas import WorldStateContext, StoryEvent, EventConsequenceType
from .modules.story_pkg.event_engine import check_and_generate_events
from .event_bus import get_event_bus
import logging

logger = logging.getLogger("monolith.orchestrator")


class Orchestrator:
    """
    Central coordinator for the Monolith architecture.

    Manages high-level state and command dispatching. It acts as the bridge
    between external inputs (UI, API) and internal event-driven modules.
    """
    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.bus = get_event_bus()
        self._lock = asyncio.Lock()
        logger.info("Orchestrator Initialized.")

    async def start(self) -> None:
        """
        Initializes the orchestrator and publishes the startup event.
        """
        # placeholder hook: modules can subscribe to bus here if needed
        await self.bus.publish("orchestrator.started", {"msg": "orchestrator up"})

    async def handle_command(self, command: str, payload: Any) -> Any:
        """
        Dispatches a high-level command to the system.

        Directly handles state queries and updates. Other commands are published
        to the event bus for modules to handle.

        Args:
            command (str): The command identifier (e.g., 'query_state', 'start_combat').
            payload (Any): The data associated with the command.

        Returns:
            Any: The result of the command (state dict, confirmation, etc.).
        """
        async with self._lock:
            # Very small dispatch example
            if command == "query_state":
                return self.state
            if command == "set_state":
                self.state.update(payload or {})
                # notify listeners
                await self.bus.publish("state.updated", self.state)
                return {"ok": True}
            # unknown commands are published as events
            await self.bus.publish(f"command.{command}", payload)
            return {"published": command}
    
    # ============================================================================
    # REACTIVE STORY ENGINE: Turn-Level Event Processing
    # ============================================================================
    
    def _get_current_state(self, session: Session) -> GameState:
        """Retrieves or creates the single global GameState row."""
        # Use a deterministic ID (1) for the single global row.
        stmt = select(GameState).where(GameState.id == 1)
        game_state = session.scalar(stmt)
        
        if game_state is None:
            # Initialize state if it doesn't exist (e.g., first run after migration)
            game_state = GameState(id=1, player_reputation=0, kingdom_resource_level=100)
            session.add(game_state)
            session.commit()
            logger.warning("GameState row not found. Initializing new state (id=1).")
            
        return game_state

    def process_turn_events(self, session: Session, player_action_tags: List[str]) -> List[StoryEvent]:
        """
        The main game loop logic: reads current state, runs reactive event checks, 
        applies consequences, and persists the updated state.
        """
        # 1. READ: Load current persistent state (GameState ORM model)
        game_state = self._get_current_state(session)

        # Build the immutable Pydantic context required by the event engine
        context = WorldStateContext(
            player_reputation=game_state.player_reputation,
            kingdom_resource_level=game_state.kingdom_resource_level,
            # Placeholder for combat outcomes, typically set by combat module
            last_combat_outcome=None, 
            current_location_tags=player_action_tags
        )
        
        # 2. GENERATE: Check rules and generate reactive events
        triggered_events = check_and_generate_events(context)
        
        # 3. APPLY: Process each generated event to modify the mutable ORM model
        for event in triggered_events:
            if event.consequence_type == EventConsequenceType.WORLD_STATE_CHANGE:
                # Example: Apply a simple reputation change from the event payload
                if 'reputation_mod' in event.payload:
                    rep_mod = event.payload['reputation_mod']
                    game_state.player_reputation += rep_mod
                    logger.info(f"Applied Reputation Change: {rep_mod}. New Reputation: {game_state.player_reputation}")
                
                if 'global_morale_debuff' in event.payload:
                    game_state.kingdom_resource_level -= event.payload['global_morale_debuff']

                # Store the narrative for client-side logging/display
                game_state.last_event_text = event.narrative_text
                
            elif event.consequence_type == EventConsequenceType.SPAWN_NPC:
                # Future: Call NPC module to spawn entities based on payload
                logger.info(f"Consequence: SPAWN_NPC triggered. Payload: {event.payload}")
                
            # NOTE: Other consequence types (COMBAT, QUEST) would call other 
            # domain-specific service methods here.
                
        # 4. PERSIST: Commit the session to save changes to the single GameState row
        session.commit()
        
        logger.info("Turn processing complete. State saved.")
        return triggered_events


# module-level orchestrator singleton for convenience
_default: Orchestrator = Orchestrator()

def get_orchestrator() -> Orchestrator:
    """
    Returns the process-wide singleton instance of the Orchestrator.
    """
    return _default
