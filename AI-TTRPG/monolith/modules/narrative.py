"""Minimal narrative module example.

This module demonstrates a module that subscribes to orchestrator events
and exposes a simple API to progress narrative state.
"""
from typing import Any
import asyncio
from ..event_bus import get_event_bus
from ..shared import PlayerState, Position


async def _on_state_updated(topic: str, payload: Any) -> None:
    """
    Handles 'state.updated' events.

    This is a placeholder listener that logs state changes. It demonstrates how the
    narrative module can react to broader system state updates.

    Args:
        topic (str): The event topic (e.g., 'state.updated').
        payload (Any): The data payload describing the state update.
    """
    # placeholder: respond to state changes
    print(f"[narrative] received {topic} -> {payload}")


def register(orchestrator) -> None:
    """
    Registers the narrative module with the orchestrator.

    Subscribes to 'state.updated' events.

    Args:
        orchestrator: The system orchestrator instance.
    """
    bus = get_event_bus()
    # subscribe to state updates
    asyncio.get_event_loop().create_task(bus.subscribe("state.updated", _on_state_updated))


async def advance_narrative(node_id: str, orchestrator) -> dict:
    """
    Advances the narrative to a specific node.

    This function sends a command to the orchestrator to update the narrative state
    to the specified node ID.

    Args:
        node_id (str): The ID of the narrative node to advance to.
        orchestrator: The orchestrator instance to handle the state update command.

    Returns:
        dict: The result of the 'set_state' command execution.
    """
    # simple state mutation example
    print(f"[narrative] advancing to {node_id}")
    return await orchestrator.handle_command("set_state", {"narrative_node": node_id})
