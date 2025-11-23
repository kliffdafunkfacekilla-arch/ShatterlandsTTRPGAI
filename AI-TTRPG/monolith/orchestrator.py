"""
Orchestrator: coordinates high-level flow inside the monolith.

Responsibilities:
- maintain a simple global state store
- receive commands from UI or external callers
- invoke modules synchronously when needed and listen to events
"""
import logging
import asyncio
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from .modules.world_pkg.models import GameState
from .modules.story_pkg.schemas import WorldStateContext, StoryEvent, EventConsequenceType
from .modules.story_pkg.event_engine import check_and_generate_events
from .event_bus import get_event_bus

logger = logging.getLogger("monolith.orchestrator")


class Orchestrator:
    """Central coordinator for the Monolith architecture.

    Manages high‑level state and command dispatching. It acts as the bridge
    between external inputs (UI, API) and internal event‑driven modules.
    """

    def __init__(self) -> None:
        self.state: Dict[str, Any] = {}
        self.bus = get_event_bus()
        self._lock = asyncio.Lock()
        logger.info("Orchestrator Initialized.")

    # ---------------------------------------------------------------------
    # Gatekeeper logic
    # ---------------------------------------------------------------------
    def should_ai_be_called(self, action_tags: List[str]) -> bool:
        """Determine if the AI DM should be invoked for a given action.

        Simple heuristic: if any tag indicates a creative or open‑ended action,
        return ``True``. Otherwise deterministic rules are expected to handle it.
        """
        creative_keywords = {"creative", "dialogue", "flavor", "story", "npc_interaction"}
        return any(tag.lower() in creative_keywords for tag in action_tags)

    # ---------------------------------------------------------------------
    # Core command handling (simplified for this task)
    # ---------------------------------------------------------------------
    async def handle_command(self, command: str, payload: Any) -> Any:
        async with self._lock:
            if command == "query_state":
                return self.state
            if command == "set_state":
                self.state.update(payload or {})
                await self.bus.publish("state.updated", self.state)
                return {"ok": True}
            # Unknown commands are published as events
            await self.bus.publish(f"command.{command}", payload)
            return {"published": command}

    # ---------------------------------------------------------------------
    # Reactive story engine helpers
    # ---------------------------------------------------------------------
    def _get_current_state(self, session: Session) -> GameState:
        """Retrieve or create the single global ``GameState`` row."""
        stmt = select(GameState).where(GameState.id == 1)
        game_state = session.scalar(stmt)
        if game_state is None:
            game_state = GameState(id=1, player_reputation=0, kingdom_resource_level=100)
            session.add(game_state)
            session.commit()
            logger.warning("GameState row not found. Initializing new state (id=1).")
        return game_state

    def process_turn_events(self, session: Session, player_action_tags: List[str]) -> List[StoryEvent]:
        """Main game‑loop logic: read state, generate events, apply consequences, persist."""
        game_state = self._get_current_state(session)
        context = WorldStateContext(
            player_reputation=game_state.player_reputation,
            kingdom_resource_level=game_state.kingdom_resource_level,
            last_combat_outcome=None,
            current_location_tags=player_action_tags,
        )
        triggered_events = check_and_generate_events(context)
        for event in triggered_events:
            if event.consequence_type == EventConsequenceType.WORLD_STATE_CHANGE:
                if "reputation_mod" in event.payload:
                    rep_mod = event.payload["reputation_mod"]
                    game_state.player_reputation += rep_mod
                    logger.info(f"Applied Reputation Change: {rep_mod}. New Reputation: {game_state.player_reputation}")
                if "global_morale_debuff" in event.payload:
                    game_state.kingdom_resource_level -= event.payload["global_morale_debuff"]
                game_state.last_event_text = event.narrative_text
            elif event.consequence_type == EventConsequenceType.SPAWN_NPC:
                logger.info(f"Consequence: SPAWN_NPC triggered. Payload: {event.payload}")
        session.commit()
        logger.info("Turn processing complete. State saved.")
        return triggered_events

# Module‑level singleton for convenience
_default: Orchestrator = Orchestrator()

def get_orchestrator() -> Orchestrator:
    """Return the process‑wide singleton instance of the Orchestrator."""
    return _default
