"""
Container for monolith domain modules.

This file provides a convenience function to register all
self-contained modules with the orchestrator and event bus.
"""
from typing import List
import logging

def register_all(orchestrator) -> None:
    # import modules lazily to avoid import cycles during bootstrap
    from . import narrative, combat, rules, encounter_generator, story, world

    # --- ADD 'character' TO THIS LIST ---
    from . import character

    narrative.register(orchestrator)
    combat.register(orchestrator)

    # stateless services being migrated first
    rules.register(orchestrator)
    encounter_generator.register(orchestrator)

    # adapters / stateful services
    world.register(orchestrator)
    story.register(orchestrator)

    # --- REGISTER THE NEW MODULE ---
    character.register(orchestrator)
