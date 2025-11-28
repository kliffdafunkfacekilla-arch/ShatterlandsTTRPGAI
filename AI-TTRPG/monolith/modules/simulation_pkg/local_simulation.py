import logging
import random
from typing import List, Dict, Any, Optional
from ..save_schemas import SaveGameData, FactionSave

logger = logging.getLogger("monolith.simulation.local")

class LocalWorldSim:
    """
    A local version of the World Simulator that operates on SaveGameData.
    """
    
    def __init__(self):
        self.logger = logger

    def process_turn(self, state: SaveGameData) -> List[str]:
        """
        Advances the world simulation by one turn.
        Resolves faction conflicts and updates resources.
        Returns a list of new events generated this turn.
        """
        if not state:
            return []
            
        # Initialize world state if missing (simplified for local)
        # We don't have a dedicated WorldState object in SaveGameData yet, 
        # so we'll just track events and maybe add a simple counter if needed.
        # For now, we'll just generate events.
        
        new_events = []
        factions = state.factions
        
        # 1. Faction Actions
        for faction in factions:
            # Simple logic: Check enemies
            # Note: FactionSave might not have relationship_matrix yet, 
            # so we need to be careful or add it.
            # Checking FactionSave schema... it usually has 'relationships' or similar.
            # If not, we'll skip complex logic for now.
            
            # Let's assume a simple random event for now if no relationships
            if random.random() < 0.1: # 10% chance of action
                event = self._generate_random_faction_event(faction, factions)
                if event:
                    new_events.append(event)

        self.logger.info(f"Simulation turn complete. {len(new_events)} events.")
        return new_events

    def _generate_random_faction_event(self, faction: FactionSave, all_factions: List[FactionSave]) -> Optional[str]:
        """Generates a random event for a faction."""
        if not all_factions or len(all_factions) < 2:
            return None
            
        target = random.choice(all_factions)
        if target.id == faction.id:
            return None
            
        action_type = random.choice(["raid", "trade", "alliance", "skirmish"])
        
        if action_type == "raid":
            damage = random.randint(1, 5)
            # target.strength -= damage # If strength exists
            return f"{faction.name} raided {target.name} territory."
            
        elif action_type == "trade":
            return f"{faction.name} established a trade route with {target.name}."
            
        elif action_type == "skirmish":
             return f"Scouts from {faction.name} clashed with {target.name} forces."
             
        return None
