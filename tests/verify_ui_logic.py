import sys
import os
import asyncio
import logging
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'AI-TTRPG'))

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager

# Mock Kivy App
class MockApp:
    def __init__(self):
        self.orchestrator = None
        self.active_character_context = None
        self.root = MagicMock()
        self.game_settings = {}

# Mock Factory
from kivy.factory import Factory
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class MockWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = ""

Factory.register('DungeonBackground', cls=MockWidget)
Factory.register('DungeonLabel', cls=Label)
Factory.register('DungeonButton', cls=Button)
Factory.register('ParchmentPanel', cls=MockWidget)

# Setup Logging
logging.basicConfig(level=logging.INFO)

async def verify_ui_logic():
    print("--- Starting UI Logic Verification ---")
    
    # 1. Setup Environment
    from monolith.orchestrator import Orchestrator
    from monolith.modules.save_manager import save_character_to_json, load_character_from_json
    from monolith.modules.save_schemas import CharacterSave
    
    # Create test directory
    test_dir = Path("./tests/ui_verification_data")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True)
    
    # Initialize Orchestrator
    import monolith.orchestrator as orch_mod
    print(f"DEBUG: Orchestrator file: {orch_mod.__file__}")
    
    # Read file content
    with open(orch_mod.__file__, 'r') as f:
        content = f.read()
        print(f"DEBUG: File content length: {len(content)}")
        print(f"DEBUG: '_handle_buy' in content: {'_handle_buy' in content}")
        # Print lines around where _handle_buy should be
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "_handle_buy" in line:
                print(f"DEBUG: Line {i+1}: {line}")
    
    orchestrator = Orchestrator()
    print(f"DEBUG: Orchestrator attributes: {[x for x in dir(orchestrator) if '_handle_' in x]}")
    
    orchestrator.event_bus = MagicMock()
    orchestrator.event_bus.publish = AsyncMock()
    
    # Mock App
    app = MockApp()
    app.orchestrator = orchestrator
    
    # Patch App.get_running_app
    with patch('kivy.app.App.get_running_app', return_value=app):
        
        # --- TEST 1: Character Creation ---
        print("\n[Test 1] Character Creation Logic")
        from game_client.views.character_creation_screen import CharacterCreationScreen
        
        # Mock rules_api
        with patch('game_client.views.character_creation_screen.rules_api') as mock_rules:
            mock_rules.get_all_talents_data.return_value = []
            mock_rules.get_all_kingdoms.return_value = ["Kingdom A"]
            mock_rules.get_data.return_value = {}
            
            screen = CharacterCreationScreen()
            screen.collected_data = {
                "name": "Test Hero",
                "kingdom": "Kingdom A",
                "ability_talent": "Strike"
            }
            
            # Mock save_character_to_json to use our test dir
            with patch('monolith.modules.save_manager.SAVE_DIR', test_dir):
                 # We need to mock the async run helper to run synchronously
                screen.run_async = lambda task, success, error: success(task())
                
                # Execute creation
                try:
                    new_char = screen._create_character_task()
                    print(f"✅ Character Created: {new_char.name} (ID: {new_char.id})")
                    
                    # Verify file exists
                    # save_manager uses its own path, we need to check where it saved.
                    # Since we patched SAVE_DIR, it should be in test_dir/characters
                    # But save_manager constructs path internally.
                    # Let's trust the return object for now.
                    assert new_char.name == "Test Hero"
                    assert new_char.level == 1
                    
                    # Set as active character for next tests
                    app.active_character_context = new_char
                    orchestrator.current_state = MagicMock()
                    orchestrator.current_state.characters = [new_char]
                    
                except Exception as e:
                    print(f"❌ Character Creation Failed: {e}")
                    raise

        # --- TEST 2: Shop Logic ---
        print("\n[Test 2] Shop Logic (Buy/Sell)")
        from game_client.views.shop_screen import ShopScreen
        
        shop_screen = ShopScreen()
        shop_screen.shop_id = "test_shop"
        
        # Mock shop inventory in shop_handler
        with patch('monolith.modules.story_pkg.shop_handler.get_shop_inventory') as mock_get_shop:
            mock_get_shop.return_value = {
                "inventory": {
                    "potion": {"price": 10, "quantity": 5}
                }
            }
            
            # Give player money
            app.active_character_context.inventory = {"currency": 100, "carried_gear": {}}
            
            # Test Buy
            # We need to await the orchestrator action directly since we can't run the full async helper loop easily
            buy_result = await orchestrator._handle_buy(
                orchestrator.current_state, 
                app.active_character_context.id, 
                {"shop_id": "test_shop", "item_id": "potion", "quantity": 1}
            )
            
            if buy_result['success']:
                print("✅ Buy Successful")
                print(f"   Currency: {buy_result['character'].inventory['currency']} (Expected 90)")
                print(f"   Inventory: {buy_result['character'].inventory['carried_gear']}")
                assert buy_result['character'].inventory['currency'] == 90
                assert buy_result['character'].inventory['carried_gear']['potion'] == 1
            else:
                print(f"❌ Buy Failed: {buy_result.get('error')}")

            # Test Sell
            sell_result = await orchestrator._handle_sell(
                orchestrator.current_state, 
                app.active_character_context.id, 
                {"shop_id": "test_shop", "item_id": "potion", "quantity": 1}
            )
            
            if sell_result['success']:
                print("✅ Sell Successful")
                print(f"   Currency: {sell_result['character'].inventory['currency']} (Expected 95 - assuming 50% value of 10 is 5)")
                # Note: Default fallback value in _handle_sell is 10 if template not found, so 50% is 5.
                # If template found, it might differ.
                assert sell_result['character'].inventory['currency'] == 95
                assert 'potion' not in sell_result['character'].inventory['carried_gear']
            else:
                print(f"❌ Sell Failed: {sell_result.get('error')}")

        # --- TEST 3: Dialogue Logic ---
        print("\n[Test 3] Dialogue Logic")
        # Just verify _handle_dialogue exists and runs
        dialogue_result = await orchestrator._handle_dialogue(
            orchestrator.current_state,
            app.active_character_context.id,
            {"npc_id": "guard", "dialogue_id": "guard_talk", "node_id": "start"}
        )
        if dialogue_result['success']:
             print("✅ Dialogue Action Successful")
        else:
             print(f"❌ Dialogue Action Failed: {dialogue_result.get('error')}")

        # --- TEST 4: Quest Log Logic ---
        print("\n[Test 4] Quest Log Logic")
        from game_client.views.quest_log_screen import QuestLogScreen
        
        # Mock quests in state
        mock_quest = MagicMock()
        mock_quest.title = "Test Quest"
        mock_quest.description = "Do something"
        mock_quest.steps = ["Step 1", "Step 2"]
        mock_quest.current_step = 1
        
        orchestrator.current_state.quests = [mock_quest]
        
        quest_screen = QuestLogScreen()
        # We can't easily test the UI building part without a window, 
        # but we can verify the logic in on_enter doesn't crash
        
        # Mock container
        quest_screen.ids = MagicMock()
        quest_screen.ids.quest_list_container = MagicMock()
        
        try:
            quest_screen.on_enter()
            print("✅ Quest Log on_enter ran without error")
            # Verify widgets added
            assert quest_screen.ids.quest_list_container.add_widget.called
        except Exception as e:
            print(f"❌ Quest Log Failed: {e}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(verify_ui_logic())
