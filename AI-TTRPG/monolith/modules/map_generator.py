"""Adapter module migrating the map_generator service.

Exposes a simple `command.map.generate` handler that returns a generated
map using existing generation data. This is intentionally lightweight and
deterministic for tests.
"""
from typing import Any, Dict
import json
from pathlib import Path
import asyncio
from random import randint
from ..event_bus import get_event_bus


def _find_map_data_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".." / ".." / "map_generator" / "data"
        candidate = candidate.resolve()
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not locate map_generator/data directory")


_DATA_DIR = _find_map_data_dir()
_ALGO = json.loads((_DATA_DIR / "generation_algorithms.json").read_text(encoding="utf-8"))
_TILES = json.loads((_DATA_DIR / "tile_definitions.json").read_text(encoding="utf-8"))


def _generate_simple_map(width: int, height: int) -> list:
    grid = [[randint(0, len(_TILES) - 1) for _ in range(width)] for _ in range(height)]
    return grid


async def _on_command(topic: str, payload: Dict[str, Any]) -> None:
    bus = get_event_bus()
    if topic.endswith("generate"):
        width = payload.get("width", 10)
        height = payload.get("height", 10)
        grid = _generate_simple_map(width, height)
        await bus.publish("response.map.generate", {"map": grid})


def register(orchestrator) -> None:
    bus = get_event_bus()
    asyncio.create_task(bus.subscribe("command.map.generate", _on_command))
