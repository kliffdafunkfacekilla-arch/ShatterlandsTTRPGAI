"""
Handles loading and processing of dialogue trees.
"""
import json
from pathlib import Path
from typing import Dict, Any

DIALOGUE_FILE = Path(__file__).parent / "data/dialogues.json"
_dialogue_data: Dict[str, Any] = {}

def _load_all_dialogues():
    """
    Internal function to load the entire dialogue dataset from disk into memory.

    Raises:
        FileNotFoundError: If the `dialogues.json` file does not exist.
    """
    global _dialogue_data
    if not DIALOGUE_FILE.is_file():
        raise FileNotFoundError(f"Dialogue file not found at {DIALOGUE_FILE}")
    with open(DIALOGUE_FILE, "r") as f:
        _dialogue_data = json.load(f)

def get_dialogue_tree(dialogue_id: str) -> Dict[str, Any]:
    """
    Retrieves a complete dialogue tree by its unique identifier.

    Ensures data is loaded before access.

    Args:
        dialogue_id (str): The ID of the dialogue tree.

    Returns:
        Dict[str, Any]: The dialogue tree data structure.

    Raises:
        ValueError: If the dialogue ID is not found.
    """
    if not _dialogue_data:
        _load_all_dialogues()

    if dialogue_id not in _dialogue_data:
        raise ValueError(f"Dialogue tree '{dialogue_id}' not found.")

    return _dialogue_data[dialogue_id]

def get_dialogue_node(dialogue_id: str, node_id: str) -> Dict[str, Any]:
    """
    Fetches a single node (conversation step) from a dialogue tree.

    Args:
        dialogue_id (str): The ID of the parent dialogue tree.
        node_id (str): The ID of the specific node to retrieve.

    Returns:
        Dict[str, Any]: The node data (text, choices, etc.).

    Raises:
        ValueError: If the node ID is not found within the specified tree.
    """
    dialogue_tree = get_dialogue_tree(dialogue_id)

    if node_id not in dialogue_tree.get("nodes", {}):
        raise ValueError(f"Node '{node_id}' not found in dialogue '{dialogue_id}'.")

    return dialogue_tree["nodes"][node_id]

# Pre-load dialogues on module import
_load_all_dialogues()
