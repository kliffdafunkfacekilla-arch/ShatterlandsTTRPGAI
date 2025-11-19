from typing import Dict, List, Optional, Tuple, Any
from .models_inventory import Inventory, Item

# Define valid slots and their allowed categories
COMBAT_SLOTS = {
    "head": ["armor", "accessory"],
    "chest": ["armor"],
    "legs": ["armor"],
    "shoulders": ["armor"],
    "boots": ["armor"],
    "hands": ["armor", "gloves"],
    "tail": ["armor", "accessory"],
    "main_hand": ["weapon", "tool", "shield"],
    "off_hand": ["weapon", "tool", "shield", "consumable", "utility"],
}

ACCESSORY_SLOTS = {
    "glasses": ["accessory"],
    "neck": ["accessory", "jewelry", "charm"],
    "ear_l1": ["accessory", "jewelry"],
    "ear_l2": ["accessory", "jewelry"],
    "ear_r1": ["accessory", "jewelry"],
    "ear_r2": ["accessory", "jewelry"],
    "lip_1": ["accessory", "jewelry"],
    "lip_2": ["accessory", "jewelry"],
    "wrist_l1": ["accessory", "jewelry", "charm"],
    "wrist_l2": ["accessory", "jewelry", "charm"],
    "wrist_r1": ["accessory", "jewelry", "charm"],
    "wrist_r2": ["accessory", "jewelry", "charm"],
    "ring_l1": ["accessory", "jewelry"],
    "ring_l2": ["accessory", "jewelry"],
    "ring_l3": ["accessory", "jewelry"],
    "ring_l4": ["accessory", "jewelry"],
    "ring_r1": ["accessory", "jewelry"],
    "ring_r2": ["accessory", "jewelry"],
    "ring_r3": ["accessory", "jewelry"],
    "ring_r4": ["accessory", "jewelry"],
    "brooch": ["accessory", "jewelry"],
    "circlet": ["accessory", "jewelry"],
    "belt": ["accessory", "clothing"],
}

def _get_slot_location(inventory: Inventory, slot_name: str) -> Tuple[Optional[Dict], Optional[str], Optional[List]]:
    """
    Helper to find where a slot lives in the nested inventory structure.
    Returns (parent_dict, key, parent_list)
    - If it's a dict slot, parent_list is None.
    - If it's a list slot (carried_gear), parent_dict and key are None.
    """
    if slot_name in COMBAT_SLOTS:
        return inventory.equipped_slots["combat"], slot_name, None
    elif slot_name in ACCESSORY_SLOTS:
        return inventory.equipped_slots["accessories"], slot_name, None
    elif slot_name == "equipped_gear":
        return inventory.equipped_slots, "equipped_gear", None
    elif slot_name == "carried_gear":
        return None, None, inventory.equipped_slots["carried_gear"]
    return None, None, None

def equip_item(inventory: Inventory, item: Item, slot_name: str) -> Tuple[bool, str]:
    """
    Equips an item to a specific slot.
    Returns (success, message).
    """
    # 1. Validate Slot Existence
    parent_dict, key, parent_list = _get_slot_location(inventory, slot_name)
    if parent_dict is None and parent_list is None:
        return False, f"Invalid slot: {slot_name}"

    # 2. Validate Item Type for Slot
    allowed_types = []
    if slot_name in COMBAT_SLOTS:
        allowed_types = COMBAT_SLOTS[slot_name]
    elif slot_name in ACCESSORY_SLOTS:
        allowed_types = ACCESSORY_SLOTS[slot_name]
    elif slot_name == "equipped_gear":
        allowed_types = ["tool", "consumable", "utility", "charm"]
    elif slot_name == "carried_gear":
        allowed_types = ["all"] # Anything can be carried? Or just tools/consumables? Let's say all for now.

    if "all" not in allowed_types:
        # Check item.item_type AND item.category
        # Also check if item specifically lists this slot
        valid_type = item.item_type in allowed_types or item.category in allowed_types
        valid_slot_ref = item.slots and (slot_name in item.slots or "equipped_gear" in item.slots and slot_name == "equipped_gear")
        
        if not valid_type and not valid_slot_ref:
             return False, f"Item {item.name} ({item.item_type}/{item.category}) cannot be equipped in {slot_name}."

    # 3. Handle Unequip if Occupied (for Dict slots)
    if parent_dict is not None:
        current_item = parent_dict.get(key)
        if current_item:
            success, msg = unequip_item(inventory, slot_name)
            if not success:
                return False, f"Failed to unequip existing item: {msg}"

        # 4. Equip
        parent_dict[key] = item
    
    # 5. Handle List slots (Carried Gear)
    elif parent_list is not None:
        # Optional: Check capacity for carried gear?
        if len(parent_list) >= 10: # Arbitrary limit
            return False, "Carried gear slots are full."
        parent_list.append(item)

    # 6. Remove from main inventory
    if item in inventory.items:
        inventory.items.remove(item)

    return True, f"Equipped {item.name} to {slot_name}"

