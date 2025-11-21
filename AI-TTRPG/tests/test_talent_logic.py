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
    
    eligible = find_eligible_talents(stats, skills, MOCK_TALENTS_DATA, list(stats.keys()), {skill: {} for skill in skills.keys()})
    
    names = [t.name for t in eligible]
    print(f"Eligible Talents: {names}")
    
    assert "Overpowering Presence" in names, "Should be eligible for Overpowering Presence"
    print("Eligibility Test Passed!")

def test_modifier_application():
    print("\nTesting Modifier Application...")
    data_loader.load_data()
    
    talents = [
        TalentInfo(
            name="Test Talent 1",
            source="talent",
            effect="test",
            modifiers=[
                PassiveModifier(type="skill_bonus", skill="Intimidation", bonus=2),
                PassiveModifier(type="resource_max", resource="Presence", bonus=1),
                PassiveModifier(type="immunity", tag="Poison"),
                PassiveModifier(type="action_cost", action="draw_weapon", new_cost="free"),
                PassiveModifier(type="reroll", skill="Knowledge")
            ]
        ),
        TalentInfo(
            name="Test Talent 2",
            source="talent",
            effect="test",
            modifiers=[
                PassiveModifier(type="skill_bonus", skill="Intimidation", bonus=1),
                PassiveModifier(type="defense_bonus", tag="Melee", bonus=2)
            ]
        )
    ]
    
    aggregated = apply_passive_modifiers({}, {}, talents)
    
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
