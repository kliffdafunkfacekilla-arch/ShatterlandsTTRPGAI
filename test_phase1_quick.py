"""
Phase 1 Quick Test - Simplified version to work with project structure
"""
import sys
import os
from pathlib import Path

# Navigate to monolith directory and run tests from there
monolith_dir = Path(__file__).parent / "AI-TTRPG" / "monolith"
os.chdir(monolith_dir)
sys.path.insert(0, str(monolith_dir))

import asyncio
import json

# Now import from current directory
from modules import save_manager_new as sm
from modules.save_schemas import CharacterSave, SaveGameData

print("="*60)
print("PHASE 1 QUICK TEST - Core Architecture")
print("="*60)

# Test 1: Character Save/Load
print("\n[Test 1] Character Save/Load...")
try:
    char = CharacterSave(
        id="test1",
        name="Test Hero",
        level=2,
        max_hp=35,
        current_hp=35,
        current_location_id=1,
        position_x=0,
        position_y=0
    )
    
    result = sm.save_character_to_json(char, "test_char.json")
    assert result["success"], f"Save failed: {result.get('error')}"
    print(f"✅ Character saved to: {result['path']}")
    
    result2 = sm.load_character_from_json(result["path"])
    assert result2["success"], f"Load failed: {result2.get('error')}"
    assert result2["character"].name == "Test Hero"
    print(f"✅ Character loaded: {result2['character'].name}")
    
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 2: Game Save/Load
print("\n[Test 2] Game Save/Load...")
try:
    char1 = CharacterSave(id="p1", name="Player1", level=1, max_hp=30, current_hp=30, current_location_id=1, position_x=0, position_y=0)
    char2 = CharacterSave(id="p2", name="Player2", level=1, max_hp=30, current_hp=30, current_location_id=1, position_x=0, position_y=0)
    
    game_data = SaveGameData(
        characters=[char1, char2],
        factions=[], regions=[], locations=[], npcs=[],
        items=[], traps=[], campaigns=[], campaign_states=[], quests=[], flags=[]
    )
    
    result = sm.save_game(game_data, "quick_test", "p1", "Player1")
    assert result["success"]
    print(f"✅ Game saved: {result['path']}")
    
    result2 = sm.load_game("quick_test")
    assert result2["success"]
    assert len(result2["save_file"].data.characters) == 2
    print(f"✅ Game loaded: {len(result2['save_file'].data.characters)} characters")
    
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 3: Scan Operations
print("\n[Test 3] Scan Operations...")
try:
    saves = sm.scan_saves()
    print(f"✅ Found {len(saves)} save files")
    for save in saves:
        print(f"   - {save['name']} ({save['timestamp']})")
    
    chars = sm.scan_characters()
    print(f"✅ Found {len(chars)} character files")
    for char in chars:
        print(f"   - {char['name']} (Level {char.get('level', '?')})")
        
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 4: Pydantic Validation
print("\n[Test 4] Pydantic Validation...")
try:
    # Test that invalid data is rejected
    try:
        bad_char = CharacterSave(
            id="bad",
            name="Bad",
            max_hp="not a number",  # Should fail validation
            current_hp=30,
            current_location_id=1,
            position_x=0,
            position_y=0
        )
        print("❌ Should have rejected invalid data!")
    except:
        print("✅ Invalid data properly rejected by Pydantic")
        
except Exception as e:
    print(f"❌ FAILED: {e}")

# Cleanup
print("\n[Cleanup] Removing test files...")
try:
    Path("../../characters/test_char.json").unlink(missing_ok=True)
    Path("../../saves/quick_test.json").unlink(missing_ok=True)
    print("✅ Cleanup complete")
except Exception as e:
    print(f"⚠️  Cleanup warning: {e}")

print("\n" + "="*60)
print("QUICK TEST COMPLETE")
print("="*60)
print("\nNote: Full async tests (Event Bus, Orchestrator) require")
print("additional setup. These basic tests verify core JSON I/O.")
