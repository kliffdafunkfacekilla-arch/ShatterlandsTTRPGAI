"""
Handler for LLM-based AI Dungeon Master responses.
Interfaces with Google's Gemini API.
"""
import logging
import os
import json
from typing import Dict, Any, Optional

# Try to import google.generativeai
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

logger = logging.getLogger("monolith.ai_dm.llm")

# Import the structured response schema
from .schemas import NarrativeResponse

def generate_dm_response(
    prompt_text: str,
    char_context: Dict[str, Any],
    loc_context: Dict[str, Any],
    api_key: Optional[str] = None
) -> str:
    """Generate a narrative response from the AI DM.

    This implementation enforces a JSON output that conforms to the
    ``NarrativeResponse`` Pydantic schema. It also demonstrates a placeholder
    for a diff‑based, minimal context prompt.
    """
    if not HAS_GENAI:
        return "Error: google-generativeai library not installed. Please install it to use the AI DM."

    if not api_key:
        api_key = os.environ.get("GOOGLE_API_KEY")

    if not api_key:
        return "Error: No Google API Key provided. Please set it in Settings."

    try:
        # Initialise the Gemini client
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        # Build the system prompt (static part)
        system_prompt = _construct_system_prompt(char_context, loc_context)

        # Diff‑based context placeholder – in a full implementation this would
        # contain only the recent state changes relevant to the action.
        diff_context = "[Recent context diff placeholder]"

        # Assemble the full prompt sent to the model
        full_prompt = f"{system_prompt}\n{diff_context}\n\nPlayer Action: {prompt_text}\n\nDM Response:"

        response = model.generate_content(full_prompt)

        # Expect the model to return a JSON string that matches NarrativeResponse
        try:
            raw_text = response.text.strip()
            data = json.loads(raw_text)
            validated = NarrativeResponse(**data)
            return validated.message
        except Exception as parse_err:
            logger.error(f"Failed to parse structured AI response: {parse_err}")
            # Fallback to raw text if JSON parsing fails
            if response.text:
                return response.text
            return "The DM remains silent (Empty response from AI)."
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return f"The DM is having trouble thinking right now. (Error: {e})"

def _construct_system_prompt(char_context: Dict[str, Any], loc_context: Dict[str, Any]) -> str:
    """Build the static system prompt for the LLM.

    This prompt provides the AI with the essential character and location
    information. It purposefully avoids sending the full game state to keep the
    token count low.
    """
    # Character Info
    char_name = char_context.get('name', 'Unknown')
    char_class = char_context.get('class_name', 'Adventurer')
    hp = f"{char_context.get('current_hp', 0)}/{char_context.get('max_hp', 0)}"

    # Location Info
    loc_name = loc_context.get('name', 'Unknown Location')
    loc_desc = loc_context.get('description', 'A mysterious place.')

    npcs = loc_context.get('npcs', [])
    npc_str = ", ".join([n.get('template_id', 'Unknown NPC') for n in npcs]) if npcs else "None"

    items = loc_context.get('items', [])
    item_str = ", ".join([i.get('template_id', 'Unknown Item') for i in items]) if items else "None"

    prompt = f"""
You are the Dungeon Master (DM) for a Tabletop RPG called Shatterlands.
Your goal is to describe the world, react to the player's actions, and advance the story.
Keep your responses immersive, concise (2-4 sentences usually), and in the second person (\"You see...\", \"You do...\").

Current Context:
- Player Character: {char_name} (Class: {char_class}, HP: {hp})
- Location: {loc_name}
- Location Description: {loc_desc}
- Visible NPCs: {npc_str}
- Visible Items: {item_str}

Game Rules:
- If the player tries to do something impossible, tell them why.
- If the player enters combat or attacks, describe the start of the fight but do not resolve the whole fight.
- You can invent small details to make the world feel alive.
"""
    return prompt
