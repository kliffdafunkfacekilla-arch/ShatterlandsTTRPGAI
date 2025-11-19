# app/schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


# --- NEW SCHEMAS ---
class CombatSlots(BaseModel):
    head: Optional[Dict[str, Any]] = None
    chest: Optional[Dict[str, Any]] = None
    legs: Optional[Dict[str, Any]] = None
    shoulders: Optional[Dict[str, Any]] = None
    boots: Optional[Dict[str, Any]] = None
    hands: Optional[Dict[str, Any]] = None
    tail: Optional[Dict[str, Any]] = None  # Added Tail slot
    main_hand: Optional[Dict[str, Any]] = None
    off_hand: Optional[Dict[str, Any]] = None

class AccessorySlots(BaseModel):
    # Glasses (1)
    glasses: Optional[Dict[str, Any]] = None
    # Necklaces (1)
    neck: Optional[Dict[str, Any]] = None
    # Earrings (Left: 2, Right: 2)
    ear_l1: Optional[Dict[str, Any]] = None
    ear_l2: Optional[Dict[str, Any]] = None
    ear_r1: Optional[Dict[str, Any]] = None
    ear_r2: Optional[Dict[str, Any]] = None
    # Lip Rings (2)
    lip_1: Optional[Dict[str, Any]] = None
    lip_2: Optional[Dict[str, Any]] = None
    # Bracelets (Left: 2, Right: 2)
    wrist_l1: Optional[Dict[str, Any]] = None
    wrist_l2: Optional[Dict[str, Any]] = None
    wrist_r1: Optional[Dict[str, Any]] = None
    wrist_r2: Optional[Dict[str, Any]] = None
    # Rings (8 total - 4 per hand)
    ring_l1: Optional[Dict[str, Any]] = None
    ring_l2: Optional[Dict[str, Any]] = None
    ring_l3: Optional[Dict[str, Any]] = None
    ring_l4: Optional[Dict[str, Any]] = None
    ring_r1: Optional[Dict[str, Any]] = None
    ring_r2: Optional[Dict[str, Any]] = None
    ring_r3: Optional[Dict[str, Any]] = None
    ring_r4: Optional[Dict[str, Any]] = None
    # Other
    brooch: Optional[Dict[str, Any]] = None
    circlet: Optional[Dict[str, Any]] = None
    belt: Optional[Dict[str, Any]] = None # Kept belt as it was in original, though not explicitly in new list, it's usually standard.
    # Removed 'face', 'outfit' as they seem redundant or replaced by specific slots, 
    # but keeping 'belt' as it is often a distinct slot. 
    # If 'outfit' was cosmetic, it might be covered by 'shoulders/cloak' or just base gear.
    # If 'face' was for masks/glasses, 'glasses' covers it.

class EquipmentSlots(BaseModel):
    combat: CombatSlots = Field(default_factory=CombatSlots)
    accessories: AccessorySlots = Field(default_factory=AccessorySlots)
    equipped_gear: Optional[Dict[str, Any]] = None
    carried_gear: List[Dict[str, Any]] = Field(default_factory=list) # New Carried Gear slot (List of items)

class FeatureChoice(BaseModel):
    """Represents a single feature choice made by the user."""

    feature_id: str  # e.g., "F1", "F9"
    choice_name: str  # e.g., "Predator's Gaze", "Capstone: +2 Might"


class CharacterCreate(BaseModel):
    """
    This is the new complex object sent from the frontend
    to create a new character.
    """

    name: str
    kingdom: str
    # This list should contain all 9 feature choices (F1-F8 + F9)
    feature_choices: List[FeatureChoice]

    # --- MODIFIED: Replaced background_talent ---
    origin_choice: str
    childhood_choice: str
    coming_of_age_choice: str
    training_choice: str
    devotion_choice: str
    # --- END MODIFIED ---

    ability_school: str
    ability_talent: str  # This is the final talent choice, which remains

    # --- ADD THIS LINE ---
    portrait_id: Optional[str] = None # Add the portrait ID here
    # --- END ADD ---


# --- UNCHANGED SCHEMAS ---
class CharacterBase(BaseModel):
    name: str
    kingdom: Optional[str] = None
    level: int = 1


class Character(CharacterBase):
    id: str

    class Config:
        from_attributes = True


class CharacterContextResponse(CharacterBase):
    """
    This is the full character sheet/context object returned
    to the frontend. It is UNCHANGED.
    """

    id: str
    stats: Dict[str, int]
    skills: Dict[str, Any]
    max_hp: int
    current_hp: int

    # --- ADD THIS LINE ---
    temp_hp: int = Field(default=0, description="Current Temporary HP")
    xp: int = Field(default=0, description="Current Experience Points")
    is_dead: bool = Field(default=False, description="Is the character dead?")
    # --- END ADD ---
    max_composure: int
    current_composure: int
    resource_pools: Dict[str, Any]  # e.g., {"Stamina": {"current": 10, "max": 10}, ...}
    talents: List[str]
    abilities: List[str]
    inventory: Dict[str, Any]
    equipment: EquipmentSlots
    status_effects: List[str]
    injuries: List[Dict[str, Any]]

    # --- ADD THIS LINE ---
    current_location_id: int
    dr: int = Field(default=0, description="Total Damage Reduction from all sources.")
    # --- END ADD ---

    position_x: int
    position_y: int

    # --- ADD THIS LINE ---
    portrait_id: Optional[str] = None # Add the portrait ID here
    # --- END ADD ---

    class Config:
        from_attributes = True


class InventoryItem(BaseModel):
    item_id: str
    quantity: int


class InventoryUpdateRequest(BaseModel):
    item_id: str
    quantity: int


class ApplyDamageRequest(BaseModel):
    damage_amount: int
    damage_type: Optional[str] = None


class ApplyStatusRequest(BaseModel):
    status_id: str


class LocationUpdateRequest(BaseModel):
    location_id: int
    coordinates: List[int]
    duration: Optional[int] = None
