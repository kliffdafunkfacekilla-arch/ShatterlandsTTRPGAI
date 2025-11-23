"""Orchestrator: coordinates high-level flow inside the monolith.

Responsibilities:
- maintain a simple global state store
- receive commands from UI or external callers
- invoke modules synchronously when needed and listen to events
"""
from typing import Any, Dict
import asyncio
from .event_bus import get_event_bus


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
    
    def process_turn_events(self, session, location_id: int) -> Dict[str, Any]:
        """
        Generates and processes reactive story events for the current turn.
        
        This method:
        1. Reads current world state from the database (location + region)
        2. Generates events using the event engine
        3. Applies event consequences (reputation, resources, etc.)
        4. Persists state changes back to the database
        
        Args:
            session: SQLAlchemy database session
            location_id: The current location ID
        
        Returns:
            Dict containing:
                - events: List of generated StoryEvent objects
                - state_changes: Dict of applied changes
                - success: Boolean indicating if processing succeeded
        """
        try:
            from .modules.world_pkg import crud as world_crud
            from .modules.story_pkg.event_engine import check_and_generate_events
            from .modules.story_pkg.schemas import EventConsequenceType
            import logging
            
            logger = logging.getLogger("monolith.orchestrator")
            
            # 1. READ: Load current world state
            logger.info(f"Processing turn events for location {location_id}")
            context = world_crud.get_world_state_context(session, location_id)
            
            logger.debug(
                f"World state: rep={context.player_reputation}, "
                f"resources={context.kingdom_resource_level}, "
                f"combat={context.last_combat_outcome}"
            )
            
            # 2. GENERATE: Check for triggered events
            events = check_and_generate_events(context)
            
            if not events:
                logger.debug("No events triggered this turn")
                return {
                    "success": True,
                    "events": [],
                    "state_changes": {},
                    "narrative": []
                }
            
            # 3. APPLY/WRITE: Process event consequences
            state_changes = {}
            narrative_log = []
            
            for event in events:
                logger.info(f"Processing event: {event.event_id}")
                narrative_log.append(event.narrative_text)
                
                # Apply consequences based on type
                if event.consequence_type == EventConsequenceType.WORLD_STATE_CHANGE:
                    # Reputation changes
                    if "reputation_bonus" in event.payload:
                        delta = event.payload["reputation_bonus"]
                        world_crud.update_player_reputation(session, location_id, delta)
                        state_changes["reputation_delta"] = delta
                        logger.info(f"Applied reputation bonus: +{delta}")
                    
                    # Resource changes
                    if "resource_delta" in event.payload:
                        location = world_crud.get_location(session, location_id)
                        if location and location.region_id:
                            delta = event.payload["resource_delta"]
                            world_crud.update_kingdom_resources(
                                session, location.region_id, delta
                            )
                            state_changes["resource_delta"] = delta
                            logger.info(f"Applied resource change: {delta:+d}")
                
                elif event.consequence_type == EventConsequenceType.SPAWN_NPC:
                    # Queue NPC spawn (implementation depends on game flow)
                    npc_type = event.payload.get("npc_type", "unknown")
                    count = event.payload.get("count", 1)
                    state_changes.setdefault("queued_spawns", []).append({
                        "type": npc_type,
                        "count": count,
                        "location_id": location_id
                    })
                    logger.info(f"Queued NPC spawn: {count}x {npc_type}")
                
                elif event.consequence_type == EventConsequenceType.ADD_QUEST_LOG:
                    # Add quest to active quests
                    quest_id = event.payload.get("quest_id")
                    quest_title = event.payload.get("quest_title")
                    state_changes.setdefault("new_quests", []).append({
                        "id": quest_id,
                        "title": quest_title
                    })
                    logger.info(f"Added quest: {quest_title}")
                
                elif event.consequence_type == EventConsequenceType.INITIATE_SKILL_CHALLENGE:
                    # Queue skill challenge
                    skill = event.payload.get("skill_check")
                    dc = event.payload.get("difficulty", 15)
                    state_changes.setdefault("skill_challenges", []).append({
                        "skill": skill,
                        "dc": dc
                    })
                    logger.info(f"Initiated skill challenge: {skill} DC {dc}")
            
            # Commit all state changes
            session.commit()
            logger.info(f"Turn events processed successfully: {len(events)} events")
            
            return {
                "success": True,
                "events": [
                    {
                        "id": e.event_id,
                        "trigger": e.trigger_type.value,
                        "consequence": e.consequence_type.value,
                        "narrative": e.narrative_text
                    }
                    for e in events
                ],
                "state_changes": state_changes,
                "narrative": narrative_log
            }
            
        except Exception as e:
            logger.exception(f"Failed to process turn events: {e}")
            # Rollback on error
            session.rollback()
            return {
                "success": False,
                "error": str(e),
                "events": [],
                "state_changes": {},
                "narrative": []
            }


# module-level orchestrator singleton for convenience
_default: Orchestrator = Orchestrator()

def get_orchestrator() -> Orchestrator:
    """
    Returns the process-wide singleton instance of the Orchestrator.
    """
    return _default
