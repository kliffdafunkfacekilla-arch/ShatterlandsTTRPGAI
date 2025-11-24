"""
Services for the camp system.
"""
from sqlalchemy.orm import Session
from monolith.modules.character_pkg import models as character_models
from monolith.modules.character_pkg import services as character_services
from monolith.modules.camp_pkg import schemas as camp_schemas

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

    # Resolve status effects
    # Import rules package for status effect data
    from monolith.modules.rules_pkg import data_loader
    
    # Ensure status effects data is loaded
    if not data_loader.STATUS_EFFECTS:
        data_loader.load_data()
    
    # Track which effects to remove
    effects_to_remove = []
    status_log = []
    
    # Process each active status effect
    if hasattr(character, 'status_effects') and character.status_effects:
        for effect_name in character.status_effects:
            # Get effect data from rules
            effect_data = data_loader.STATUS_EFFECTS.get(effect_name)
            
            if not effect_data:
                # Unknown effect, log warning and remove
                status_log.append(f"Unknown status effect '{effect_name}' removed.")
                effects_to_remove.append(effect_name)
                continue
            
            duration_type = effect_data.get("duration_type", "condition")
            
            # Check if effect should be resolved by rest
            if duration_type == "until_rest":
                # Effects that clear on rest
                effects_to_remove.append(effect_name)
                status_log.append(f"Status effect '{effect_name}' cleared by rest.")
                
            elif duration_type == "time_decay":
                # Time-based effects reduce with rest
                default_duration = effect_data.get("default_duration", 1)
                if rest_request.duration >= default_duration:
                    effects_to_remove.append(effect_name)
                    status_log.append(f"Status effect '{effect_name}' expired.")
                    
            elif duration_type == "condition":
                # Condition-based effects (e.g., "until healed above 50% HP")
                # Check if the condition is met
                if effect_name.lower() in ["bleeding", "wounded"]:
                    # Bleeding/Wounded clears when HP is above 50%
                    if character.current_hp >= character.max_hp * 0.5:
                        effects_to_remove.append(effect_name)
                        status_log.append(f"Status effect '{effect_name}' healed.")
                        
                elif effect_name.lower() in ["exhausted", "fatigued"]:
                    # Exhaustion clears with sufficient rest (4+ hours)
                    if rest_request.duration >= 4:
                        effects_to_remove.append(effect_name)
                        status_log.append(f"Status effect '{effect_name}' removed by rest.")
                        
            # Note: Permanent effects (duration_type == "permanent") are not removed
    
    # Remove expired effects
    if effects_to_remove:
        current_effects = list(character.status_effects) if character.status_effects else []
        for effect in effects_to_remove:
            if effect in current_effects:
                current_effects.remove(effect)
        character.status_effects = current_effects

    db.commit()
    db.refresh(character)

    # Log status effect changes if any
    if status_log:
        print(f"[Camp Rest] {character.name}: " + ", ".join(status_log))

    return character_services.get_character_context(db, character)
