import logging
from typing import Dict, Any, List
from .simulation_pkg import services, database
# from .. import orchestrator # Not actually used in this file, and causes circular imports if not careful.
# The register function takes orchestrator as an arg, so we don't need to import it at top level.

logger = logging.getLogger("monolith.simulation")

def get_world_context() -> str:
    """
    Returns a natural language summary of the current world state.
    Used by the AI Director to understand the geopolitical context.
    """
    db = database.SessionLocal()
    try:
        return services.get_world_context_summary(db)
    finally:
        db.close()

def process_turn() -> List[str]:
    """
    Advances the simulation by one turn.
    Returns a list of events that occurred.
    """
    logger.info("Processing simulation turn...")
    db = database.SessionLocal()
    try:
        return services.process_turn(db)
    except Exception as e:
        logger.exception(f"Simulation turn failed: {e}")
        return []
    finally:
        db.close()

def register(orchestrator_instance) -> None:
    """
    Registers the Simulation module with the orchestrator.
    """
    logger.info("[simulation] module registered")
    # Future: Subscribe to event bus for "quest_completed" events to trigger turns automatically
