from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

# --- Tool Schemas ---

class SkillCheckInput(BaseModel):
    """
    Perform a skill check for the player.
    """
    skill_name: str = Field(..., description="The name of the skill (e.g., 'Athletics', 'Perception').")
    difficulty: int = Field(..., description="The DC (Difficulty Class) for the check.")

class SpawnEntityInput(BaseModel):
    """
    Spawn an entity (monster, NPC, item) at a specific location.
    """
    entity_type: str = Field(..., description="Type of entity (e.g., 'goblin', 'chest').")
    x: int = Field(..., description="X coordinate.")
    y: int = Field(..., description="Y coordinate.")

# --- Tool Implementations ---
# These functions will be called by the AI DM.
# They should interact with the game modules (Rules, Map, etc.)

def perform_skill_check(skill_name: str, difficulty: int) -> str:
    """
    Executes a skill check.
    """
    # In a real implementation, this would call rules_pkg.check_skill(player, skill, dc)
    # For now, we simulate a roll.
    import random
    roll = random.randint(1, 20)
    # Add modifiers here if we had access to player sheet
    total = roll # + modifier
    
    result = "SUCCESS" if total >= difficulty else "FAILURE"
    return f"Skill Check ({skill_name} DC {difficulty}): Rolled {roll}. Result: {result}."

def spawn_entity(entity_type: str, x: int, y: int) -> str:
    """
    Spawns an entity on the map.
    """
    # This would call map_pkg.spawn_entity or similar
    return f"Spawned {entity_type} at ({x}, {y})."

# --- Tool Registry ---
# Map tool names to their schemas and functions
AI_TOOLS = {
    "perform_skill_check": {
        "schema": SkillCheckInput,
        "function": perform_skill_check,
        "description": "Use this to resolve uncertain actions like climbing, searching, or persuading."
    },
    "spawn_entity": {
        "schema": SpawnEntityInput,
        "function": spawn_entity,
        "description": "Use this to spawn new creatures or items on the map dynamically."
    }
}
