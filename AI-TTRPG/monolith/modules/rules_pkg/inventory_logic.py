from typing import Dict, List, Optional, Tuple, Any
from .models_inventory import Item

def get_passive_modifiers(character: "Character") -> List["PassiveModifier"]:
    """
    Aggregates all passive modifiers from a character's equipped items.
    """
    from ..character_pkg.models import Character
    from .models_inventory import PassiveModifier
    
    modifiers: List[PassiveModifier] = []
    if not isinstance(character.equipment, dict):
        return modifiers

    equipment = character.equipment

    # Iterate through combat and accessory slots
    for category in ["combat", "accessories"]:
        for slot_name, item in equipment.get(category, {}).items():
            if not item:
                continue

            item_id = item.get("id", "unknown_item")

            # Handle direct DR stat
            if "dr" in item and isinstance(item["dr"], int):
                modifiers.append(PassiveModifier(
                    effect_type="DR_MODIFIER",
                    target=slot_name,
                    value=item["dr"],
                    source_id=item_id
                ))

            # Handle effects list
            for effect in item.get("effects", []):
                if effect.get("type") == "buff" and "target_stat" in effect:
                    modifiers.append(PassiveModifier(
                        effect_type="STAT_MODIFIER",
                        target=effect["target_stat"],
                        value=effect.get("value", 0),
                        source_id=item_id
                    ))
    
    return modifiers
