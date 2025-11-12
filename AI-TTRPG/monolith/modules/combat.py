"""Minimal combat module example.

This stub demonstrates subscribing to orchestrator commands and publishing
combat events back onto the event bus.
"""
from typing import Any
import asyncio
from ..event_bus import get_event_bus


async def _on_command_start_combat(topic: str, payload: Any) -> None:
    print(f"[combat] start combat with payload: {payload}")
    # simulate combat resolution
    await asyncio.sleep(0.1)
    bus = get_event_bus()
    await bus.publish("combat.enemy_defeated", {"enemy_id": payload.get("enemy_id")})


def register(orchestrator) -> None:
    bus = get_event_bus()
    asyncio.create_task(bus.subscribe("command.start_combat", _on_command_start_combat))
