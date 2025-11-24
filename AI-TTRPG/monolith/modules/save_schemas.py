"""
Pydantic schemas used *only* for serializing and deserializing
the database state for save games. These schemas must match the
table columns in ..._pkg/models.py exactly.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- Character Schema ---
class CharacterSave(BaseModel):
    id: str
    name: str
    kingdom: Optional[str] = None
    level: int = 1
    stats: Optional[Dict[str, Any]] = {}
    skills: Optional[Dict[str, Any]] = {}
    max_hp: int = 1
    current_hp: int = 1

    # --- ADD THIS LINE ---
    temp_hp: Optional[int] = 0
    # --- END ADD ---
    max_composure: int = 10
    current_composure: int = 10
    resource_pools: Optional[Dict[str, Any]] = {}
    talents: Optional[List[str]] = []
    abilities: Optional[List[str]] = []
    inventory: Optional[Dict[str, Any]] = {}
    equipment: Optional[Dict[str, Any]] = {}
    status_effects: Optional[List[str]] = []
    injuries: Optional[List[Dict[str, Any]]] = []
    current_location_id: int = 1
    position_x: int = 1
    position_y: int = 1
    portrait_id: Optional[str] = None
    
    # --- ADD THIS LINE ---
    previous_state: Optional[Dict[str, Any]] = {} # For AI Context Diffing
    # --- END ADD ---

    class Config:
        from_attributes = True

# --- World Schemas ---
class FactionSave(BaseModel):
    id: int
    name: str
    status: str
    disposition: Dict[str, Any]
    resources: int

    class Config:
        from_attributes = True

class RegionSave(BaseModel):
    id: int
    name: str
    current_weather: Optional[str] = "clear"
    environmental_effects: Optional[List[str]] = []
    faction_influence: Optional[Dict[str, Any]] = {}

    class Config:
        from_attributes = True

class LocationSave(BaseModel):
    id: int
    name: str
    tags: List[str]
    exits: Dict[str, Any]
    description: Optional[str] = None
    generated_map_data: Optional[Any] = None
    map_seed: Optional[str] = None
    region_id: int
    ai_annotations: Optional[Dict[str, Any]] = None
    spawn_points: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class NpcInstanceSave(BaseModel):
    id: int
    template_id: str
    name_override: Optional[str] = None
    current_hp: int
    max_hp: int
    temp_hp: Optional[int] = 0
    max_composure: Optional[int] = 10
    current_composure: Optional[int] = 10
    resource_pools: Optional[Dict[str, Any]] = {}
    abilities: Optional[List[str]] = []
    status_effects: List[str]
    # --- ADD THIS LINE ---
    injuries: Optional[List[Dict[str, Any]]] = []
    # --- END ADD ---
    location_id: int
    behavior_tags: List[str] = []
    coordinates: Optional[Any] = None

    class Config:
        from_attributes = True

class ItemInstanceSave(BaseModel):
    id: int
    template_id: str
    quantity: int
    location_id: Optional[int] = None
    npc_id: Optional[int] = None
    coordinates: Optional[Any] = None

    class Config:
        from_attributes = True

class TrapInstanceSave(BaseModel):
    id: int
    template_id: str
    location_id: int
    coordinates: Optional[Any] = None
    status: str = "armed"

    class Config:
        from_attributes = True

# --- Story Schemas ---
class CampaignSave(BaseModel):
    id: int
    name: str
    main_plot_summary: Optional[str] = None

    class Config:
        from_attributes = True

class ActiveQuestSave(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    steps: List[str]
    current_step: int = 1
    status: str = "active"
    campaign_id: int

    class Config:
        from_attributes = True

class StoryFlagSave(BaseModel):
    id: int
    flag_name: str
    value: Optional[str] = None

    class Config:
        from_attributes = True

# --- Main Save File Structure ---
class SaveGameData(BaseModel):
    characters: List[CharacterSave] = []
    factions: List[FactionSave] = []
    regions: List[RegionSave] = []
    locations: List[LocationSave] = []
    npcs: List[NpcInstanceSave] = []
    items: List[ItemInstanceSave] = []
    traps: List[TrapInstanceSave] = []
    campaigns: List[CampaignSave] = []
    quests: List[ActiveQuestSave] = []
    flags: List[StoryFlagSave] = []

class SaveFile(BaseModel):
    save_name: str
    save_time: str
    active_character_id: Optional[str] = None
    active_character_name: Optional[str] = None
    data: SaveGameData
