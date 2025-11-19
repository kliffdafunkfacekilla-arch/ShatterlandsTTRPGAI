from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Union, Any

class ItemEffect(BaseModel):
    type: str = Field(..., description="Type of effect: 'heal', 'buff', 'utility', 'damage'")
    value: int = Field(default=0, description="Numeric value of the effect")
    target_stat: Optional[str] = Field(None, description="Stat modified by the effect")
    duration: int = Field(default=0, description="Duration in turns (0 for instant)")
    description: str = Field(..., description="Human readable description")

class Item(BaseModel):
    name: str
    item_type: str = Field(..., description="weapon, armor, consumable, tool, quest, material, charm, book, treasure")
    category: str = Field(..., description="Sub-category matching JSON data keys")
    weight: float = Field(default=0.0, description="Weight in arbitrary units")
    slots: List[str] = Field(default_factory=list, description="Body slots this item occupies")
    effects: List[ItemEffect] = Field(default_factory=list, description="Passive or active effects")
    quantity: int = Field(default=1, description="Stack size")
    max_stack: int = Field(default=1, description="Max stack size")
    value: int = Field(default=0, description="Monetary value in coins")
    
    # Graphics
    icon: Optional[str] = Field(None, description="Icon resource ID")
    sprite_ref: Optional[str] = Field(None, description="Sprite resource ID")

    # Weapon specific
    damage_dice: Optional[str] = None
    range_type: Optional[str] = None # 'melee', 'ranged'
    
    # Armor specific
    dr: int = Field(default=0, description="Damage Reduction")
    
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
