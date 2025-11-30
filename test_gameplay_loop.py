import sys
import os
import asyncio
import logging
import shutil
from pathlib import Path

# Setup paths
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
MONOLITH_PATH = APP_ROOT / "AI-TTRPG"
if str(MONOLITH_PATH) not in sys.path:
    sys.path.insert(0, str(MONOLITH_PATH))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("test_loop")

async def run_test():
    print("=== Starting Gameplay Loop Test ===")
    
    # 1. Initialize Orchestrator
    print("\n[1] Initializing Engine...")
    from monolith.orchestrator import Orchestrator
    
    # Mock AI to speed up test
    from monolith.modules.ai_dm_pkg.llm_service import ai_client
    ai_client.generate_map_flavor = lambda tags, lore_context="": {}
    
    orchestrator = Orchestrator()
    await orchestrator.initialize_engine()
    print("    Engine Initialized.")

    # 2. Start New Game
    print("\n[2] Starting New Game...")
    char_path = APP_ROOT / "characters" / "Test Hero 2.json"
    if not char_path.exists():
        print(f"ERROR: Character file not found at {char_path}")
        return

    # We use a list of paths, maybe duplicate the hero to have 2 players for hotseat test
    result = await orchestrator.start_new_game([str(char_path), str(char_path)])
    if not result["success"]:
        print(f"ERROR: Failed to start game: {result}")
        return
    
    print(f"    Game Started. Players: {result['num_players']}")
    
    # 3. Verify Initial State
    state = orchestrator.get_current_state()
    active_player = orchestrator.get_active_player()
    print(f"    Active Player: {active_player.name} (ID: {active_player.id})")
    print(f"    Position: ({active_player.position_x}, {active_player.position_y})")
    
    # 4. Test Movement (using the new API)
    print("\n[3] Testing Movement...")
    
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    move_successful = False
    
    for dx, dy in directions:
        target_x = active_player.position_x + dx
        target_y = active_player.position_y + dy
        
        print(f"    Requesting move to ({target_x}, {target_y})...")
        move_result = await orchestrator.handle_player_move(active_player.id, target_x, target_y)
        
        if move_result["success"]:
            print(f"    Move Successful: {move_result['message']}")
            move_successful = True
            
            # Verify state update
            updated_player = orchestrator.get_active_player()
            print(f"    New Position in State: ({updated_player.position_x}, {updated_player.position_y})")
            
            if updated_player.position_x == target_x and updated_player.position_y == target_y:
                print("    SUCCESS: State updated correctly.")
            else:
                print("    FAILURE: State did not update.")
            break
        else:
            print(f"    Move Failed: {move_result.get('message')}")
            
    if not move_successful:
        print("    WARNING: Could not find a valid move from current position.")

    # 5. Test Turn Rotation
    print("\n[4] Testing Turn Rotation...")
    print(f"    Current Active: {active_player.name} ({active_player.id})")
    
    end_turn_result = await orchestrator.handle_player_action(active_player.id, "END_TURN")
    if end_turn_result["success"]:
        new_active = orchestrator.get_active_player()
        print(f"    Turn Ended. New Active: {new_active.name} ({new_active.id})")
        
        if new_active.id == active_player.id:
            # Since we loaded the same file twice, IDs might be identical if not handled.
            # SaveManager.load_character_from_json usually keeps the ID from file.
            # If IDs are same, hotseat logic might be confused or just look same.
            print("    WARNING: IDs are identical. Verify hotseat index changed.")
            print(f"    Active Index: {orchestrator.state_manager.active_player_index}")
    else:
        print(f"    End Turn Failed: {end_turn_result.get('error')}")

    # 6. Save Game
    print("\n[5] Testing Save...")
    save_result = orchestrator.state_manager.save_current_game()
    if save_result["success"]:
        print(f"    Game Saved to: {save_result['path']}")
    else:
        print(f"    Save Failed: {save_result.get('error')}")

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
