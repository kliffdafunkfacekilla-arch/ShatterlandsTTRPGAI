"""
Phase 7 Integration Test Suite

Comprehensive tests for the complete TTRPG system
"""
import sys
import asyncio
from pathlib import Path
import json
import tempfile
import shutil

# Add monolith to path
monolith_dir = Path(__file__).parent / "AI-TTRPG" / "monolith"
sys.path.insert(0, str(monolith_dir))


def run_integration_tests():
    """Run all integration tests"""
    
    print("="*70)
    print("PHASE 7 INTEGRATION TESTS - Full System Validation")
    print("="*70)
    
    test_results = {"passed": 0, "failed": 0, "warnings": 0}
    
    # Shared state
    test_state = {
        "orchestrator": None,
        "event_bus": None,
        "test_chars_dir": None,
        "char1_path": None,
        "char2_path": None
    }
    
    # ========================================================================
    # TEST 1: Orchestrator Initialization
    # ========================================================================
    print("\n[Test 1] Orchestrator Initialization")
    try:
        from orchestrator import Orchestrator
        from event_bus import get_event_bus
        from modules.rules_pkg.data_loader_enhanced import load_and_validate_all
        
        # Initialize components
        test_state["orchestrator"] = Orchestrator()
        test_state["event_bus"] = get_event_bus()
        
        # Load rules
        print("   Loading game rules...")
        rules_summary = load_and_validate_all()
        print(f"   ✅ Rules loaded: {rules_summary}")
        
        # Initialize engine
        print("   Initializing engine...")
        asyncio.run(test_state["orchestrator"].initialize_engine())
        print("   ✅ Engine initialized")
        test_results["passed"] += 1
        
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        test_results["failed"] += 1
        import traceback
        traceback.print_exc()
        return test_results  # Can't continue without orchestrator
    
    # ========================================================================
    # TEST 2: Create Test Character JSON Files
    # ========================================================================
    print("\n[Test 2] Create Test Character Files")
    try:
        test_state["test_chars_dir"] = Path(tempfile.mkdtemp())
        
        # Create 2 test characters
        char1 = {
            "id": "test_char_1",
            "name": "Test Warrior",
            "level": 1,
            "stats": {"Might": 14, "Endurance": 12, "Finesse": 10, "Logic": 8, "Charm": 8, "Instinct": 10},
            "max_hp": 30,
            "current_hp": 30,
            "current_location_id": 1,
            "position_x": 5,
            "position_y": 5,
            "talents": [],
            "abilities": []
        }
        
        char2 = {
            "id": "test_char_2",
            "name": "Test Mage",
            "level": 1,
            "stats": {"Might": 8, "Endurance": 10, "Finesse": 10, "Logic": 14, "Charm": 12, "Instinct": 8},
            "max_hp": 25,
            "current_hp": 25,
            "current_location_id": 1,
            "position_x": 6,
            "position_y": 5,
            "talents": [],
            "abilities": []
        }
        
        test_state["char1_path"] = test_state["test_chars_dir"] / "warrior.json"
        test_state["char2_path"] = test_state["test_chars_dir"] / "mage.json"
        
        with open(test_state["char1_path"], 'w') as f:
            json.dump(char1, f, indent=2)
        
        with open(test_state["char2_path"], 'w') as f:
            json.dump(char2, f, indent=2)
        
        print(f"   ✅ Created test characters in {test_state['test_chars_dir']}")
        test_results["passed"] += 1
        
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        test_results["failed"] += 1
    
    # ========================================================================
    # TEST 3: Start New Game
    # ========================================================================
    print("\n[Test 3] Start New Game")
    try:
        char_files = [str(test_state["char1_path"]), str(test_state["char2_path"])]
        
        result = asyncio.run(test_state["orchestrator"].start_new_game(char_files))
        
        if result["success"]:
            print(f"   ✅ Game started successfully")
            print(f"      Players: {result.get('num_players', 0)}")
            test_results["passed"] += 1
        else:
            print(f"   ❌ FAILED: {result.get('error')}")
            test_results["failed"] += 1
            
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        test_results["failed"] += 1
    
    # ========================================================================
    # TEST 4: Game State Access
    # ========================================================================
    print("\n[Test 4] Game State Access")
    try:
        state = test_state["orchestrator"].get_current_state()
        
        if state and state.characters:
            print(f"   ✅ Game state retrieved")
            print(f"      Characters: {len(state.characters)}")
            for char in state.characters:
                print(f"         - {char.name} (HP: {char.current_hp}/{char.max_hp})")
            test_results["passed"] += 1
        else:
            print(f"   ❌ FAILED: No game state")
            test_results["failed"] += 1
            
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        test_results["failed"] += 1
    
    # ========================================================================
    # TEST 5: Hotseat Rotation
    # ========================================================================
    print("\n[Test 5] Hotseat Player Rotation")
    try:
        player1 = test_state["orchestrator"].get_active_player()
        player1_id = player1.id if player1 else None
        
        player2 = test_state["orchestrator"].state_manager.switch_active_player()
        player2_id = player2.id if player2 else None
        
        player3 = test_state["orchestrator"].state_manager.switch_active_player()
        player3_id = player3.id if player3 else None
        
        if player1_id and player2_id and player3_id:
            if player1_id != player2_id and player3_id == player1_id:
                print(f"   ✅ Hotseat rotation working")
                print(f"      {player1.name} → {player2.name} → {player1.name}")
                test_results["passed"] += 1
            else:
                print(f"   ❌ FAILED: Rotation not working correctly")
                test_results["failed"] += 1
        else:
            print(f"   ❌ FAILED: Could not test rotation")
            test_results["failed"] += 1
            
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        test_results["failed"] += 1
    
    # ========================================================================
    # TEST 6: Save Game
    # ========================================================================
    print("\n[Test 6] Save Game")
    try:
        save_result = test_state["orchestrator"].state_manager.save_current_game("test_integration_save")
        
        if save_result["success"]:
            print(f"   ✅ Game saved successfully")
            test_results["passed"] += 1
        else:
            print(f"   ❌ FAILED: {save_result.get('error')}")
            test_results["failed"] += 1
            
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        test_results["failed"] += 1
    
    # ========================================================================
    # TEST 7: Load Game
    # ========================================================================
    print("\n[Test 7] Load Game")
    try:
        load_result = asyncio.run(test_state["orchestrator"].load_game("test_integration_save"))
        
        if load_result["success"]:
            print(f"   ✅ Game loaded successfully")
            test_results["passed"] += 1
        else:
            print(f"   ❌ FAILED: {load_result.get('error')}")
            test_results["failed"] += 1
            
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        test_results["failed"] += 1
    
    # ========================================================================
    # TEST 8: Event Bus
    # ========================================================================
    print("\n[Test 8] Event Bus Pub/Sub")
    try:
        # Just test that Event Bus exists and can subscribe
        test_state["event_bus"].subscribe("test.event", lambda **kw: None)
        print(f"   ✅ Event Bus working")
        print(f"      Subscription registered successfully")
        test_results["passed"] += 1
            
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        test_results["failed"] += 1
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    print("\n[Cleanup]")
    try:
        if test_state["test_chars_dir"] and test_state["test_chars_dir"].exists():
            shutil.rmtree(test_state["test_chars_dir"])
            print(f"   ✅ Test files cleaned up")
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")
        test_results["warnings"] += 1
    
    return test_results


if __name__ == "__main__":
    results = run_integration_tests()
    
    # Summary
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    print(f"""
Tests Passed:  {results['passed']}
Tests Failed:  {results['failed']}
Warnings:      {results['warnings']}

System Status: {'✅ READY FOR USE!' if results['failed'] == 0 else '❌ NEEDS FIXES'}

Next Steps:
- Run this before major changes
- All tests passing = system is functional
- Test UI interactions manually
""")
    print("="*70)
    
    # Exit code
    sys.exit(0 if results['failed'] == 0 else 1)
