import sys
import os
import json
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from monolith.modules.rules_pkg.talent_logic import find_eligible_talents, get_talent_modifiers
from monolith.modules.character_pkg.services import apply_passive_modifiers
from monolith.modules.character_pkg.models import Character
from monolith.modules.rules_pkg.models import TalentInfo, PassiveModifier, SingleStatTalent, SingleSkillTalent, DualStatTalent, Talents
from monolith.modules.rules_pkg import data_loader

def test_eligibility():
    print("Testing Talent Eligibility...")
    data_loader.load_data()

    # Case 1: Eligible for Single Stat
    stats = {"Might": 14, "Agility": 12, "Endurance": 10, "Vitality": 10, "Reflexes": 10, "Fortitude": 10,
             "Knowledge": 10, "Logic": 10, "Awareness": 10, "Intuition": 10, "Charm": 10, "Willpower": 10}
    skills = {"Swords": {"rank": 1}}
    
    eligible = find_eligible_talents(stats, skills)
    
    names = [t.get("talent_name") or t.get("name") for t in eligible]
    print(f"Eligible Talents: {names}")
    
    assert "Overpowering Presence" in names, "Should be eligible for Overpowering Presence"
    print("Eligibility Test Passed!")

def test_modifier_application():
    print("\nTesting Modifier Application...")
    data_loader.load_data()
    
    mock_character = Character(
        id="test",
        name="Test Character",
        stats={"Might": 14},
        skills={},
        talents=["Overpowering Presence", "Unfailing Stamina"],
        equipment={
            "combat": {
                "chest": {
                    "id": "item_leather_jerkin",
                    "dr": 1
                }
            }
        }
    )

    modified_stats, total_dr = apply_passive_modifiers(mock_character)
    
    print("Modified Stats:", json.dumps(modified_stats, indent=2, default=str))
    print("Total DR:", total_dr)
    
    assert modified_stats["Might"] > 14, "Might should be modified by Overpowering Presence"
    assert total_dr == 1, "DR should be 1 from leather jerkin"
    
    print("Modifier Application Test Passed!")

if __name__ == "__main__":
    try:
        test_eligibility()
        test_modifier_application()
        print("\nALL TESTS PASSED")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
