"""
Handles shop and barter logic.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session

# Fix imports to match correct relative pathing or package structure if needed,
# but based on file structure these absolute imports look suspicious if running from root.
# Assuming standard structure:
from ..character_pkg import services as character_services
from ..character_pkg import models as character_models
from ..rules_pkg import data_loader

# For now, a simple in-memory shop inventory.
# In the future, this could be loaded from a file or database.
_shop_inventories: Dict[str, Dict[str, Any]] = {
    "willows_wares": {
        "name": "Willow's Wares",
        "inventory": {
            "item_health_potion_small": {"price": 25, "quantity": 10},
            "item_iron_sword": {"price": 100, "quantity": 2},
            "item_leather_jerkin": {"price": 75, "quantity": 3},
        }
    }
}

def get_shop_inventory(shop_id: str) -> Dict[str, Any]:
    """
    Retrieves the inventory for a specific shop.

    Args:
        shop_id (str): The unique identifier of the shop.

    Returns:
        Dict[str, Any]: The shop's data, including its inventory.

    Raises:
        ValueError: If the shop ID is not found.
    """
    if shop_id not in _shop_inventories:
        raise ValueError(f"Shop '{shop_id}' not found.")
    return _shop_inventories[shop_id]

def buy_item(db: Session, char_id: str, shop_id: str, item_id: str, quantity: int):
    """
    Executes a purchase transaction.

    Verifies the shop has stock and the character has funds.
    Deducts currency and adds the item to the character's inventory.

    Args:
        db (Session): Database session.
        char_id (str): Character ID.
        shop_id (str): Shop ID.
        item_id (str): Item ID to buy.
        quantity (int): Amount to buy.

    Returns:
        schemas.CharacterContextResponse: Updated character context.

    Raises:
        ValueError: If validation fails (insufficient funds/stock).
    """
    character = db.query(character_models.Character).filter(character_models.Character.id == char_id).first()
    if not character:
        raise ValueError("Character not found")

    shop = get_shop_inventory(shop_id)
    shop_item = shop["inventory"].get(item_id)

    if not shop_item:
        raise ValueError("Item not found in shop")
    if shop_item["quantity"] < quantity:
        raise ValueError("Shop does not have enough of that item")

    total_cost = shop_item["price"] * quantity
    if character.inventory["currency"] < total_cost:
        raise ValueError("Not enough currency")

    # Perform transaction
    character.inventory["currency"] -= total_cost
    shop_item["quantity"] -= quantity

    # Add item to character inventory
    character_services.add_item_to_inventory(db, character, item_id, quantity)

    db.commit()
    db.refresh(character)

    return character_services.get_character_context(db, character)

def sell_item(db: Session, char_id: str, shop_id: str, item_id: str, quantity: int):
    """
    Executes a sale transaction.

    Verifies the character has the item. Calculates sell price (currently 50% value).
    Removes item from character and adds currency.

    Args:
        db (Session): Database session.
        char_id (str): Character ID.
        shop_id (str): Shop ID.
        item_id (str): Item ID to sell.
        quantity (int): Amount to sell.

    Returns:
        schemas.CharacterContextResponse: Updated character context.

    Raises:
        ValueError: If character does not have the item.
    """
    character = db.query(character_models.Character).filter(character_models.Character.id == char_id).first()
    if not character:
        raise ValueError("Character not found")

    # Check if character has the item
    char_item_count = character.inventory["carried_gear"].get(item_id, 0)
    if char_item_count < quantity:
        raise ValueError("You do not have enough of that item to sell")

    item_template = data_loader.get_item_template(item_id)
    # Sell price is typically a fraction of the base value.
    sell_price = item_template.value // 2 * quantity

    # Perform transaction
    character.inventory["currency"] += sell_price
    character_services.remove_item_from_inventory(db, character, item_id, quantity)

    # Add item to shop inventory
    shop = get_shop_inventory(shop_id)
    if item_id in shop["inventory"]:
        shop["inventory"][item_id]["quantity"] += quantity
    else:
        # If the shop doesn't carry it, use the template value as the price.
        shop["inventory"][item_id] = {"price": item_template.value, "quantity": quantity}

    db.commit()
    db.refresh(character)

    return character_services.get_character_context(db, character)
