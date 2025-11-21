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

def generate_dm_response(
    prompt_text: str,
    char_context: Dict[str, Any],
    loc_context: Dict[str, Any],
    api_key: Optional[str] = None
) -> str:
    """
    Generates a response from the AI DM using the Gemini API.
    """
    if not HAS_GENAI:
        return "Error: google-generativeai library not installed. Please install it to use the AI DM."

    if not api_key:
        # Try to get from env var as fallback
        api_key = os.environ.get("GOOGLE_API_KEY")

    if not api_key:
        return "Error: No Google API Key provided. Please set it in Settings."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        # Construct the system prompt
        system_prompt = _construct_system_prompt(char_context, loc_context)
        
        # Combine system prompt and user prompt
        full_prompt = f"{system_prompt}\n\nPlayer Action: {prompt_text}\n\nDM Response:"

        response = model.generate_content(full_prompt)
        
        if response.text:
            return response.text
        else:
            return "The DM remains silent (Empty response from AI)."

    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return f"The DM is having trouble thinking right now. (Error: {e})"

def _construct_system_prompt(char_context: Dict[str, Any], loc_context: Dict[str, Any]) -> str:
    """
    Builds the context string for the LLM.
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
Keep your responses immersive, concise (2-4 sentences usually), and in the second person ("You see...", "You do...").

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
