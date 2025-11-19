import sys
import os
import json
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from monolith.modules.rules_pkg.core import find_eligible_talents, apply_passive_modifiers
from monolith.modules.rules_pkg.models import TalentInfo, PassiveModifier, SingleStatTalent, SingleSkillTalent, DualStatTalent, Talents

# Mock Data
MOCK_TALENTS_DATA = {
    "single_stat_mastery": [
        {
            "stat": "Might",
            "talent_name": "Mighty Blow",
            "effect": "Hit harder",
            "modifiers": [{"type": "damage_bonus", "bonus": 2}]
        }
    ],
    "single_skill_mastery": [
        {
            "skill": "Swords",
            "stat_focus": "Might",
            "talent_name": "Sword Master",
            "prerequisite_mt": "MT 1",
            "focus": "Damage",
            "effect": "Better swords",
            "modifiers": [{"type": "skill_bonus", "skill": "Swords", "bonus": 1}]
        }
    ],
    "dual_stat_focus": [
        {
            "paired_stats": ["Might", "Agility"], # OLD KEY - should be ignored or handled if we didn't fix it? 
                                                  # Wait, we fixed the code to look for 'stats', so we should provide 'stats' here if we want it to work, 
                                                  # OR provide the old key to verify it FAILS if we didn't fix it?
                                                  # The JSON has 'stats' usually? Let's check the JSON structure in a bit.
                                                  # The code change was `stats_pair = talent.get("stats", [])`.
            "stats": ["Might", "Agility"], # NEW KEY
            "synergy_focus": "Movement",
            "tier": "Tier 1",
            "talent_name": "Fast & Strong",
            "effect": "Move fast hit hard",
            "score": 10,
            "modifiers": [{"type": "initiative", "bonus": 5}]
        }
    ]
}

def test_eligibility():
    print("Testing Talent Eligibility...")
    
    # Case 1: Eligible for Single Stat
    stats = {"Might": 12, "Agility": 12, "Endurance": 10, "Vitality": 10, "Reflexes": 10, "Fortitude": 10, 
             "Intellect": 10, "Logic": 10, "Awareness": 10, "Intuition": 10, "Confidence": 10, "Willpower": 10}
    skills = {"Swords": 1}
    
    # We need to mock the loading of talents because find_eligible_talents loads from JSON usually?
    # Actually find_eligible_talents takes `talent_data` as an argument if we look at the signature...
    # Wait, let me check the signature of find_eligible_talents in core.py
    # It is: def find_eligible_talents(stats: Dict[str, int], skills: Dict[str, int], talent_data: Dict = None) -> List[TalentInfo]:
    
    eligible = find_eligible_talents(stats, skills, MOCK_TALENTS_DATA, list(stats.keys()), {skill: {} for skill in skills.keys()})
    
    names = [t.name for t in eligible]
    print(f"Eligible Talents: {names}")
    
    assert "Mighty Blow" in names, "Should be eligible for Mighty Blow"
    assert "Fast & Strong" in names, "Should be eligible for Fast & Strong"
    # Sword Master might require specific logic check (e.g. MT 1?). 
    # In core.py: 
    # for talent in talent_data.get("single_skill_mastery", []):
    #    req_skill = talent.get("skill")
    #    # It checks if skills[req_skill] >= 1 usually?
    #    if skills.get(req_skill, 0) >= 1: ...
    
    assert "Sword Master" in names, "Should be eligible for Sword Master"
    print("Eligibility Test Passed!")

def test_modifier_application():
    print("\nTesting Modifier Application...")
    
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
    
    print("Aggregated Modifiers:", json.dumps(aggregated, indent=2, default=str))
    
    assert aggregated["skill_bonuses"]["Intimidation"] == 3, "Intimidation bonus should be 3"
    assert aggregated["resource_max_bonuses"]["Presence"] == 1, "Presence max bonus should be 1"
    assert aggregated["defense_bonuses"]["Melee"] == 2, "Melee defense bonus should be 2"
    assert len(aggregated["immunities"]) == 1, "Should have 1 immunity"
    assert aggregated["immunities"][0].tag == "Poison", "Immunity should be Poison"
    assert "draw_weapon" in aggregated["action_cost_reductions"], "Should have draw_weapon cost reduction"
    assert len(aggregated["rerolls"]) == 1, "Should have 1 reroll"
    
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
