from pydantic import BaseModel, Field
from typing import List, Optional, Union

class ItemEffect(BaseModel):
    """
    Represents a single, direct effect of an item, usually from being used (e.g., a consumable).
    """
    type: str = Field(..., description="Type of effect: 'heal', 'buff', 'utility', 'damage'")
    value: Union[int, str] = Field(default=0, description="Numeric or string value of the effect (e.g., damage amount or a specific condition ID).")
    target_stat: Optional[str] = Field(None, description="Stat modified by the effect, if any.")
    duration: Optional[int] = Field(None, description="Duration in turns (0 for instant, None for permanent while equipped).")
    description: str = Field(..., description="Human-readable description of the effect.")

class Item(BaseModel):
    """
    Represents the static template data for an item, loaded from item_templates.json.
    """
    name: str
    item_type: str = Field(..., description="e.g., weapon, armor, consumable, tool, quest, material, charm, book, treasure")
    category: str = Field(..., description="Sub-category, e.g., 'Double/dual wield', 'potion', 'jewelry'")
    weight: float = Field(default=0.0)
    slots: List[str] = Field(default_factory=list, description="List of valid equipment slots for this item.")
    effects: List[ItemEffect] = Field(default_factory=list)
    quantity: int = Field(default=1)
    max_stack: int = Field(default=1)
    value: int = Field(default=0, description="Monetary value.")
    
    # Graphics
    icon: Optional[str] = None
    sprite_ref: Optional[str] = None

    # Weapon-specific attributes
    damage_dice: Optional[str] = None
    range_type: Optional[str] = None
    
    # Armor-specific attributes
    dr: Optional[int] = Field(None, description="Damage Reduction provided by the item.")
    
    def is_stackable(self) -> bool:
        return self.max_stack > 1

class Inventory(BaseModel):
    items: List[Item] = Field(default_factory=list)
    equipped_slots: Dict[str, Any] = Field(default_factory=lambda: {
        "combat": {
            "head": None, "chest": None, "legs": None, "shoulders": None, 
            "boots": None, "hands": None, "tail": None, "main_hand": None, "off_hand": None
        },
        "accessories": {
            "glasses": None, "neck": None,
            "ear_l1": None, "ear_l2": None, "ear_r1": None, "ear_r2": None,
            "lip_1": None, "lip_2": None,
            "wrist_l1": None, "wrist_l2": None, "wrist_r1": None, "wrist_r2": None,
            "ring_l1": None, "ring_l2": None, "ring_l3": None, "ring_l4": None,
            "ring_r1": None, "ring_r2": None, "ring_r3": None, "ring_r4": None,
            "brooch": None, "circlet": None, "belt": None
        },
        "equipped_gear": None,
        "carried_gear": []
    })
    currency: int = Field(default=0, description="Coins")
    
    def calculate_total_weight(self) -> float:
        total = 0.0
        for item in self.items:
            total += item.weight * item.quantity
        # Add weight of equipped items if they are not in 'items' list 
        # (Assuming equipped items are separate or flagged. 
        # For this model, let's assume 'items' contains EVERYTHING and equipped_slots just references them 
        # OR equipped_slots holds the instances. 
        # Let's go with: items list holds backpack, equipped_slots holds equipped.)
        
        for slot, item in self.equipped_slots.items():
            if item:
                total += item.weight
        return total

class EquipmentSlot(BaseModel):
    name: str
    accepted_item_types: List[str]

class PassiveModifier(BaseModel):
    """
    A standardized representation of a passive effect from an item or talent.
    This is used to aggregate all passive effects for character stat calculation.
    """
    effect_type: str = Field(..., description="The type of modification (e.g., 'STAT_MOD', 'DR_MOD', 'SKILL_MOD').")
    target: str = Field(..., description="The specific stat, skill, or area affected (e.g., 'Might', 'chest', 'Athletics').")
    value: Union[int, float] = Field(..., description="The numeric value of the modification.")
    source_id: Optional[str] = Field(None, description="The ID of the item or talent providing the effect.")

    model_config = {"from_attributes": True}