def unequip_item(inventory: Inventory, slot_name: str, item_to_remove: Item = None) -> Tuple[bool, str]:
    """
    Unequips an item from a slot and returns it to the bag.
    For list slots, item_to_remove must be specified.
    """
    parent_dict, key, parent_list = _get_slot_location(inventory, slot_name)
    
    if parent_dict is None and parent_list is None:
        return False, "Invalid slot"

    item = None
    
    if parent_dict is not None:
        item = parent_dict.get(key)
        if not item:
            return False, "Slot is empty"
        parent_dict[key] = None
        
    elif parent_list is not None:
        if not item_to_remove:
            return False, "Must specify item to remove from carried gear"
        if item_to_remove not in parent_list:
            return False, "Item not found in carried gear"
        item = item_to_remove
        parent_list.remove(item)

    if item:
        inventory.items.append(item)
        return True, f"Unequipped {item.name}"
        
    return False, "Unknown error"

def use_item(inventory: Inventory, item: Item, target_context: Dict = None) -> Tuple[bool, str, Dict]:
    """
    Uses an item (consumable, tool).
    Returns (success, message, effect_data).
    """
    if item.item_type not in ["consumable", "tool", "readable", "charm"]:
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
        elif effect.type == "damage":
             effect_result["damage"] = {
                 "value": effect.value,
                 "description": effect.description
             }
        elif effect.type == "utility":
            effect_result["utility"] = effect.description
            
    # Consume if applicable
    should_consume = item.item_type in ["consumable", "charm"]
    
    if should_consume:
        if item.quantity > 1:
            item.quantity -= 1
        else:
            # Remove from wherever it is
            if item in inventory.items:
                inventory.items.remove(item)
            else:
                # Check equipped slots
                # This is expensive, maybe optimize later
                found = False
                for s_name in COMBAT_SLOTS:
                    if inventory.equipped_slots["combat"].get(s_name) == item:
                        inventory.equipped_slots["combat"][s_name] = None
                        found = True
                        break
                if not found:
                    for s_name in ACCESSORY_SLOTS:
                        if inventory.equipped_slots["accessories"].get(s_name) == item:
                            inventory.equipped_slots["accessories"][s_name] = None
                            found = True
                            break
                if not found and inventory.equipped_slots.get("equipped_gear") == item:
                     inventory.equipped_slots["equipped_gear"] = None
                     found = True
                if not found and item in inventory.equipped_slots["carried_gear"]:
                    inventory.equipped_slots["carried_gear"].remove(item)
                    found = True

    return True, f"Used {item.name}", effect_result

def calculate_encumbrance(inventory: Inventory, weight_capacity: float) -> str:
    total_weight = inventory.calculate_total_weight()
    if total_weight <= weight_capacity:
        return "Light"
    elif total_weight <= weight_capacity * 1.5:
        return "Heavy" 
    else:
        return "Overburdened"
