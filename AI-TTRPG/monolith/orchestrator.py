"""
Enhanced Orchestrator: Central coordinator for local monolith TTRPG.

Responsibilities:
- Manage GameStateManager for hotseat multiplayer
- Dispatch player actions to appropriate game logic modules
- Integrate with Event Bus for UI reactivity
- Coordinate async AI DM narrative generation
- Handle save/load operations
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import core components
from .event_bus import get_event_bus
from .modules.save_schemas import SaveGameData, CharacterSave
from .modules import save_manager

logger = logging.getLogger("monolith.orchestrator")


class GameStateManager:
    """Manages the live game state and hotseat player rotation.
    
    This is the single source of truth for the current game state.
    """
    
    def __init__(self):
        self.current_state: Optional[SaveGameData] = None
        self.active_player_index: int = 0
        self.save_slot_name: str = "CurrentSave"
        logger.info("GameStateManager initialized")
    
    def load_state(self, save_data: SaveGameData, slot_name: str = "CurrentSave"):
        """Load a game state into the manager.
        
        Args:
            save_data: Complete game state from save file
            slot_name: Name of the save slot
        """
        self.current_state = save_data
        self.save_slot_name = slot_name
        self.active_player_index = 0
        logger.info(f"Game state loaded: {len(save_data.characters)} characters")
    
    def get_current_state(self) -> Optional[SaveGameData]:
        """Get read-only view of current game state."""
        return self.current_state
    
    def get_active_player(self) -> Optional[CharacterSave]:
        """Get the currently active player character."""
        if not self.current_state or not self.current_state.characters:
            return None
        return self.current_state.characters[self.active_player_index]
    
    def get_active_player_id(self) -> Optional[str]:
        """Get the active player's ID."""
        player = self.get_active_player()
        return player.id if player else None
    
    def switch_active_player(self) -> Optional[CharacterSave]:
        """Rotate to the next player in hotseat order.
        
        Returns:
            The newly active player
        """
        if not self.current_state or not self.current_state.characters:
            logger.warning("Cannot switch player: no characters loaded")
            return None
        
        # Rotate to next player (circular)
        num_players = len(self.current_state.characters)
        self.active_player_index = (self.active_player_index + 1) % num_players
        
        next_player = self.get_active_player()
        logger.info(f"Switched to player: {next_player.name}")
        
        return next_player
    
    def apply_state_change(self, new_state: SaveGameData, auto_save: bool = True):
        """Update the current state and optionally save to disk.
        
        Args:
            new_state: Updated game state
            auto_save: Whether to automatically save to disk
        """
        self.current_state = new_state
        
        if auto_save:
            self.save_current_game()
    
    def save_current_game(self) -> Dict[str, Any]:
        """Save the current game state to disk."""
        if not self.current_state:
            return {"success": False, "error": "No game state loaded"}
        
        active_player = self.get_active_player()
        return save_manager.save_game(
            data=self.current_state,
            slot_name=self.save_slot_name,
            active_character_id=active_player.id if active_player else None,
            active_character_name=active_player.name if active_player else None
        )


