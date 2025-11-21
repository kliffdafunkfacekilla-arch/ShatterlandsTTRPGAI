"""
Handles experience gain and character leveling.
"""
from sqlalchemy.orm import Session
from monolith.modules.character_pkg import models as character_models
from monolith.modules.rules_pkg import data_loader

def add_experience(db: Session, char_id: str, xp_amount: int):
    """
    Adds experience to a character and handles leveling up.
    """
    character = db.query(character_models.Character).filter(character_models.Character.id == char_id).first()
    if not character:
        raise ValueError("Character not found")

    character.xp += xp_amount

    # Check for level up
    generation_rules = data_loader.get_generation_rules()
    xp_threshold = generation_rules["xp_per_level"].get(str(character.level + 1))

    if xp_threshold and character.xp >= xp_threshold:
        character.level += 1
        # Apply stat increases or other level-up benefits here.
        # For now, we'll just increment the level.

    db.commit()
    db.refresh(character)

    return character
