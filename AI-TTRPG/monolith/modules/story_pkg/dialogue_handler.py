"""
Handles loading and processing of dialogue trees.
"""
import json
from pathlib import Path
from typing import Dict, Any

DIALOGUE_FILE = Path(__file__).parent / "data/dialogues.json"
_dialogue_data: Dict[str, Any] = {}

def _load_all_dialogues():
    """Loads all dialogues from the JSON file into memory."""
    global _dialogue_data
    if not DIALOGUE_FILE.is_file():
        raise FileNotFoundError(f"Dialogue file not found at {DIALOGUE_FILE}")
    with open(DIALOGUE_FILE, "r") as f:
        _dialogue_data = json.load(f)

def get_dialogue_tree(dialogue_id: str) -> Dict[str, Any]:
    """
    Retrieves a full dialogue tree by its ID.
    Loads the data from file if not already in memory.
    """
    if not _dialogue_data:
        _load_all_dialogues()

    if dialogue_id not in _dialogue_data:
        raise ValueError(f"Dialogue tree '{dialogue_id}' not found.")

    return _dialogue_data[dialogue_id]

def get_dialogue_node(dialogue_id: str, node_id: str) -> Dict[str, Any]:
    """
    Retrieves a specific node from a dialogue tree.
    """
    dialogue_tree = get_dialogue_tree(dialogue_id)

    if node_id not in dialogue_tree.get("nodes", {}):
        raise ValueError(f"Node '{node_id}' not found in dialogue '{dialogue_id}'.")

    return dialogue_tree["nodes"][node_id]

# Pre-load dialogues on module import
_load_all_dialogues()
