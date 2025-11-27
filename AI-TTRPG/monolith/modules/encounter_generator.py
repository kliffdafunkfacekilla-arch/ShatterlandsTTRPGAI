"""Adapter module migrating the encounter_generator's stateless logic.

This module loads encounter templates and exposes a simple generator API
via the event bus (command.encounter.generate).
"""
from typing import Any, Dict, List
import json
from pathlib import Path
import random
import asyncio
from ..event_bus import get_event_bus


def _get_data_dir() -> Path:
    """
    Resolves the absolute path to the encounter data directory.

    Returns:
        Path: The Path object pointing to 'encounter_pkg/data' relative to this file.
    """
    # Correct path, relative to this file's new location
    return Path(__file__).parent / "encounter_pkg" / "data"

_DATA_DIR = _get_data_dir()
_COMBAT_ENCOUNTERS = json.loads((_DATA_DIR / "combat_encounters.json").read_text(encoding="utf-8"))
_SKILL_CHALLENGES = json.loads((_DATA_DIR / "skill_challenges.json").read_text(encoding="utf-8"))


def _pick_encounter(tags: List[str] = None) -> Dict[str, Any]:
    """
    Selects a random combat encounter that matches the provided tags.

    If no tags are provided, or if no encounter matches the tags, a random encounter
    is chosen from the entire list of available combat encounters.

    Args:
        tags (List[str], optional): A list of tags to filter encounters (e.g., "forest", "ambush").
            Defaults to None.

    Returns:
        Dict[str, Any]: The data dictionary of the selected encounter.
    """
    tags = tags or []
    candidates = []
    for e in _COMBAT_ENCOUNTERS:
        e_tags = e.get("tags", [])
        if not tags or any(t in e_tags for t in tags):
            candidates.append(e)
    if not candidates:
        candidates = list(_COMBAT_ENCOUNTERS)
    return random.choice(candidates)


async def _on_command(topic: str, payload: Dict[str, Any]) -> None:
    """
    Handles encounter generation commands from the event bus.

    Listens for topics ending in "generate" (e.g., 'command.encounter.generate').
    It selects an encounter based on tags in the payload and publishes the result
    to 'response.encounter.generate'.

    Args:
        topic (str): The topic of the event.
        payload (Dict[str, Any]): The event data, optionally containing a 'tags' list.
    """
    bus = get_event_bus()
    if topic.endswith("generate"):
        tags = payload.get("tags") if payload else None
        enc = _pick_encounter(tags)
        await bus.publish("response.encounter.generate", {"encounter": enc})


def register(orchestrator) -> None:
    """
    Registers the encounter generator module with the orchestrator.

    Subscribes to 'command.encounter.generate' events.

    Args:
        orchestrator: The system orchestrator instance.
    """
    bus = get_event_bus()
    asyncio.get_event_loop().create_task(bus.subscribe("command.encounter.generate", _on_command))
