"""
Core logic for the (non-AI) keyword-based AI Dungeon Master.
Includes intent classification for deterministic routing.
"""
import logging
import re
from dataclasses import dataclass
from typing import Dict, Any, List

logger = logging.getLogger("monolith.ai_dm")

# Simple keyword mapping to deterministic action tags
INTENT_KEYWORD_MAP = {
    "attack": "combat_action",
    "hit": "combat_action",
    "strike": "combat_action",
    "fight": "combat_action",
    "buy": "shop_interaction",
    "purchase": "shop_interaction",
    "sell": "shop_interaction",
    "trade": "shop_interaction",
    "inspect": "inspect_item",
    "look at": "inspect_item",
    "examine": "inspect_item",
    "check": "inspect_item",
    "talk to": "dialogue_action",
    "speak to": "dialogue_action",
    "persuade": "dialogue_action",
    "ask": "dialogue_action",
    "tell a story about": "narrative_request",
    "describe": "narrative_request",
    "what is": "narrative_request",
    "tell me about": "narrative_request",
}

@dataclass
class ActionIntent:
    """Represents the classified intent of a player's narrative prompt."""
    intent_type: str  # e.g., "combat_action", "shop_interaction", "narrative_request"
    is_deterministic: bool  # True if this can be handled by coded logic
    action_tags: List[str]  # Fallback tags for legacy AI gatekeeper
    payload: Dict[str, Any] = None  # Additional parsed data

def classify_intent(prompt_text: str) -> ActionIntent:
    """Lightweight deterministic intent classifier.

    Scans the prompt for known keywords (case-insensitive) and returns the first match.
    If no keyword is found, falls back to a generic narrative intent.

    This is the first line of defense in the AI gatekeeper, allowing deterministic
    actions to bypass expensive LLM calls entirely.

    Args:
        prompt_text: The raw user input to classify

    Returns:
        ActionIntent object with classified intent type and metadata
    """
    lowered = prompt_text.lower()
    
    for phrase, tag in INTENT_KEYWORD_MAP.items():
        if re.search(r"\b" + re.escape(phrase) + r"\b", lowered):
            deterministic = tag != "narrative_request"
            return ActionIntent(
                intent_type=tag,
                is_deterministic=deterministic,
                action_tags=[tag],
                payload={"matched_phrase": phrase},
            )
    
    # No known keyword – treat as narrative
    return ActionIntent(
        intent_type="narrative_request",
        is_deterministic=False,
        action_tags=["creative", "dialogue", "story"],
        payload={},
    )

def get_keyword_response(
    prompt_text: str,
    char_context: Dict[str, Any],
    loc_context: Dict[str, Any]) -> str:
    """
    Generates a narrative response based on simple keyword matching in the user's prompt.

    It checks for standard actions like looking around, inspecting specific objects (doors),
    or checking one's own status, and uses the provided character and location context
    to construct a relevant reply.

    Args:
        prompt_text (str): The raw text input from the user.
        char_context (Dict[str, Any]): The current state of the character (HP, name, etc.).
        loc_context (Dict[str, Any]): The current state of the location (description, NPCs, items).

    Returns:
        str: A descriptive string response to the user's action.
    """
    prompt = prompt_text.lower().strip()

    # --- 1. Inspection Keywords ---
    if "look around" in prompt or "inspect room" in prompt or "describe" in prompt:
        description = loc_context.get("description", "You are in a room.")

        npcs = loc_context.get("npcs", [])
        items = loc_context.get("items", [])

        if npcs:
            description += "\nYou see "
            description += ", ".join([n.get('template_id', 'an NPC') for n in npcs])
            description += "."

        if items:
            description += "\nThere are items on the ground: "
            description += ", ".join([i.get('template_id', 'an item') for i in items])
            description += "."

        return description

    # --- 2. Annotation Keywords ---
    if "door" in prompt:
        annotations = loc_context.get("ai_annotations", {})
        door_found = False
        for key, data in annotations.items():
            if data.get("type") == "door":
                door_found = True
                status = data.get("status", "closed")
                if status == "locked":
                    return f"The {key.replace('_', ' ')} is locked."
                elif status == "open":
                    return f"The {key.replace('_', ' ')} is wide open."
                else:
                    return f"You see a {key.replace('_', ' ')}. It is currently closed."
        if not door_found:
            return "You don't see any doors here."

    # --- 3. Self-Inspection Keywords ---
    if "check self" in prompt or "look at myself" in prompt:
        hp = char_context.get('current_hp', 0)
        max_hp = char_context.get('max_hp', 1)
        status = char_context.get('status_effects', [])

        response = f"You are {char_context.get('name', 'a character')}. You have {hp}/{max_hp} HP."
        if status:
            response += f"\nYou are currently afflicted with: {', '.join(status)}."
        else:
            response += "\nYou feel fine."
        return response

    # --- 4. NPC Keywords ---
    if "talk to guard" in prompt or "ask guard" in prompt:
        # This is a simple placeholder.
        # A real implementation would check if a "guard" NPC is nearby.
        return "The guard eyes you suspiciously. 'What do you want?'"

    # --- 5. Default Fallback ---
    return f"You ponder the words '{prompt_text}', but nothing seems to happen."
