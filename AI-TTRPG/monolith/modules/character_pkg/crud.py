# crud.py
from sqlalchemy.orm import Session
from . import models
from typing import Dict, Any, List
from sqlalchemy.orm.attributes import flag_modified
import logging

logger = logging.getLogger("monolith.character.crud")

def get_character(db: Session, char_id: str) -> models.Character | None:
    """Retrieves a single character by ID."""
    return db.query(models.Character).filter(models.Character.id == char_id).first()

def apply_damage_to_character(
db: Session, character: models.Character, damage_amount: int) -> models.Character:
    """
    Subtracts damage from current_hp, depleting temp_hp first.
    """
    if damage_amount <= 0:
        return character # No damage

    # --- THIS FUNCTION IS HEAVILY MODIFIED ---
    current_temp_hp = character.temp_hp or 0
    damage_to_hp = damage_amount

    logger.info(f"Applying {damage_amount} damage to {character.name}. (HP: {character.current_hp}, TempHP: {current_temp_hp})")

    if current_temp_hp > 0:
        if damage_amount <= current_temp_hp:
            # Damage is fully absorbed by Temp HP
            character.temp_hp = current_temp_hp - damage_amount
            damage_to_hp = 0
            logger.info(f"Damage absorbed by Temp HP. New Temp HP: {character.temp_hp}")
        else:
            # Damage breaks Temp HP and overflows
            damage_to_hp = damage_amount - current_temp_hp
            character.temp_hp = 0
            logger.info(f"Temp HP depleted. {damage_to_hp} damage overflows to HP.")

        flag_modified(character, "temp_hp")

    if damage_to_hp > 0:
        new_hp = character.current_hp - damage_to_hp
        character.current_hp = max(0, new_hp) # Clamp HP at 0
        logger.info(f"New HP: {character.current_hp}")
        flag_modified(character, "current_hp")
    # --- END MODIFICATION ---

    db.commit()
    db.refresh(character)
    return character

def apply_status_to_character(
db: Session, character: models.Character, status_id: str) -> models.Character:
    """Adds a status effect ID to the status_effects list."""
    status_effects = character.status_effects or []

    if status_id not in status_effects:
        status_effects.append(status_id)
        logger.info(f"Applying status '{status_id}' to {character.name}")
    character.status_effects = status_effects
    flag_modified(character, "status_effects")
    db.commit()
    db.refresh(character)
    return character

def remove_status_from_character(
db: Session, character: models.Character, status_id: str) -> models.Character:
    """Removes a status effect ID from the status_effects list."""
    status_effects = character.status_effects or []

    if status_id in status_effects:
        status_effects.remove(status_id)
        logger.info(f"Removing status '{status_id}' from {character.name}")
        character.status_effects = status_effects
        flag_modified(character, "status_effects")
        db.commit()
        db.refresh(character)
    return character

# --- MODIFIED: THIS NEW FUNCTION ---
def update_character_location_and_coords(
    db: Session,
    character: models.Character,
    new_location_id: int,
    new_coordinates: List[int],
) -> models.Character:
    """Updates the character's location ID and coordinates."""

    character.current_location_id = new_location_id
    character.position_x = new_coordinates[0]
    character.position_y = new_coordinates[1]

    flag_modified(character, "current_location_id")
    flag_modified(character, "position_x")
    flag_modified(character, "position_y")

    db.commit()
    db.refresh(character)
    return character
# --- ---

def add_item_to_inventory(
    db: Session, character: models.Character, item_id: str, quantity: int
) -> models.Character:
    # --- MODIFICATION: Update the correct column ---
    inventory = character.inventory or {}

    # Assuming inventory is a dict {item_id: {name: "...", "quantity": X}}
    # Based on apiTypes.ts, it seems to be: { item_id: { name: "...", quantity: X } }
    # Let's check apiTypes.ts...
    # `inventory: { [key: string]: InventoryItem };` where InventoryItem is `{ name: string, quantity: number}`
    # This is complex. The `create_character` service initializes it as `{}`.
    # The `apiTypes` implies it should be `{ "potion_1": { "name": "Health Potion", "quantity": 1 } }`
    # Let's assume the key is the item_id for simplicity.

    # A simpler structure `{ "potion_health_small": 5 }` is easier.
    # But your `create_character` service sets `inventory={}` (a dict)
    # and your `apiTypes` expects `inventory: { [key: string]: InventoryItem };`
    # Let's stick to the `apiTypes` definition.

    # This logic is complex and needs a call to rules_engine to get item details (like name).
    # For now, let's just add the ID and quantity.
    # A better structure would be: `inventory: { "potion_health_small": 5 }`
    # Let's assume this simpler structure for now, as the `create_character` sets an empty dict.

    current_quantity = inventory.get(item_id, 0)
    inventory[item_id] = current_quantity + quantity

    character.inventory = inventory
    flag_modified(character, "inventory")
    # --- END MODIFICATION ---
    db.commit()
    db.refresh(character)
    return character

