import logging
import random
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("monolith.combat.local")

@dataclass
class CombatParticipant:
    id: str
    name: str
    is_player: bool
    hp: int
    max_hp: int
    initiative: int = 0
    team: str = "neutral" # player, enemy, neutral
    status_effects: List[str] = field(default_factory=list)

@dataclass
class CombatState:
    is_active: bool = False
    participants: List[CombatParticipant] = field(default_factory=list)
    turn_order: List[str] = field(default_factory=list) # List of IDs
    current_turn_index: int = 0
    round_number: int = 1
    log: List[str] = field(default_factory=list)

class LocalCombatManager:
    """
    Manages combat state locally without database dependencies.
    """
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.state = CombatState()
        logger.info("LocalCombatManager initialized")

    def start_combat(self, players: List[Dict], enemies: List[Dict]) -> Dict[str, Any]:
        """
        Initializes a new combat encounter.
        
        Args:
            players: List of player dicts (id, name, hp, max_hp)
            enemies: List of enemy dicts (id, name, hp, max_hp)
        """
        logger.info(f"Starting combat: {len(players)} players vs {len(enemies)} enemies")
        
        self.state = CombatState(is_active=True)
        
        # Add Players
        for p in players:
            participant = CombatParticipant(
                id=p['id'],
                name=p['name'],
                is_player=True,
                hp=p.get('hp', 10),
                max_hp=p.get('max_hp', 10),
                team="player"
            )
            self.state.participants.append(participant)
            
        # Add Enemies
        for e in enemies:
            participant = CombatParticipant(
                id=e['id'],
                name=e['name'],
                is_player=False,
                hp=e.get('hp', 10),
                max_hp=e.get('max_hp', 10),
                team="enemy"
            )
            self.state.participants.append(participant)
            
        # Roll Initiative
        self._roll_initiative()
        
        # Notify start
        asyncio.create_task(self.event_bus.publish("combat.started", self.get_state_dict()))
        
        return self.get_state_dict()

    def _roll_initiative(self):
        """Rolls initiative for all participants and sorts turn order."""
        for p in self.state.participants:
            # Simple d20 roll for now. Could add DEX mod later.
            p.initiative = random.randint(1, 20)
            
        # Sort by initiative (descending)
        sorted_participants = sorted(self.state.participants, key=lambda x: x.initiative, reverse=True)
        self.state.turn_order = [p.id for p in sorted_participants]
        self.state.current_turn_index = 0
        self.state.round_number = 1
        
        self._log(f"Initiative rolled. {self.get_active_participant().name} goes first.")

    def get_active_participant(self) -> Optional[CombatParticipant]:
        if not self.state.turn_order:
            return None
        active_id = self.state.turn_order[self.state.current_turn_index]
        return next((p for p in self.state.participants if p.id == active_id), None)

    def handle_action(self, actor_id: str, action_type: str, data: Dict) -> Dict[str, Any]:
        """
        Processes a combat action.
        """
        if not self.state.is_active:
            return {"success": False, "error": "Combat not active"}
            
        active_actor = self.get_active_participant()
        if not active_actor or active_actor.id != actor_id:
            return {"success": False, "error": "Not your turn"}
            
        result = {"success": False, "message": "Unknown action"}
        
        if action_type == "ATTACK":
            result = self._handle_attack(active_actor, data)
        elif action_type == "END_TURN":
            result = self._handle_end_turn()
        elif action_type == "FLEE":
            result = self._handle_flee(active_actor)
            
        # Check win/loss
        self._check_combat_status()
        
        # Publish update
        asyncio.create_task(self.event_bus.publish("combat.updated", self.get_state_dict()))
        
        return result

    def _handle_attack(self, attacker: CombatParticipant, data: Dict) -> Dict:
        target_id = data.get('target_id')
        target = next((p for p in self.state.participants if p.id == target_id), None)
        
        if not target:
            return {"success": False, "error": "Target not found"}
            
        # Simple attack logic
        # Hit chance? For now, auto-hit or simple roll
        roll = random.randint(1, 20)
        hit_threshold = 10 # Placeholder AC
        
        if roll >= hit_threshold:
            damage = random.randint(1, 6) # Placeholder damage
            target.hp -= damage
            self._log(f"{attacker.name} attacks {target.name} (Roll: {roll}) and hits for {damage} damage!")
            
            if target.hp <= 0:
                target.hp = 0
                self._log(f"{target.name} is defeated!")
        else:
            self._log(f"{attacker.name} attacks {target.name} (Roll: {roll}) and misses.")
            
        return {"success": True, "message": "Attack processed"}

    def _handle_end_turn(self) -> Dict:
        self.state.current_turn_index += 1
        if self.state.current_turn_index >= len(self.state.turn_order):
            self.state.current_turn_index = 0
            self.state.round_number += 1
            self._log(f"Round {self.state.round_number} begins.")
            
        next_actor = self.get_active_participant()
        self._log(f"It is now {next_actor.name}'s turn.")
        
        # If next actor is AI (enemy), trigger AI turn (placeholder)
        if not next_actor.is_player:
            asyncio.create_task(self._process_ai_turn(next_actor))
            
        return {"success": True, "message": "Turn ended"}

    async def _process_ai_turn(self, ai_actor: CombatParticipant):
        """Simulates AI turn with a delay."""
        await asyncio.sleep(1.0) # Thinking time
        
        # Find a player target
        targets = [p for p in self.state.participants if p.is_player and p.hp > 0]
        if targets:
            target = random.choice(targets)
            self.handle_action(ai_actor.id, "ATTACK", {"target_id": target.id})
            await asyncio.sleep(0.5)
            self.handle_action(ai_actor.id, "END_TURN", {})
        else:
            # No targets? End turn
            self.handle_action(ai_actor.id, "END_TURN", {})

    def _handle_flee(self, actor: CombatParticipant) -> Dict:
        # Simple 50/50 flee chance
        if random.random() > 0.5:
            self._log(f"{actor.name} fled from combat!")
            # Remove from participants? Or end combat?
            # For simplicity, if player flees, end combat
            if actor.is_player:
                self.state.is_active = False
                asyncio.create_task(self.event_bus.publish("combat.ended", {"result": "fled"}))
            return {"success": True, "message": "Fled successfully"}
        else:
            self._log(f"{actor.name} failed to flee.")
            return self._handle_end_turn() # Lose turn on fail

    def _check_combat_status(self):
        players_alive = any(p.hp > 0 for p in self.state.participants if p.is_player)
        enemies_alive = any(p.hp > 0 for p in self.state.participants if not p.is_player)
        
        if not players_alive:
            self.state.is_active = False
            self._log("All players defeated. Combat lost.")
            asyncio.create_task(self.event_bus.publish("combat.ended", {"result": "defeat"}))
        elif not enemies_alive:
            self.state.is_active = False
            self._log("All enemies defeated. Victory!")
            asyncio.create_task(self.event_bus.publish("combat.ended", {"result": "victory"}))

    def _log(self, message: str):
        self.state.log.append(message)
        logger.info(f"[COMBAT] {message}")

    def get_state_dict(self) -> Dict:
        return asdict(self.state)
