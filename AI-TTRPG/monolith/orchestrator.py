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
        
        # Initialize Local Combat Manager
        from .modules.combat_pkg.local_combat_manager import LocalCombatManager
        self.combat_manager = LocalCombatManager(self.event_bus)
        
        # Initialize Local World Sim & Director
        from .modules.simulation_pkg.local_simulation import LocalWorldSim
        from .modules.story_pkg.local_director import LocalCampaignDirector
        self.world_sim = LocalWorldSim()
        self.campaign_director = LocalCampaignDirector()
        
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
            
            # Generate initial world state
            from .modules.map_pkg import core as map_core
            from .modules.map_pkg import models as map_models
            
            # Select a random algorithm for the starting area
            algo = map_core.select_algorithm(["forest", "starter"])
            if not algo:
                # Fallback if no specific tag match
                algo = map_core.GENERATION_ALGORITHMS[0]
                
            # Generate the map
            map_response = map_core.run_generation(
                algorithm=algo,
                seed="start_seed_12345", # Fixed seed for consistency or random
                width_override=40,
                height_override=30
            )
            
            # Create starting location
            start_location = LocationSave(
                id=1,
                name="Starting Area",
                tags=["forest", "starter"],
                exits={},
                description="A quiet clearing in the woods.",
                generated_map_data=map_response.map_data,
                map_seed=map_response.seed_used,
                region_id=1,
                spawn_points=map_response.spawn_points
            )
            
            # Create minimal game state
            game_state = SaveGameData(
                characters=characters,
                factions=[],
                regions=[],
                locations=[start_location],
                npcs=[],
                items=[],
                traps=[],
                campaigns=[],
                campaign_states=[],
                quests=[],
                flags=[]
            )
            
            # Set initial positions for characters
            spawn_x, spawn_y = 10, 10
            if map_response.spawn_points and "player" in map_response.spawn_points:
                spawns = map_response.spawn_points["player"]
                if spawns:
                    spawn_x, spawn_y = spawns[0]
            
            for char in characters:
                char.current_location_id = start_location.id
                char.position_x = spawn_x
                char.position_y = spawn_y
            
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
                elif action_type == "EQUIP":
                    result = await self._handle_equip(current_state, player_id, action_data)
                elif action_type == "UNEQUIP":
                    result = await self._handle_unequip(current_state, player_id, action_data)
                elif action_type == "BUY":
                    result = await self._handle_buy(current_state, player_id, action_data)
                elif action_type == "SELL":
                    result = await self._handle_sell(current_state, player_id, action_data)
                elif action_type in ["ATTACK", "FLEE"]:
                    # Route directly to combat manager
                    result = self.combat_manager.handle_action(player_id, action_type, action_data)
                elif action_type == "END_TURN":
                    # Check if we are in combat
                    if self.combat_manager.state.is_active:
                        result = self.combat_manager.handle_action(player_id, action_type, action_data)
                    else:
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
        """Handle ability usage."""
        logger.info(f"Dialogue: {player_id} with {data.get('npc_id')}")
        
        # TODO: Implement dialogue system with AI DM
        
        await self.event_bus.publish("action.dialogue", {
            "player_id": player_id,
            "npc_id": data.get('npc_id')
        })
        
        return {
            "success": True,
            "action": "ability",
            "message": "Ability system not yet implemented"
        }

    async def _handle_dialogue(
        self,
        current_state: SaveGameData,
        player_id: str,
        data: dict
    ) -> Dict[str, Any]:
        """Handle dialogue interaction."""
        npc_id = data.get("npc_id")
        dialogue_id = data.get("dialogue_id")
        node_id = data.get("node_id")
        
        logger.info(f"Dialogue: {player_id} talking to {npc_id} (Dialogue: {dialogue_id}, Node: {node_id})")
        
        # Publish event
        await self.event_bus.publish("action.dialogue", {
            "player_id": player_id,
            "npc_id": npc_id,
            "dialogue_id": dialogue_id,
            "node_id": node_id
        })
        
        # If this is a narrative advance (e.g. choosing an option), we might want to trigger story logic
        if node_id:
             await self.event_bus.publish("command.story.advance_narrative", {
                "node_id": node_id,
                "actor_id": player_id
            })
        
        return {
            "success": True,
            "action": "dialogue",
            "message": f"Dialogue processed: {node_id}"
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
    
    def get_active_player(self) -> Optional[CharacterSave]:
        """Get the currently active player."""
        return self.state_manager.get_active_player()

    async def _handle_equip(
        self,
        current_state: SaveGameData,
        player_id: str,
        data: dict
    ) -> Dict[str, Any]:
        """Handle equipping an item."""
        item_id = data.get("item_id")
        slot = data.get("slot")
        
        logger.info(f"Equip: {player_id} equipping {item_id} to {slot}")
        
        # Find character
        character = next((c for c in current_state.characters if c.id == player_id), None)
        if not character:
            return {"success": False, "error": "Character not found"}
            
        # Basic validation
        if item_id not in (character.inventory or {}):
            return {"success": False, "error": "Item not in inventory"}
            
        # Logic:
        # 1. Remove from inventory
        # 2. Add to equipment
        # 3. If slot occupied, move old item to inventory
        
        # Implementation (simplified for now)
        if not character.equipment:
            character.equipment = {}
        if not character.inventory:
            character.inventory = {}
            
        # Check if slot occupied
        old_item = character.equipment.get(slot)
        if old_item:
            # Move old item to inventory
            character.inventory[old_item] = character.inventory.get(old_item, 0) + 1
            
        # Equip new item
        character.equipment[slot] = item_id
        
        # Remove from inventory
        character.inventory[item_id] -= 1
        if character.inventory[item_id] <= 0:
            del character.inventory[item_id]
            
        # Save state
        # Save state
        self.state_manager.save_current_game()
        await self.event_bus.publish("notification.auto_save", {})
        
        await self.event_bus.publish("action.equip", {
            "player_id": player_id,
            "item_id": item_id,
            "slot": slot
        })
        
        return {
            "success": True,
            "message": f"Equipped {item_id}",
            "character": character
        }

    async def _handle_unequip(
        self,
        current_state: SaveGameData,
        player_id: str,
        data: dict
    ) -> Dict[str, Any]:
        """Handle unequipping an item."""
        slot = data.get("slot")
        
        logger.info(f"Unequip: {player_id} unequipping {slot}")
        
        # Find character
        character = next((c for c in current_state.characters if c.id == player_id), None)
        if not character:
            return {"success": False, "error": "Character not found"}
            
        if not character.equipment or slot not in character.equipment:
            return {"success": False, "error": "Slot is empty"}
            
        item_id = character.equipment[slot]
        
        # Logic:
        # 1. Remove from equipment
        # 2. Add to inventory
        
        del character.equipment[slot]
        
        if not character.inventory:
            character.inventory = {}
            
        character.inventory[item_id] = character.inventory.get(item_id, 0) + 1
        
        # Save state
        self.state_manager.save_current_game()
        
        await self.event_bus.publish("action.unequip", {
            "player_id": player_id,
            "item_id": item_id,
            "slot": slot
        })
        
        return {
            "success": True,
            "message": f"Unequipped {item_id}",
            "character": character
        }

    async def _handle_buy(
        self,
        current_state: SaveGameData,
        player_id: str,
        data: dict
    ) -> Dict[str, Any]:
        """Handle buying an item."""
        shop_id = data.get("shop_id")
        item_id = data.get("item_id")
        quantity = data.get("quantity", 1)
        
        logger.info(f"Buy: {player_id} buying {quantity}x {item_id} from {shop_id}")
        
        # Find character
        character = next((c for c in current_state.characters if c.id == player_id), None)
        if not character:
            return {"success": False, "error": "Character not found"}
            
        # Get Shop Data (Importing here to avoid circular imports if possible, or move to top)
        from .modules.story_pkg.shop_handler import get_shop_inventory
        try:
            shop = get_shop_inventory(shop_id)
        except ValueError:
            return {"success": False, "error": "Shop not found"}
            
        shop_item = shop["inventory"].get(item_id)
        if not shop_item:
            return {"success": False, "error": "Item not in shop"}
            
        if shop_item["quantity"] < quantity:
            return {"success": False, "error": "Not enough stock"}
            
        cost = shop_item["price"] * quantity
        
        # Check funds
        # Ensure inventory exists
        if not character.inventory: character.inventory = {}
        current_gold = character.inventory.get("currency", 0)
        
        if current_gold < cost:
            return {"success": False, "error": "Not enough gold"}
            
        # Transaction
        character.inventory["currency"] = current_gold - cost
        shop_item["quantity"] -= quantity
        
        # Add item
        # If it's gear, it goes to 'carried_gear' usually? 
        # The schema says 'inventory' is Dict[str, Any]. 
        # Let's assume flat structure or nested 'carried_gear' depending on usage.
        # ShopScreen expects `char_context.inventory['carried_gear']`.
        # So we should respect that structure.
        
        if "carried_gear" not in character.inventory:
            character.inventory["carried_gear"] = {}
            
        character.inventory["carried_gear"][item_id] = character.inventory["carried_gear"].get(item_id, 0) + quantity
        
        self.state_manager.save_current_game()
        
        await self.event_bus.publish("action.buy", {
            "player_id": player_id,
            "shop_id": shop_id,
            "item_id": item_id,
            "quantity": quantity,
            "cost": cost
        })
        
        return {
            "success": True,
            "message": f"Bought {quantity}x {item_id}",
            "character": character
        }

    async def _handle_sell(
        self,
        current_state: SaveGameData,
        player_id: str,
        data: dict
    ) -> Dict[str, Any]:
        """Handle selling an item."""
        shop_id = data.get("shop_id")
        item_id = data.get("item_id")
        quantity = data.get("quantity", 1)
        
        logger.info(f"Sell: {player_id} selling {quantity}x {item_id} to {shop_id}")
        
        # Find character
        character = next((c for c in current_state.characters if c.id == player_id), None)
        if not character:
            return {"success": False, "error": "Character not found"}
            
        # Get Shop Data
        from .modules.story_pkg.shop_handler import get_shop_inventory
        try:
            shop = get_shop_inventory(shop_id)
        except ValueError:
            return {"success": False, "error": "Shop not found"}
            
        # Check player inventory
        if not character.inventory: character.inventory = {}
        
        # Check carried gear
        carried = character.inventory.get("carried_gear", {})
        if item_id not in carried or carried[item_id] < quantity:
            return {"success": False, "error": "Item not in inventory"}
            
        # Calculate value (simplified: 50% of buy price)
        # We need item data to know price.
        # For now, let's assume we can get it from shop if they sell it, or rule engine.
        # Fallback: 10 gold per item if unknown.
        
        shop_item = shop["inventory"].get(item_id)
        base_price = shop_item["price"] if shop_item else 20
        sell_price = int(base_price * 0.5)
        total_value = sell_price * quantity
        
        # Transaction
        carried[item_id] -= quantity
        if carried[item_id] <= 0:
            del carried[item_id]
            
        current_gold = character.inventory.get("currency", 0)
        character.inventory["currency"] = current_gold + total_value
        
        # Shop gets item? (Optional, maybe shop has infinite space or we add it)
        # For now, items just vanish into the economy.
        
        self.state_manager.save_current_game()
        
        await self.event_bus.publish("action.sell", {
            "player_id": player_id,
            "shop_id": shop_id,
            "item_id": item_id,
            "quantity": quantity,
            "value": total_value
        })
        
        return {
            "success": True,
            "message": f"Sold {quantity}x {item_id} for {total_value} gold",
            "character": character
        }

    # -------------------------------------------------------------------------
    # Time & Simulation
    # -------------------------------------------------------------------------

    async def advance_time(self, hours: int = 8) -> Dict[str, Any]:
        """
        Advances game time, triggering world simulation and story checks.
        """
        logger.info(f"Advancing time by {hours} hours...")
        
        state = self.state_manager.current_state
        if not state:
            return {"success": False, "error": "No active game state"}
            
        events = []
        
        # 1. Run World Simulation
        if self.world_sim:
            sim_events = self.world_sim.process_turn(state)
            events.extend(sim_events)
            
        # 2. Run Story Director
        if self.campaign_director:
            # Check pacing
            if self.campaign_director.check_pacing(state):
                beat = self.campaign_director.generate_next_beat(state)
                if beat:
                    # Add new quest to state
                    from .modules.save_schemas import QuestSave
                    new_quest = QuestSave(
                        id=f"quest_{len(state.quests) + 1}",
                        title=beat.get("title", "Unknown Quest"),
                        description=beat.get("description", ""),
                        status="active",
                        objectives=[{"text": obj, "completed": False} for obj in beat.get("objectives", [])],
                        rewards={"xp": 100, "gold": 50} # Simplified
                    )
                    state.quests.append(new_quest)
                    events.append(f"New Quest: {new_quest.title}")
                    
        # Save changes
        self.state_manager.save_current_game()
        
        return {
            "success": True,
            "hours_passed": hours,
            "events": events
        }
        quantity = data.get("quantity", 1)
        
        logger.info(f"Sell: {player_id} selling {quantity}x {item_id} to {shop_id}")
        
        character = next((c for c in current_state.characters if c.id == player_id), None)
        if not character:
            return {"success": False, "error": "Character not found"}
            
        if not character.inventory or "carried_gear" not in character.inventory:
             return {"success": False, "error": "Inventory empty"}
             
        current_qty = character.inventory["carried_gear"].get(item_id, 0)
        if current_qty < quantity:
            return {"success": False, "error": "Not enough items"}
            
        # Calculate price (50% value)
        # We need item template.
        from .modules.rules_pkg.data_loader import get_item_template
        try:
            template = get_item_template(item_id)
            value = template.value if template else 10 # Default fallback
        except:
            value = 10
            
        sell_price = (value // 2) * quantity
        
        # Transaction
        character.inventory["carried_gear"][item_id] -= quantity
        if character.inventory["carried_gear"][item_id] <= 0:
            del character.inventory["carried_gear"][item_id]
            
        character.inventory["currency"] = character.inventory.get("currency", 0) + sell_price
        
        # Add to shop
        from .modules.story_pkg.shop_handler import get_shop_inventory
        try:
            shop = get_shop_inventory(shop_id)
            if item_id in shop["inventory"]:
                shop["inventory"][item_id]["quantity"] += quantity
            else:
                shop["inventory"][item_id] = {"price": value, "quantity": quantity}
        except:
            pass # Ignore shop update error if shop not found (shouldn't happen)
            
        self.state_manager.save_current_game()
        
        await self.event_bus.publish("action.sell", {
            "player_id": player_id,
            "shop_id": shop_id,
            "item_id": item_id,
            "quantity": quantity,
            "value": sell_price
        })
        
        return {
            "success": True,
            "message": f"Sold {quantity}x {item_id}",
            "character": character
        }


# Module-level singleton
_orchestrator_instance: Optional[Orchestrator] = None

def get_orchestrator() -> Orchestrator:
    """Return the singleton Orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = Orchestrator()
    return _orchestrator_instance

