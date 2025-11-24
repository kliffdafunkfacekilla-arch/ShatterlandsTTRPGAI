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

# Import the structured response schema and context builder
from .schemas import NarrativeResponse
from .context_builder import build_minimal_context

def generate_dm_response(
    prompt_text: str,
    char_context: Dict[str, Any],
    loc_context: Dict[str, Any],
    recent_log: list = None,
    api_key: Optional[str] = None,
    request_type: str = "narrative" # Added request_type
) -> str:
    """Generate a narrative response from the AI DM using minimal context.

    This implementation enforces a JSON output that conforms to the
    ``NarrativeResponse`` Pydantic schema and uses diff-based minimal
    context to drastically reduce token usage.
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

        # Build minimal context snapshot (diff-based)
        context_snapshot = build_minimal_context(char_context, loc_context, recent_log)
        context_text = context_snapshot.to_prompt_text()

        # Build the system instruction
        system_instruction = _get_system_instruction()

        # Assemble the full prompt with minimal context
        full_prompt = f"{system_instruction}\n\n{context_text}\n\nPlayer Input: {prompt_text}\n\nYour Task: Respond in valid JSON matching {{\"message\": \"your response here\"}}"

        # --- Metrics: Estimate Prompt Tokens ---
        # Rough estimate: 1 token ~= 4 chars
        prompt_tokens = len(full_prompt) // 4
        
        response = model.generate_content(full_prompt)

        # --- Metrics: Estimate Response Tokens ---
        response_text = response.text if response.text else ""
        response_tokens = len(response_text) // 4
        total_tokens = prompt_tokens + response_tokens
        
        logger.info(f"LLM Request ({request_type}): Prompt={prompt_tokens}t, Response={response_tokens}t, Total={total_tokens}t")

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

def _get_system_instruction() -> str:
    """Get the static system instruction for the AI DM.

    This is intentionally minimal - context is provided dynamically
    via the ContextSnapshot to keep prompts lean and focused.
    """
    return """
You are the Dungeon Master (DM) for Shatterlands, a dark fantasy TTRPG.

Your role:
- React to player actions with immersive, concise descriptions (2-4 sentences)
- Use second person (\"You see...\", \"You do...\")
- Stay consistent with the provided context
- Invent atmospheric details but respect the game rules

Constraints:
- If the player tries something impossible, explain why
- If combat starts, describe the opening but don't resolve it
- Base your response ONLY on the provided context - do not invent major plot points

Output Format:
- You MUST output valid JSON: {\"message\": \"your narrative response\"}
"""
