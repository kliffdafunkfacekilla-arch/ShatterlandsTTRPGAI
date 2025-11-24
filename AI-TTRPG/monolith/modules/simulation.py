from .simulation_pkg import models
from .simulation_pkg.database import SessionLocal
from .simulation_pkg.services import process_turn

def get_world_context() -> str:
    """
    Returns a simplified string summary of the simulation state
    (e.g., "War brewing between Goblins and Humans") for the AI to read.
    """
    db = SessionLocal()
    try:
        world_state = db.query(models.WorldState).first()
        factions = db.query(models.Faction).all()

        tension = world_state.current_tension if world_state else 0
        turn = world_state.turn_count if world_state else 0

        summary = [f"Turn: {turn}, Global Tension: {tension}/100"]

        for faction in factions:
            relationships = faction.relationship_matrix or {}
            active_conflicts = [target for target, status in relationships.items() if status == "war"]
            if active_conflicts:
                summary.append(f"{faction.name} is at war with: {', '.join(active_conflicts)}.")

        # Add high level resource info
        # e.g. "Goblins control Iron Mine (Abundance: 20)"
        resources = db.query(models.WorldResource).all()
        for res in resources:
            if res.owner_faction:
                summary.append(f"{res.owner_faction.name} controls {res.type} (Abundance: {res.abundance_level})")

        return "\n".join(summary)
    finally:
        db.close()

def run_simulation_turn() -> list:
    """
    Triggers the turn processing logic.
    """
    db = SessionLocal()
    try:
        events = process_turn(db)
        return events
    finally:
        db.close()
