"""
Phase 1 Test Suite: Core Architecture Components

Tests:
1. JSON Save Manager - save/load/scan operations
2. GameStateManager - state management and hotseat rotation
3. Event Bus - publish/subscribe pattern
4. Orchestrator - game initialization and action handling
"""
import sys
import os
import asyncio
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "AI-TTRPG" / "monolith"))

# Import components to test
from modules import save_manager_new as save_manager
from modules.save_schemas import (
    SaveGameData, CharacterSave, SaveFile
)
from orchestrator import Orchestrator, GameStateManager, get_orchestrator
from event_bus import get_event_bus



class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.passed += 1
        print(f"✅ PASS: {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"❌ FAIL: {test_name}")
        print(f"   Error: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print("\n" + "="*60)
        print(f"TEST SUMMARY: {self.passed}/{total} passed")
        print("="*60)
        if self.errors:
            print("\nFailed Tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        return self.failed == 0


results = TestResults()


def test_1_character_save_load():
    """Test saving and loading a character JSON"""
    print("\n[Test 1] Character Save/Load")
    try:
        # Create test character
        test_char = CharacterSave(
            id="test_char_001",
            name="Test Warrior",
            kingdom="TestKingdom",
            level=5,
            stats={"strength": 16, "dexterity": 14},
            skills={"combat": 3},
            max_hp=50,
            current_hp=50,
            current_location_id=1,
            position_x=0,
            position_y=0
        )
        
        # Save character
        save_result = save_manager.save_character_to_json(test_char, "test_warrior.json")
        assert save_result["success"], f"Save failed: {save_result.get('error')}"
        assert Path(save_result["path"]).exists(), "Character file not created"
        
        # Load character back
        load_result = save_manager.load_character_from_json(save_result["path"])
        assert load_result["success"], f"Load failed: {load_result.get('error')}"
        
        loaded_char = load_result["character"]
        assert loaded_char.id == test_char.id, "Character ID mismatch"
        assert loaded_char.name == test_char.name, "Character name mismatch"
        assert loaded_char.level == test_char.level, "Character level mismatch"
        
        results.add_pass("Character Save/Load")
        return save_result["path"]
        
    except Exception as e:
        results.add_fail("Character Save/Load", str(e))
        return None


def test_2_game_save_load():
    """Test saving and loading a complete game state"""
    print("\n[Test 2] Game State Save/Load")
    try:
        # Create test game data
        char1 = CharacterSave(
            id="player1", name="Hero", level=1,
            max_hp=30, current_hp=30,
            current_location_id=1, position_x=0, position_y=0
        )
        char2 = CharacterSave(
            id="player2", name="Sidekick", level=1,
            max_hp=25, current_hp=25,
            current_location_id=1, position_x=1, position_y=0
        )
        
        game_data = SaveGameData(
            characters=[char1, char2],
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
        
        # Save game
        save_result = save_manager.save_game(
            data=game_data,
            slot_name="test_save",
            active_character_id="player1",
            active_character_name="Hero"
        )
        assert save_result["success"], f"Save failed: {save_result.get('error')}"
        
        # Load game back
        load_result = save_manager.load_game("test_save")
        assert load_result["success"], f"Load failed: {load_result.get('error')}"
        
        loaded_data = load_result["save_file"].data
        assert len(loaded_data.characters) == 2, "Character count mismatch"
        assert loaded_data.characters[0].id == "player1", "Character order changed"
        
        results.add_pass("Game State Save/Load")
        return game_data
        
    except Exception as e:
        results.add_fail("Game State Save/Load", str(e))
        return None


def test_3_scan_operations():
    """Test directory scanning for saves and characters"""
    print("\n[Test 3] Scan Operations")
    try:
        # Scan saves
        saves = save_manager.scan_saves()
        assert isinstance(saves, list), "Scan saves should return a list"
        print(f"   Found {len(saves)} save files")
        
        # Scan characters
        characters = save_manager.scan_characters()
        assert isinstance(characters, list), "Scan characters should return a list"
        print(f"   Found {len(characters)} character files")
        
        results.add_pass("Scan Operations")
        
    except Exception as e:
        results.add_fail("Scan Operations", str(e))


def test_4_game_state_manager():
    """Test GameStateManager hotseat rotation"""
    print("\n[Test 4] GameStateManager - Hotseat Rotation")
    try:
        # Create test data
        char1 = CharacterSave(id="p1", name="Player 1", level=1, max_hp=30, current_hp=30, current_location_id=1, position_x=0, position_y=0)
        char2 = CharacterSave(id="p2", name="Player 2", level=1, max_hp=30, current_hp=30, current_location_id=1, position_x=0, position_y=0)
        char3 = CharacterSave(id="p3", name="Player 3", level=1, max_hp=30, current_hp=30, current_location_id=1, position_x=0, position_y=0)
        
        game_data = SaveGameData(
            characters=[char1, char2, char3],
            factions=[], regions=[], locations=[], npcs=[],
            items=[], traps=[], campaigns=[], campaign_states=[], quests=[], flags=[]
        )
        
        # Initialize state manager
        state_mgr = GameStateManager()
        state_mgr.load_state(game_data, "test_hotseat")
        
        # Test initial state
        assert state_mgr.active_player_index == 0, "Should start at player 0"
        player = state_mgr.get_active_player()
        assert player.id == "p1", "First active player should be p1"
        
        # Test rotation
        state_mgr.switch_active_player()
        assert state_mgr.active_player_index == 1, "Should move to player 1"
        player = state_mgr.get_active_player()
        assert player.id == "p2", "Second active player should be p2"
        
        state_mgr.switch_active_player()
        assert state_mgr.active_player_index == 2, "Should move to player 2"
        player = state_mgr.get_active_player()
        assert player.id == "p3", "Third active player should be p3"
        
        # Test circular rotation
        state_mgr.switch_active_player()
        assert state_mgr.active_player_index == 0, "Should wrap back to player 0"
        player = state_mgr.get_active_player()
        assert player.id == "p1", "Should be back to p1"
        
        results.add_pass("GameStateManager - Hotseat Rotation")
        
    except Exception as e:
        results.add_fail("GameStateManager - Hotseat Rotation", str(e))


async def test_5_event_bus():
    """Test Event Bus publish/subscribe"""
    print("\n[Test 5] Event Bus - Pub/Sub")
    try:
        bus = get_event_bus()
        
        # Test data
        received_events = []
        
        async def handler1(topic, payload):
            received_events.append(("handler1", topic, payload))
        
        async def handler2(topic, payload):
            received_events.append(("handler2", topic, payload))
        
        # Subscribe handlers
        await bus.subscribe("test.event", handler1)
        await bus.subscribe("test.event", handler2)
        
        # Publish event
        await bus.publish("test.event", {"data": "test_value"})
        
        # Give handlers time to execute
        await asyncio.sleep(0.1)
        
        # Verify both handlers received the event
        assert len(received_events) == 2, f"Expected 2 events, got {len(received_events)}"
        assert all(e[1] == "test.event" for e in received_events), "Topic mismatch"
        assert all(e[2]["data"] == "test_value" for e in received_events), "Payload mismatch"
        
        results.add_pass("Event Bus - Pub/Sub")
        
    except Exception as e:
        results.add_fail("Event Bus - Pub/Sub", str(e))


async def test_6_orchestrator_initialization():
    """Test Orchestrator initialization"""
    print("\n[Test 6] Orchestrator Initialization")
    try:
        orch = Orchestrator()
        
        # Test initialization
        await orch.initialize_engine()
        assert orch._initialized, "Orchestrator should be initialized"
        
        # Test state manager exists
        assert orch.state_manager is not None, "State manager should exist"
        
        # Test event bus exists
        assert orch.event_bus is not None, "Event bus should exist"
        
        results.add_pass("Orchestrator Initialization")
        return orch
        
    except Exception as e:
        results.add_fail("Orchestrator Initialization", str(e))
        return None


async def test_7_orchestrator_new_game(char_path):
    """Test starting a new game via Orchestrator"""
    print("\n[Test 7] Orchestrator - Start New Game")
    try:
        if not char_path:
            print("   Skipping (no character file from Test 1)")
            return
        
        orch = Orchestrator()
        await orch.initialize_engine()
        
        # Start new game with test character
        result = await orch.start_new_game([char_path])
        
        assert result["success"], f"New game failed: {result.get('error')}"
        assert result["num_players"] == 1, "Should have 1 player"
        
        # Verify state manager has the game loaded
        state = orch.state_manager.get_current_state()
        assert state is not None, "Game state should be loaded"
        assert len(state.characters) == 1, "Should have 1 character"
        
        results.add_pass("Orchestrator - Start New Game")
        
    except Exception as e:
        results.add_fail("Orchestrator - Start New Game", str(e))


async def test_8_orchestrator_action_handling():
    """Test action dispatching"""
    print("\n[Test 8] Orchestrator - Action Handling")
    try:
        orch = Orchestrator()
        await orch.initialize_engine()
        
        # Create minimal game state
        char = CharacterSave(id="test_p1", name="Test", level=1, max_hp=30, current_hp=30, current_location_id=1, position_x=0, position_y=0)
        game_data = SaveGameData(
            characters=[char], factions=[], regions=[], locations=[],
            npcs=[], items=[], traps=[], campaigns=[], campaign_states=[], quests=[], flags=[]
        )
        orch.state_manager.load_state(game_data)
        
        # Test END_TURN action
        result = await orch.handle_player_action(
            player_id="test_p1",
            action_type="END_TURN"
        )
        assert result["success"], f"Action failed: {result.get('error')}"
        
        # Test invalid player (not their turn)
        result = await orch.handle_player_action(
            player_id="wrong_player",
            action_type="MOVE"
        )
        assert not result["success"], "Should reject invalid player"
        assert "turn" in result["error"].lower(), "Should mention turn validation"
        
        results.add_pass("Orchestrator - Action Handling")
        
    except Exception as e:
        results.add_fail("Orchestrator - Action Handling", str(e))


async def run_all_tests():
    """Run complete test suite"""
    print("="*60)
    print("PHASE 1 TEST SUITE - Core Architecture")
    print("="*60)
    
    # Synchronous tests
    char_path = test_1_character_save_load()
    test_2_game_save_load()
    test_3_scan_operations()
    test_4_game_state_manager()
    
    # Async tests
    await test_5_event_bus()
    await test_6_orchestrator_initialization()
    await test_7_orchestrator_new_game(char_path)
    await test_8_orchestrator_action_handling()
    
    # Summary
    success = results.summary()
    
    # Cleanup test files
    print("\nCleaning up test files...")
    try:
        test_files = [
            "./characters/test_warrior.json",
            "./saves/test_save.json",
            "./saves/test_hotseat.json",
            "./saves/CurrentSave.json"
        ]
        for f in test_files:
            if Path(f).exists():
                Path(f).unlink()
                print(f"  Deleted: {f}")
    except Exception as e:
        print(f"  Cleanup warning: {e}")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
