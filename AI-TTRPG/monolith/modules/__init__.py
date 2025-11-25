"""
Container for monolith domain modules.

This file provides a convenience function to register all
self-contained modules with the orchestrator and event bus.
"""
from typing import List
import logging

def register_all(orchestrator) -> None:
    """
    Registers all Monolith modules with the orchestrator.

    This function imports and initializes each module, allowing them to
    subscribe to event bus topics or expose their APIs.
    Imports are performed lazily to avoid circular dependencies during startup.

    Args:
        orchestrator: The system orchestrator instance.
    """
    # import modules lazily to avoid import cycles during bootstrap
    from . import narrative, combat, rules, encounter_generator, story, world
    from . import character, save_api, ai_dm

    narrative.register(orchestrator)
    combat.register(orchestrator)

    # stateless services being migrated first
    rules.register(orchestrator)
    encounter_generator.register(orchestrator)

    # adapters / stateful services
    world.register(orchestrator)
    story.register(orchestrator)

    # --- REGISTER THE NEW MODULES ---
    character.register(orchestrator)
    save_api.register(orchestrator)
    ai_dm.register(orchestrator)
    simulation.register(orchestrator)
