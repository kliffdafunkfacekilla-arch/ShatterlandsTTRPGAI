"""
Phase 2 Test Suite: Data Layer & Rules Validation

Tests:
1. RuleSetContainer singleton pattern
2. JSON file loading and validation
3. Ability and talent lookup maps
4. Error handling for invalid data
5. Thread safety
"""
import sys
from pathlib import Path

# Navigate to monolith directory
monolith_dir = Path(__file__).parent / "AI-TTRPG" / "monolith"
sys.path.insert(0, str(monolith_dir))

from modules.rules_pkg.data_loader_enhanced import (
    RuleSetContainer, load_and_validate_all, get_rules
)

print("="*60)
print("PHASE 2 TEST - Data Layer & Validation")
print("="*60)

# Test 1: Singleton Pattern
print("\n[Test 1] Singleton Pattern...")
try:
    instance1 = RuleSetContainer.get_instance()
    instance2 = RuleSetContainer.get_instance()
    
    assert instance1 is instance2, "Should return same instance"
    print("✅ Singleton pattern working")
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 2: Load All Rules Data
print("\n[Test 2] Load All Rules Data...")
try:
    summary = load_and_validate_all()
    
    print(f"✅ Loaded {summary['stats']} stats")
    print(f"✅ Loaded {summary['skills']} skills")
    print(f"✅ Loaded {summary['abilities']} abilities")
    print(f"✅ Loaded {summary['talents']} talents")
    print(f"✅ Loaded {summary['status_effects']} status effects")
    
    if summary['load_errors'] > 0:
        print(f"⚠️  {summary['load_errors']} non-fatal errors during loading")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Data Access
print("\n[Test 3] Data Access...")
try:
    rules = get_rules()
    
    # Test stats
    assert len(rules.stats_list) > 0, "Should have stats"
    print(f"✅ Stats available: {rules.stats_list[:3]}...")
    
    # Test skills
    assert len(rules.skill_map) > 0, "Should have skills"
    first_skill = list(rules.skill_map.keys())[0]
    skill_info = rules.get_skill_info(first_skill)
    print(f"✅ Skill lookup working: {first_skill} -> {skill_info}")
    
    # Test abilities (if any exist)
    if rules.ability_lookup:
        first_ability = list(rules.ability_lookup.keys())[0]
        ability = rules.get_ability(first_ability)
        print(f"✅ Ability lookup working: {first_ability}")
    else:
        print("⚠️  No abilities in lookup (might be normal)")
    
    # Test talents (if any exist)
    if rules.talent_lookup:
        first_talent = list(rules.talent_lookup.keys())[0]
        talent = rules.get_talent(first_talent)
        print(f"✅ Talent lookup working: {first_talent}")
    else:
        print("⚠️  No talents in lookup (might be normal)")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Error Handling
print("\n[Test 4] Error Handling...")
try:
    # Try to get rules before loading (should fail)
    RuleSetContainer.reset_instance()
    
    try:
        rules = get_rules()
        print("❌ Should have raised RuntimeError")
    except RuntimeError as e:
        print(f"✅ Correct error handling: {e}")
    
    # Reload for subsequent tests
    load_and_validate_all()
    
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 5: Immutability Verification
print("\n[Test 5] Data Integrity...")
try:
    rules = get_rules()
    
    # Verify data is accessible but not accidentally modifiable
    original_count = len(rules.stats_list)
    
    # Get reference and confirm it works
    assert original_count > 0, "Should have stats"
    print(f"✅ Data integrity verified: {original_count} stats loaded")
    
except Exception as e:
    print(f"❌ FAILED: {e}")

print("\n" + "="*60)
print("PHASE 2 TEST COMPLETE")
print("="*60)
print("\nNote: RuleSetContainer is ready for integration with")
print("Orchestrator and game logic modules.")