class Orchestrator:
    """Central coordinator for the local monolith architecture.
    
    Manages game state, dispatches actions, and coordinates all subsystems.
    """
    
    def __init__(self) -> None:
        self.state_manager = GameStateManager()
        self.event_bus = get_event_bus()
        self._lock = asyncio.Lock()
        self._initialized = False
        logger.info("Orchestrator initialized")
    
    # -------------------------------------------------------------------------
    # Initialization & Lifecycle
    # -------------------------------------------------------------------------
    
    async def initialize_engine(self):
        """Initialize the game engine and load static data.
        
        This should be called once at application startup.
        """
        if self._initialized:
            logger.warning("Engine already initialized")
            return
        
        logger.info("Initializing game engine...")
        
        # Load and validate all JSON rules from data directory
        try:
            from .modules.rules_pkg.data_loader_enhanced import load_and_validate_all
            rules_summary = load_and_validate_all()
            logger.info(f"Rules loaded: {rules_summary}")
        except Exception as e:
            logger.exception(f"Failed to load rules data: {e}")
            await self.event_bus.publish("engine.initialization_failed", {"error": str(e)})
            raise
        
        self._initialized = True
        await self.event_bus.publish("engine.initialized", {})
        logger.info("Game engine initialization complete")
    
    def shutdown(self):
        """Gracefully shut down the orchestrator."""
        logger.info("Orchestrator shutting down...")
        # Save current game if loaded
        if self.state_manager.current_state:
            self.state_manager.save_current_game()
    
    # -------------------------------------------------------------------------
    # Game Creation & Loading
    # -------------------------------------------------------------------------
    
    async def start_new_game(self, character_json_paths: List[str]) -> Dict[str, Any]:
        """Initialize a new game from character JSON files.
        
        Args:
            character_json_paths: List of paths to character JSON files
            
        Returns:
            Result dictionary with success status
        """
        try:
            logger.info(f"Starting new game with {len(character_json_paths)} characters")
            
            # Load and validate each character
            characters = []
            for char_path in character_json_paths:
                result = save_manager.load_character_from_json(char_path)
                if not result["success"]:
                    return result  # Return error
                characters.append(result["character"])
            
            logger.info(f"Loaded {len(characters)} characters")
            
            # TODO: Generate initial world state
            # from .modules.map_pkg.core import generate_starting_map
            # world_state = generate_starting_map()
            
            # TODO: Initialize story state
            # from .modules.story_pkg.services import start_new_quest_line
            # story_state = start_new_quest_line()
            
            # For now, create minimal game state
            game_state = SaveGameData(
                characters=characters,
                factions=[],
                regions=[],
                locations=[],
                npcs=[],
                items=[],
                traps=[],
                campaigns=[],
                campaign_states=[],
                quests=[],
                flags=[]
            )
            
            # Load into state manager
            self.state_manager.load_state(game_state)
            
            # Initial save
            save_result = self.state_manager.save_current_game()
            
            if save_result["success"]:
                await self.event_bus.publish("game.started", {
                    "num_players": len(characters),
                    "save_path": save_result["path"]
                })
                
                logger.info("New game started successfully")
                return {
                    "success": True,
                    "num_players": len(characters),
                    "save_path": save_result["path"]
                }
            else:
                return save_result
            
        except Exception as e:
            logger.exception(f"Failed to start new game: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def load_game(self, slot_name: str) -> Dict[str, Any]:
        """Load an existing game from a save file.
        
        Args:
            slot_name: Name of the save slot to load
            
        Returns:
            Result dictionary with success status
        """
        try:
            logger.info(f"Loading game from slot: {slot_name}")
            
            result = save_manager.load_game(slot_name)
            
            if not result["success"]:
                return result
            
            save_file = result["save_file"]
            self.state_manager.load_state(save_file.data, slot_name)
            
            await self.event_bus.publish("game.loaded", {
                "slot_name": slot_name,
                "num_players": len(save_file.data.characters)
            })
            
            logger.info("Game loaded successfully")
            return {
                "success": True,
                "slot_name": slot_name,
                "timestamp": save_file.save_time
            }
            
        except Exception as e:
            logger.exception(f"Failed to load game: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # -------------------------------------------------------------------------
    # Player Action Handling
    # -------------------------------------------------------------------------
    
    async def handle_player_action(
        self,
        player_id: str,
        action_type: str,
        **action_data
    ) -> Dict[str, Any]:
        """Main dispatcher for all player actions.
        
        Args:
            player_id: ID of the player taking the action
            action_type: Type of action (MOVE, ABILITY, DIALOGUE, etc.)
            **action_data: Additional action-specific data
            
        Returns:
            Result dictionary with action outcome
        """
        async with self._lock:
            try:
                logger.info(f"Processing action: {action_type} from {player_id}")
                
                # Verify it's the active player's turn
                active_id = self.state_manager.get_active_player_id()
                if player_id != active_id:
                    return {
                        "success": False,
                        "error": f"Not {player_id}'s turn (active player: {active_id})"
                    }
                
                current_state = self.state_manager.get_current_state()
                
                # Dispatch based on action type
                if action_type == "MOVE":
                    result = await self._handle_movement(current_state, player_id, action_data)
                elif action_type == "ABILITY":
                    result = await self._handle_ability(current_state, player_id, action_data)
                elif action_type == "DIALOGUE":
                    result = await self._handle_dialogue(current_state, player_id, action_data)
                elif action_type == "END_TURN":
                    result = await self._handle_end_turn(current_state, player_id, action_data)
                else:
                    return {
                        "success": False,
                        "error": f"Unknown action type: {action_type}"
                    }
                
                return result
                
            except Exception as e:
                logger.exception(f"Action handling failed: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
    
    # -------------------------------------------------------------------------
    # Action Handlers (Stubs for now - to be implemented with game logic)
    # -------------------------------------------------------------------------
    
    async def _handle_movement(
        self,
        current_state: SaveGameData,
        player_id: str,
        data: dict
    ) -> Dict[str, Any]:
        """Handle player movement action."""
        logger.info(f"Movement: {player_id} -> {data.get('direction')}")
        
        # TODO: Implement movement logic
        # - Validate movement
        # - Update character position
        # - Check for encounters
        # - Generate AI narrative
        
        await self.event_bus.publish("action.move", {
            "player_id": player_id,
            "direction": data.get('direction')
        })
        
        return {
            "success": True,
            "action": "move",
            "message": "Movement not yet implemented"
        }
    
    async def _handle_ability(
        self,
        player_id: str,
        data: dict
    ) -> Dict[str, Any]:
        """Handle dialogue/NPC interaction."""
        logger.info(f"Dialogue: {player_id} with {data.get('npc_id')}")
        
        # TODO: Implement dialogue system with AI DM
        
        await self.event_bus.publish("action.dialogue", {
            "player_id": player_id,
            "npc_id": data.get('npc_id')
        })
        
        return {
            "success": True,
            "action": "dialogue",
            "message": "Dialogue system not yet implemented"
        }
    
    async def _handle_end_turn(
        self,
        current_state: SaveGameData,
        player_id: str,
        data: dict
    ) -> Dict[str, Any]:
        """Handle end of player turn (hotseat rotation)."""
        logger.info(f"End turn: {player_id}")
        
        # Switch to next player
        next_player = self.state_manager.switch_active_player()
        
        # Publish event for UI update
        await self.event_bus.publish("player.turn_start", {
            "player_id": next_player.id,
            "player_name": next_player.name
        })
        
        return {
            "success": True,
            "action": "end_turn",
            "next_player": next_player.name,
            "next_player_id": next_player.id
        }
    
    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    
    def get_current_state(self) -> Optional[SaveGameData]:
        """Get the current game state (read-only)."""
        return self.state_manager.get_current_state()
    
    def get_active_player(self) -> Optional[CharacterSave]:
        """Get the currently active player."""
        return self.state_manager.get_active_player()


# Module-level singleton
_orchestrator_instance: Optional[Orchestrator] = None

def get_orchestrator() -> Orchestrator:
    """Return the singleton Orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = Orchestrator()
    return _orchestrator_instance
