"""
Services for the camp system.
"""
from sqlalchemy.orm import Session
from AI-TTRPG.monolith.modules.character_pkg import models as character_models
from AI-TTRPG.monolith.modules.character_pkg import services as character_services
from AI-TTRPG.monolith.modules.camp_pkg import schemas as camp_schemas

def rest_at_camp(db: Session, rest_request: camp_schemas.CampRestRequest):
    """
    Executes a rest action at a campsite.

    Restores HP and Composure based on the duration of the rest.
    Future logic will include status effect resolution and resource consumption.

    Args:
        db (Session): Database session.
        rest_request (camp_schemas.CampRestRequest): The rest request parameters (char_id, duration).

    Returns:
        schemas.CharacterContextResponse: The updated character context.

    Raises:
        ValueError: If the character ID is not found.
    """
    character = db.query(character_models.Character).filter(character_models.Character.id == rest_request.char_id).first()
    if not character:
        raise ValueError("Character not found")

    # For now, let's assume a simple healing rate.
    healing_rate = 10  # HP and Composure per hour
    hp_to_heal = healing_rate * rest_request.duration
    composure_to_heal = healing_rate * rest_request.duration

    character.current_hp = min(character.max_hp, character.current_hp + hp_to_heal)
    character.current_composure = min(character.max_composure, character.current_composure + composure_to_heal)

    # TODO: Resolve status effects

    db.commit()
    db.refresh(character)

    return character_services.get_character_context(db, character)
