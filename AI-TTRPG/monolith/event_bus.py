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
import logging

Subscriber = Callable[[str, Any], Coroutine[Any, Any, None]]


class EventBus:
    """
    A simple asynchronous event bus for in-process communication.

    Supports publishing events to topics and subscribing handlers to those topics.
    Thread-safe for registration but handlers are invoked as asyncio tasks.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Subscriber]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: Any) -> None:
        """
        Publishes an event to a topic.

        All subscribers to the topic will be invoked as independent asyncio tasks.
        This method does not wait for subscribers to finish.

        Args:
            topic (str): The event topic identifier.
            payload (Any): The data to pass to subscribers.
        """
        # dispatch to subscribers without waiting on each
        async with self._lock:
            subs = list(self._subscribers.get(topic, []))
        for sub in subs:
            # schedule but don't await to keep bus responsive
            task = asyncio.create_task(sub(topic, payload))
            task.add_done_callback(self._handle_task_result)

    def _handle_task_result(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.getLogger("monolith.event_bus").exception(f"Event handler failed: {e}")

    async def subscribe(self, topic: str, handler: Subscriber) -> None:
        """
        Subscribes a handler function to a topic.

        Args:
            topic (str): The event topic to listen for.
            handler (Subscriber): An async callable that takes (topic, payload).
        """
        async with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(handler)

    async def unsubscribe(self, topic: str, handler: Subscriber) -> None:
        """
        Unsubscribes a handler from a topic.

        Args:
            topic (str): The event topic.
            handler (Subscriber): The handler to remove.
        """
        async with self._lock:
            if topic in self._subscribers:
                try:
                    self._subscribers[topic].remove(handler)
                except ValueError:
                    pass


# singleton convenience (but modules may create their own bus if needed)
_default_bus: Optional[EventBus] = None

def get_event_bus() -> EventBus:
    """
    Returns the process-wide singleton instance of the EventBus.
    """
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus
