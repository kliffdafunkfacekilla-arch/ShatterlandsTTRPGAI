from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# --- API Request Model ---
class MapInjectionRequest(BaseModel):
    """
    Specific items or NPCs to force into the generated map.
    """
    required_item_ids: List[str] = []
    required_npc_ids: List[str] = []
    atmosphere_tags: List[str] = []

class MapGenerationRequest(BaseModel):
    """
    Inputs from the AI DM or story_engine.
    """
    tags: List[str] # e.g., ["forest", "outside", "ruins"]
    seed: Optional[str] = None # For reproducible generation
    width: Optional[int] = None # Optional override
    height: Optional[int] = None # Optional override
    injections: Optional[MapInjectionRequest] = None # --- NEW ---

# --- New: Context Containers ---
class MapFlavorContext(BaseModel):
    """
    Pre-generated text assets for this specific map.
    Saved in the Location's ai_annotations or similar field.
    """
    # General Atmosphere
    environment_description: str = "A generic area."
    visuals: List[str] = [] # e.g., "Vines hanging from trees", "Broken pillars"
    sounds: List[str] = [] # e.g., "Distant wolf howl", "Rustling leaves"
    smells: List[str] = []

    # Combat Flavor Banks (The optimization)
    # The client will pick random entries from these lists during combat
    combat_hits: List[str] = [] # e.g. "Your blade cuts through the thick vines to strike the foe."
    combat_misses: List[str] = []
    spell_casts: List[str] = []
    enemy_intros: List[str] = [] # e.g. "A goblin bursts from the underbrush!"

# --- API Response Model ---
class MapGenerationResponse(BaseModel):
    """
    The generated map data, now enriched with AI context.
    """
    width: int
    height: int
    map_data: List[List[int]] # The 2D array of tile IDs
    seed_used: str # The actual seed used (generated if none provided)
    algorithm_used: str # Name of the algorithm from the rules file
    spawn_points: Optional[Dict[str, List[List[int]]]] = None # e.g., {"player": [[5,5]], "enemy": [[10,10],[12,8]]}

    # --- NEW FIELD ---
    flavor_context: Optional[MapFlavorContext] = None
