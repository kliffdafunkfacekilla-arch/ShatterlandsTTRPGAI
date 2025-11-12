"""Simple asyncio-based in-process event bus for the monolith.

Features:
- pub/sub with topic string keys
- optional filtering by predicate
- support for synchronous query handlers via direct call

This is intentionally small and dependency-free; swap for a more
feature-rich implementation later if needed.
"""
from typing import Any, Callable, Dict, List, Coroutine, Optional
import asyncio

Subscriber = Callable[[str, Any], Coroutine[Any, Any, None]]


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Subscriber]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: Any) -> None:
        # dispatch to subscribers without waiting on each
        async with self._lock:
            subs = list(self._subscribers.get(topic, []))
        for sub in subs:
            # schedule but don't await to keep bus responsive
            asyncio.create_task(sub(topic, payload))

    async def subscribe(self, topic: str, handler: Subscriber) -> None:
        async with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(handler)

    async def unsubscribe(self, topic: str, handler: Subscriber) -> None:
        async with self._lock:
            if topic in self._subscribers:
                try:
                    self._subscribers[topic].remove(handler)
                except ValueError:
                    pass


# singleton convenience (but modules may create their own bus if needed)
_default_bus: Optional[EventBus] = None

def get_event_bus() -> EventBus:
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus
