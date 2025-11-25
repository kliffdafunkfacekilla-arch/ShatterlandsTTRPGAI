from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from enum import Enum

# --- StoryFlag ---
class StoryFlagBase(BaseModel):
    flag_name: str
    value: str
class StoryFlag(StoryFlagBase):
    id: int
    class Config:
        from_attributes = True

# --- ActiveQuest ---
class ActiveQuestBase(BaseModel):
    title: str
    description: Optional[str] = None
    steps: List[str]
    current_step: int = 1
    status: str = "active"
    campaign_id: int
class ActiveQuestCreate(ActiveQuestBase):
    pass
class ActiveQuest(ActiveQuestBase):
    id: int
    class Config:
        from_attributes = True
class ActiveQuestUpdate(BaseModel):
    current_step: Optional[int] = None
    status: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[str]] = None

# --- Story Seed ---
class StorySeed(BaseModel):
    """
    A dormant plot point placed in the world.
    """
    id: str
    trigger_type: str # e.g. "npc_talk", "enter_zone"
    location_type: str # e.g. "forest"
    data: Optional[Dict[str, Any]] = {} # Extra data

# --- Campaign ---
class CampaignBase(BaseModel):
    name: str
    main_plot_summary: Optional[str] = None
class CampaignCreate(CampaignBase):
    pass
class Campaign(CampaignBase):
    id: int
    active_quests: List[ActiveQuest] = []
    class Config:
        from_attributes = True

# --- Orchestration ---
class OrchestrationSpawnNpc(BaseModel):
    template_id: str
    location_id:int
    name_override: Optional[str] = None
    coordinates: Optional[Any] = None
    current_hp: Optional[int] = None
    max_hp: Optional[int] = None
    temp_hp: Optional[int] = 0
    max_composure: Optional[int] = 10
    current_composure: Optional[int] = 10
    resource_pools: Optional[Dict[str, Any]] = {}
    abilities: Optional[List[str]] = []
    behavior_tags: Optional[List[str]] = []

class TrapInstanceCreate(BaseModel):
    template_id: str
    location_id: int
    coordinates: List[int]

class OrchestrationSpawnItem(BaseModel):
    template_id: str
    location_id: Optional[int] = None
    npc_id: Optional[int] = None
    quantity: int = 1
    coordinates: Optional[Any] = None

class OrchestrationCharacterContext(BaseModel):
    id: int
    name: str
    kingdom: str
    character_sheet: Dict[str, Any]

class OrchestrationWorldContext(BaseModel):
    id: int
    name: str
    region: Any
    generated_map_data: Optional[Any] = None
    ai_annotations: Optional[Dict[str, Any]] = None
    spawn_points: Optional[Dict[str, Any]] = None
    npcs: List[Any] = []
    items: List[Any] = []

# --- Combat ---
class CombatStartRequest(BaseModel):
    location_id: int
    player_ids: List[str]
    npc_template_ids: List[str]

class CombatParticipantResponse(BaseModel):
    actor_id: str
    actor_type: str
    initiative_roll: int
    # --- BURT'S NEW FIELD ---
    ability_usage: Dict[str, int] = {}
    # ------------------------
    class Config:
        from_attributes = True

class CombatEncounter(BaseModel):
    id: int
    location_id: int
    status: str
    turn_order: List[str]
    current_turn_index: int
    participants: List[CombatParticipantResponse] = []
    # --- BURT'S NEW FIELD ---
    active_zones: List[Dict[str, Any]] = []
    # ------------------------
    class Config:
        from_attributes = True

class PlayerActionRequest(BaseModel):
    action: str
    target_id: Optional[str] = None
    ability_id: Optional[str] = None
    item_id: Optional[str] = None
    coordinates: Optional[List[int]] = None
    ready_action_details: Optional[Dict[str, Any]] = None

class PlayerActionResponse(BaseModel):
    success: bool
    message: str
    log: list[str]
    new_turn_index: int
    combat_over: bool = False
    # --- BURT'S NEW FIELD ---
    reaction_opportunity: Optional[Dict[str, Any]] = None
    # ------------------------

class WorldStateContext(BaseModel):
    player_reputation: int
    kingdom_resource_level: int
    last_combat_outcome: Optional[str] = None
    current_location_tags: List[str] = []

class EventConsequenceType(Enum):
    WORLD_STATE_CHANGE = "world_state_change"
    SPAWN_NPC = "spawn_npc"
    START_COMBAT = "start_combat"
    ADD_QUEST = "add_quest"
    NO_OP = "no_op"
    INITIATE_SKILL_CHALLENGE = "initiate_skill_challenge"
    ADD_QUEST_LOG = "add_quest_log"

class StoryEvent(BaseModel):
    event_type: str
    narrative_text: str
    consequence_type: EventConsequenceType
    payload: Dict[str, Any] = {}

class EventTriggerType(Enum):
    REPUTATION_CHANGE = "reputation_change"
    RESOURCE_LOW = "resource_low"
    COMBAT_CRITICAL = "combat_critical"
    PLAYER_ACTION = "player_action"

class InteractionRequest(BaseModel):
    actor_id: str
    target_object_id: str
    interaction_type: str
    location_id: int

class InteractionResponse(BaseModel):
    success: bool
    message: str
    updated_annotations: Optional[Dict[str, Any]] = None
    items_added: Optional[List[Dict[str, Any]]] = None
    items_removed: Optional[List[Dict[str, Any]]] = None
