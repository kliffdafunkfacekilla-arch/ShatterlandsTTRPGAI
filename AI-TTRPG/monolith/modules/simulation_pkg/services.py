import logging
from sqlalchemy.orm import Session
from . import models
from typing import List, Dict, Any
import random

logger = logging.getLogger("monolith.simulation")

def get_world_state(db: Session) -> models.WorldState:
    """Retrieves or creates the singleton WorldState."""
    state = db.query(models.WorldState).first()
    if not state:
        state = models.WorldState(current_tension=10, turn_count=0, recent_events=[])
        db.add(state)
        db.commit()
        db.refresh(state)
    return state

def process_turn(db: Session) -> List[str]:
    """
    Advances the world simulation by one turn.
    Resolves faction conflicts and updates resources.
    Returns a list of new events generated this turn.
    """
    state = get_world_state(db)
    state.turn_count += 1
    
    new_events = []
    factions = db.query(models.Faction).all()
    
    # 1. Faction Actions
    for faction in factions:
        # Simple logic: Check enemies
        if not faction.relationship_matrix:
            continue
            
        for target_name, relation in faction.relationship_matrix.items():
            if relation < -20: # Hostile
                target = db.query(models.Faction).filter(models.Faction.name == target_name).first()
                if target:
                    # Conflict Resolution
                    if faction.strength > target.strength:
                        # Raid/Attack success
                        damage = random.randint(1, 5)
                        target.strength = max(0, target.strength - damage)
                        event_msg = f"{faction.name} raided {target.name}, reducing their strength by {damage}."
                        new_events.append(event_msg)
                        
                        # Tension rises
                        state.current_tension = min(100, state.current_tension + 2)
                    else:
                        # Failed attack
                        event_msg = f"{faction.name} skirmished with {target.name} but was repelled."
                        new_events.append(event_msg)

    # 2. Resource Updates (Placeholder)
    # In a real sim, resources would fluctuate or be consumed.
    
    # 3. Update World State
    # Append new events to history (keep last 50)
    current_history = state.recent_events or []
    updated_history = current_history + new_events
    state.recent_events = updated_history[-50:]
    
    db.commit()
    db.refresh(state)
    
    logger.info(f"Simulation Turn {state.turn_count} complete. {len(new_events)} events generated.")
    return new_events

def get_world_context_summary(db: Session) -> str:
    """
    Returns a natural language summary of the world state for the AI.
    """
    state = get_world_state(db)
    factions = db.query(models.Faction).all()
    
    summary = [f"Turn: {state.turn_count}", f"Global Tension: {state.current_tension}/100"]
    
    summary.append("Factions:")
    for f in factions:
        summary.append(f"- {f.name} (Str: {f.strength}): {f.goals}")
        
    summary.append("Recent Events:")
    if state.recent_events:
        for event in state.recent_events[-5:]: # Last 5 events
            summary.append(f"- {event}")
    else:
        summary.append("- None")
        
    return "\n".join(summary)
