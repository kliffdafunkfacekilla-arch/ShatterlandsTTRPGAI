from sqlalchemy.orm import Session
from .models import Faction, WorldResource, WorldState, Base
from .database import SessionLocal

def process_turn(db: Session, recent_events: list = None):
    """
    Iterate through all Faction entities.
    If Faction A hates Faction B and has higher strength, reduce Faction B's resource level.
    Log these changes to a text list called recent_events.
    """
    if recent_events is None:
        recent_events = []

    # Get or create WorldState
    world_state = db.query(WorldState).first()
    if not world_state:
        world_state = WorldState(current_tension=0, turn_count=0)
        db.add(world_state)

    world_state.turn_count += 1

    factions = db.query(Faction).all()

    # Simple simulation logic
    for faction in factions:
        relationships = faction.relationship_matrix or {}

        for target_faction_name, status in relationships.items():
            # In a real system, we'd probably use IDs in the matrix, but the prompt example implies names or IDs.
            # Assuming keys are faction names for simplicity or IDs. Let's assume names as strings based on "Goblins" example.
            # But the model says 'faction_id_2'. Let's handle both or assume ID.
            # The prompt example: "Goblins raided the Iron Mine".

            if status == "war":
                # Find target faction
                # If key is name
                target = db.query(Faction).filter(Faction.name == target_faction_name).first()
                if not target:
                    # If key is ID
                    try:
                        target_id = int(target_faction_name)
                        target = db.query(Faction).filter(Faction.id == target_id).first()
                    except ValueError:
                        pass

                if target:
                    if faction.strength > target.strength:
                        # Reduce target resources
                        # Find a resource owned by target
                        resource = db.query(WorldResource).filter(WorldResource.owner_faction_id == target.id).first()
                        if resource:
                            reduction = 5
                            resource.abundance_level = max(0, resource.abundance_level - reduction)
                            event = f"{faction.name} raided {target.name}'s {resource.type}."
                            recent_events.append(event)

                            # Also slightly increase tension
                            world_state.current_tension = min(100, world_state.current_tension + 1)
                        else:
                             # Direct damage to strength if no resources?
                            damage = 2
                            target.strength = max(0, target.strength - damage)
                            event = f"{faction.name} attacked {target.name} forces directly."
                            recent_events.append(event)

    db.commit()
    return recent_events
