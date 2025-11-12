"""Minimal narrative module example.

This module demonstrates a module that subscribes to orchestrator events
and exposes a simple API to progress narrative state.
"""
from typing import Any
import asyncio
from ..event_bus import get_event_bus
from ..shared import PlayerState, Position


async def _on_state_updated(topic: str, payload: Any) -> None:
    # placeholder: respond to state changes
    print(f"[narrative] received {topic} -> {payload}")


def register(orchestrator) -> None:
    bus = get_event_bus()
    # subscribe to state updates
    asyncio.create_task(bus.subscribe("state.updated", _on_state_updated))


async def advance_narrative(node_id: str, orchestrator) -> dict:
    # simple state mutation example
    print(f"[narrative] advancing to {node_id}")
    return await orchestrator.handle_command("set_state", {"narrative_node": node_id})
