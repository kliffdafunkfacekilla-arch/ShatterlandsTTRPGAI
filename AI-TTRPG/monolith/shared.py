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
    id: int
    name: str
    position: Position
    current_location_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def safe_update(target: Dict[str, Any], diff: Dict[str, Any]) -> Dict[str, Any]:
    """Simple deterministic merge helper used by orchestrator/state updates."""
    result = dict(target)
    result.update(diff)
    return result
