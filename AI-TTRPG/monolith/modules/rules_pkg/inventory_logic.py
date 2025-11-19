from typing import Dict, List, Optional, Tuple
from .models_inventory import Inventory, Item, EquipmentSlot

# Define standard slots
SLOTS = {
    "Head": ["armor", "accessory"],
    "Chest": ["armor"],
    "Shoulders": ["armor"],
    "Arms": ["armor"],
    "Legs": ["armor"],
    "Boots": ["armor"],
    "Tail": ["armor", "accessory"],
    "Hands": ["armor", "gloves"],
    "Main Hand": ["weapon", "tool", "shield"],
    "Off Hand": ["weapon", "tool", "shield", "consumable"], # Consumable in hand to use?
    "Accessory 1": ["accessory"],
    "Accessory 2": ["accessory"],
    "Quick Slot 1": ["consumable", "tool"],
    "Quick Slot 2": ["consumable", "tool"]
}

def equip_item(inventory: Inventory, item: Item, slot_name: str) -> Tuple[bool, str]:
    """
    Equips an item to a specific slot.
    Returns (success, message).
    """
    if slot_name not in SLOTS:
        return False, f"Invalid slot: {slot_name}"
    
    # Check if item is allowed in this slot
    # This is a basic check, might need more robust category checking
    allowed_types = SLOTS[slot_name]
    if item.item_type not in allowed_types and "all" not in allowed_types:
        # Relaxed check for now, or strict? 
        # Let's assume item.slots contains valid slots if defined
        if item.slots and slot_name not in item.slots:
             return False, f"Item {item.name} cannot be equipped in {slot_name}. Valid slots: {item.slots}"
    
    # Check if slot is occupied
    current_item = inventory.equipped_slots.get(slot_name)
    if current_item:
        unequip_item(inventory, slot_name)
        
    # Equip
    inventory.equipped_slots[slot_name] = item
    # Remove from main inventory list if we want to track unique instances
    # For now, let's assume inventory.items is the "bag" and equipped is separate.
    if item in inventory.items:
        inventory.items.remove(item)
        
    return True, f"Equipped {item.name} to {slot_name}"

def unequip_item(inventory: Inventory, slot_name: str) -> Tuple[bool, str]:
    """
    Unequips an item from a slot and returns it to the bag.
    """
    if slot_name not in inventory.equipped_slots:
        return False, "Slot not found"
        
    item = inventory.equipped_slots[slot_name]
    if not item:
        return False, "Slot is empty"
        
    inventory.equipped_slots[slot_name] = None
    inventory.items.append(item)
    return True, f"Unequipped {item.name}"

def use_item(inventory: Inventory, item: Item, target_context: Dict = None) -> Tuple[bool, str, Dict]:
    """
    Uses an item (consumable, tool).
    Returns (success, message, effect_data).
    """
    if item.item_type not in ["consumable", "tool", "readable"]:
        return False, "Item is not usable", {}
        
    effect_result = {}
    
    # Process effects
    for effect in item.effects:
        if effect.type == "heal":
            effect_result["heal"] = effect.value
        elif effect.type == "buff":
            effect_result["buff"] = {
                "stat": effect.target_stat,
                "value": effect.value,
                "duration": effect.duration
            }
            
    # Consume if applicable
    if item.item_type == "consumable":
        if item.quantity > 1:
            item.quantity -= 1
        else:
            if item in inventory.items:
                inventory.items.remove(item)
            # Check equipped slots (e.g. Quick Slots)
            for slot, equipped in inventory.equipped_slots.items():
                if equipped == item:
                    inventory.equipped_slots[slot] = None
                    
    return True, f"Used {item.name}", effect_result

def calculate_encumbrance(inventory: Inventory, weight_capacity: float) -> str:
    total_weight = inventory.calculate_total_weight()
    if total_weight <= weight_capacity:
        return "Light"
    elif total_weight <= weight_capacity * 1.5:
        return "Heavy" # -1 Movement?
    else:
        return "Overburdened" # No movement?
