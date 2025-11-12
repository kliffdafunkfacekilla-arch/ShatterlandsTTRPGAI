"""Adapter module for the existing rules data.

This module is an initial, lightweight migration of stateless rules data
into the monolith. It exposes a small command handler interface via the
event bus and also provides programmatic helpers for other modules.
"""
from typing import Any, Dict
import json
from pathlib import Path
import asyncio
from ..event_bus import get_event_bus


def _find_rules_data_dir() -> Path:
    # Walk up from this file until we find the AI-TTRPG/rules_engine/data folder
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".." / ".." / "rules_engine" / "data"
        candidate = candidate.resolve()
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not locate rules_engine/data directory")


_DATA_DIR = _find_rules_data_dir()


def _load_json(name: str) -> Any:
    p = _DATA_DIR / name
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


# preload some common data
STATS_AND_SKILLS = _load_json("stats_and_skills.json")
SKILL_MAPPINGS = _load_json("skill_mappings.json")
ITEM_TEMPLATES = _load_json("item_templates.json")


def get_skill_for_category(category_name: str) -> str:
    if category_name not in SKILL_MAPPINGS:
        raise ValueError(f"Category '{category_name}' not found")
    return SKILL_MAPPINGS[category_name]


async def _on_command(topic: str, payload: Dict[str, Any]) -> None:
    # expected topic: command.rules.<action>
    bus = get_event_bus()
    if topic.endswith("get_skill_for_category"):
        try:
            category = payload.get("category")
            result = get_skill_for_category(category)
            await bus.publish("response.rules.get_skill_for_category", {"result": result})
        except Exception as e:
            await bus.publish("response.rules.get_skill_for_category", {"error": str(e)})


def register(orchestrator) -> None:
    bus = get_event_bus()
    # subscribe to relevant commands
    asyncio.create_task(bus.subscribe("command.rules.get_skill_for_category", _on_command))
