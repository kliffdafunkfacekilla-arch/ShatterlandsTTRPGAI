"""
Container for monolith domain modules.

Modules should expose a `register(orchestrator)` function that attaches
their handlers to the orchestrator and event bus. This file provides a
convenience function to register all built-in modules.
"""
from typing import List

def register_all(orchestrator) -> None:
    # import modules lazily to avoid import cycles during bootstrap
    from . import narrative, combat, rules, encounter_generator, map_generator, story, world

    # --- ADD 'character' TO THIS LIST ---
    from . import character

    narrative.register(orchestrator)
    combat.register(orchestrator)

    # stateless services being migrated first
    rules.register(orchestrator)
    encounter_generator.register(orchestrator)
    map_generator.register(orchestrator)

    # adapters / stateful services
    world.register(orchestrator)
    story.register(orchestrator)

    # --- REGISTER THE NEW MODULE ---
    character.register(orchestrator)
