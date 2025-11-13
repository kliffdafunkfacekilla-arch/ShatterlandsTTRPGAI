# AI-TTRPG/monolith/modules/__init__.py
"""
Container for monolith domain modules.

This file provides a convenience function to register all
self-contained modules with the orchestrator and event bus.
"""
from typing import List
import logging

logger = logging.getLogger("monolith.modules")

def register_all(orchestrator) -> None:
    """
    Imports and registers all self-contained modules.
    The import order matters for data loading (e.g., rules first).
    """
    try:
        # Stateless, foundational modules
        from . import rules
        from . import map
        from . import encounter_generator

        # Stateful, dependent modules
        from . import world
        from . import character
        from . import story

        # Simple/stub modules
        from . import narrative
        from . import combat

        # Register all modules
        rules.register(orchestrator)
        map.register(orchestrator)
        encounter_generator.register(orchestrator)

        world.register(orchestrator)
        character.register(orchestrator)
        story.register(orchestrator) # This is the main "brain"

        narrative.register(orchestrator)
        combat.register(orchestrator)

        logger.info("All monolith modules registered successfully.")

    except Exception as e:
        logger.exception(f"Failed during module registration: {e}")
        raise
