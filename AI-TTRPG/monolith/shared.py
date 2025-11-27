"""Shared kernel: data models, simple utilities and types.

Keep this small: the shared kernel should NOT be a dumping ground for
business logic. Use it for canonical data shapes, small helpers, and
cross-cutting concerns (logging adapters, feature flags etc.).
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional


@dataclass
class Position:
    x: int
    y: int


@dataclass
class PlayerState:
    """
    Represents the minimal shared state of a player for system-wide access.
    """
    id: int
    name: str
    position: Position
    current_location_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts the dataclass instance to a dictionary."""
        return asdict(self)


def safe_update(target: Dict[str, Any], diff: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs a safe, non-destructive dictionary update.

    Returns a new dictionary containing the merged result of `target` and `diff`,
    without modifying the original `target` dictionary.

    Args:
        target (Dict): The base dictionary.
        diff (Dict): The updates to apply.

    Returns:
        Dict: The new merged dictionary.
    """
    result = dict(target)
    result.update(diff)
    return result

import functools
from typing import Callable

def with_db_session(session_factory):
    """
    Decorator to inject a database session into a function.
    
    If 'db' is already present in kwargs, it is used.
    Otherwise, a new session is created from session_factory and closed after execution.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # If 'db' is passed explicitly, use it and don't close it here
            if "db" in kwargs and kwargs["db"] is not None:
                return func(*args, **kwargs)
            
            # Otherwise, create a new session
            db = session_factory()
            try:
                kwargs["db"] = db
                return func(*args, **kwargs)
            finally:
                db.close()
        return wrapper
    return decorator