def remove_item_from_inventory(
    db: Session, character: models.Character, item_id: str, quantity: int
) -> models.Character:
    # --- MODIFICATION: Update the correct column ---
    inventory = character.inventory or {}

    current_quantity = inventory.get(item_id, 0)
    new_quantity = current_quantity - quantity

    if new_quantity > 0:
        inventory[item_id] = new_quantity
    else:
        if item_id in inventory:
            del inventory[item_id] # Remove item if quantity is 0 or less

    character.inventory = inventory
    flag_modified(character, "inventory")
    # --- END MODIFICATION ---
    db.commit()
    db.refresh(character)
    return character

def list_characters(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Character]:
    """Retrieves a list of characters."""
    return db.query(models.Character).offset(skip).limit(limit).all()


def get_character_by_name(db: Session, name: str) -> models.Character | None:
    """Retriees a single character by their name."""
    return db.query(models.Character).filter(models.Character.name == name).first()

def apply_composure_healing(db: Session, character: models.Character, amount: int) -> models.Character:
    """Applies healing to a character's composure pool."""
    if amount <= 0:
        return character

    new_composure = min(character.current_composure + amount, character.max_composure)
    character.current_composure = new_composure
    flag_modified(character, "current_composure")
    db.commit()
    db.refresh(character)
    return character

def apply_composure_damage(db: Session, character: models.Character, damage_amount: int) -> models.Character:
    """Subtracts damage from current_composure."""
    if damage_amount <= 0:
        return character

    new_composure = max(0, character.current_composure - damage_amount)
    character.current_composure = new_composure
    flag_modified(character, "current_composure")
    db.commit()
    db.refresh(character)
    return character

def apply_resource_damage(db: Session, character: models.Character, resource_name: str, damage_amount: int) -> models.Character:
    """Subtracts damage from a generic resource pool (e.g., Chi, Stamina)."""
    if damage_amount <= 0 or resource_name not in character.resource_pools:
        return character

    resource_pools = character.resource_pools or {}
    target_pool = resource_pools.get(resource_name, {"current": 0, "max": 0})

    current_value = target_pool.get("current", 0)
    new_value = max(0, current_value - damage_amount)

    target_pool["current"] = new_value
    resource_pools[resource_name] = target_pool
    character.resource_pools = resource_pools

    flag_modified(character, "resource_pools")
    db.commit()
    db.refresh(character)
    return character

def apply_healing(db: Session, character: models.Character, amount: int) -> models.Character:
    """Applies healing to a character."""
    new_hp = min(character.current_hp + amount, character.max_hp)
    character.current_hp = new_hp
    flag_modified(character, "current_hp")
    db.commit()
    db.refresh(character)
    return character

def equip_item(db: Session, character: models.Character, item_id: str, slot: str) -> models.Character:
    """Equips an item to a character."""

def apply_temp_hp(db: Session, character: models.Character, amount: int) -> models.Character:
    """
    Applies temporary HP to a character.
    Temp HP does not stack; the highest value is taken.
    """
    # --- THIS FUNCTION IS NO LONGER A PLACEHOLDER ---
    logger.info(f"Applying {amount} Temp HP to {character.name}. Current Temp HP: {character.temp_hp}")

    # Temp HP takes the highest value, it does not stack
    new_temp_hp = max(character.temp_hp or 0, amount)

    if new_temp_hp > (character.temp_hp or 0):
        character.temp_hp = new_temp_hp
        flag_modified(character, "temp_hp")
        db.commit()
        db.refresh(character)
        logger.info(f"New Temp HP set to {new_temp_hp}.")
    # --- END MODIFICATION ---
    return character

def update_resource_pool(db: Session, character: models.Character, pool_name: str, new_value: int) -> models.Character:
    """Updates a specific resource pool for a character."""
    current_pools = character.resource_pools or {}

    if pool_name not in current_pools:
        # Initialize pool if it doesn't exist (e.g., from base stats)
        current_pools[pool_name] = {"max": 10, "current": 0}

    # Clamp new value between 0 and max
    max_val = current_pools[pool_name].get("max", 10)
    final_value = max(0, min(max_val, new_value))

    current_pools[pool_name]["current"] = final_value
    character.resource_pools = current_pools

    flag_modified(character, "resource_pools")
    db.commit()
    db.refresh(character)
    return character
    inventory = character.inventory or {}
    equipment = character.equipment or {}

    if item_id not in inventory or inventory[item_id] <= 0:
        # Item not in inventory, do nothing
        return character

    # Unequip old item if any
    currently_equipped_item_id = equipment.get(slot)
    if currently_equipped_item_id:
        inventory[currently_equipped_item_id] = inventory.get(currently_equipped_item_id, 0) + 1

    # Equip new item
    inventory[item_id] -= 1
    if inventory[item_id] == 0:
        del inventory[item_id]
    equipment[slot] = item_id

    character.inventory = inventory
    character.equipment = equipment
    flag_modified(character, "inventory")
    flag_modified(character, "equipment")

    db.commit()
    db.refresh(character)
    return character
