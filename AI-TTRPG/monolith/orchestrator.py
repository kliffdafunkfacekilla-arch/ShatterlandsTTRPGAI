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


# module-level orchestrator singleton for convenience
_default: Orchestrator = Orchestrator()

def get_orchestrator() -> Orchestrator:
    """
    Returns the process-wide singleton instance of the Orchestrator.
    """
    return _default
