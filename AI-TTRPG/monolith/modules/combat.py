"""Minimal combat module example.

This stub demonstrates subscribing to orchestrator commands and publishing
combat events back onto the event bus.
"""
from typing import Any
import asyncio
from ..event_bus import get_event_bus


async def _on_command_start_combat(topic: str, payload: Any) -> None:
    """
    Handles the 'command.start_combat' event.

    This function simulates a combat resolution process by waiting briefly and then
    publishing a 'combat.enemy_defeated' event. It serves as a placeholder or example
    implementation for combat logic triggered via the event bus.

    Args:
        topic (str): The topic of the event (e.g., 'command.start_combat').
        payload (Any): The data associated with the event, expected to contain 'enemy_id'.
    """
    print(f"[combat] start combat with payload: {payload}")
    # simulate combat resolution
    await asyncio.sleep(0.1)
    bus = get_event_bus()
    await bus.publish("combat.enemy_defeated", {"enemy_id": payload.get("enemy_id")})


def register(orchestrator) -> None:
    """
    Registers the combat module with the orchestrator.

    Subscribes the module to the 'command.start_combat' event.

    Args:
        orchestrator: The system orchestrator instance.
    """
    bus = get_event_bus()
    asyncio.create_task(bus.subscribe("command.start_combat", _on_command_start_combat))
