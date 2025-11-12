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
    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.bus = get_event_bus()
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        # placeholder hook: modules can subscribe to bus here if needed
        await self.bus.publish("orchestrator.started", {"msg": "orchestrator up"})

    async def handle_command(self, command: str, payload: Any) -> Any:
        """Dispatch a high-level command.

        This function keeps the orchestrator as the single locus of truth for
        game state transitions. It may call modules synchronously (await)
        for short operations, or publish events for longer workflows.
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
    return _default
