"""
Core logic for the (non-AI) keyword-based AI Dungeon Master.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("monolith.ai_dm")

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
