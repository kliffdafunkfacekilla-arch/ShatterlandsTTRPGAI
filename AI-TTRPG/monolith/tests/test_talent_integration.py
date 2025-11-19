import pytest
from unittest.mock import patch, MagicMock
from monolith.modules import rules
from monolith.modules.rules_pkg import models as rules_models

# Mock data for talents
MOCK_TALENT_DATA = {
    "Might Mastery": {
        "talent_name": "Might Mastery",
        "modifiers": [
            {"type": "stat_bonus", "stat": "Might", "bonus": 2},
            {"type": "contested_check", "stat": "Might", "bonus": 1}
        ]
    },
    "Sword Specialist": {
        "talent_name": "Sword Specialist",
        "modifiers": [
            {"type": "skill_bonus", "skill": "Swords", "bonus": 1},
            {"type": "damage_bonus", "bonus": 2}
        ]
    }
}

@pytest.fixture
def mock_get_talent_details():
    with patch("monolith.modules.rules.get_talent_details") as mock:
        def side_effect(name):
            return MOCK_TALENT_DATA.get(name)
        mock.side_effect = side_effect
        yield mock

def test_calculate_talent_bonuses_attack(mock_get_talent_details):
    character_context = {
        "talents": ["Might Mastery", "Sword Specialist"]
    }
    
    # Test Attack Roll with Might and Swords
    tags = ["Swords", "Melee", "Might"]
    bonuses = rules.calculate_talent_bonuses(character_context, "attack_roll", tags)
    
    # Expected:
    # Might Mastery: +1 to contested_check:Might (attack_roll_bonus)
    # Sword Specialist: +1 to skill:Swords (attack_roll_bonus)
    # Total attack_roll_bonus = 2
    
    assert bonuses["attack_roll_bonus"] == 2
    assert bonuses["damage_bonus"] == 0 # Not requested

def test_calculate_talent_bonuses_damage(mock_get_talent_details):
    character_context = {
        "talents": ["Might Mastery", "Sword Specialist"]
    }
    
    # Test Damage Roll
    tags = ["Swords", "Melee", "Might"]
    bonuses = rules.calculate_talent_bonuses(character_context, "damage_roll", tags)
    
    # Expected:
    # Sword Specialist: +2 damage_bonus
    
    assert bonuses["damage_bonus"] == 2
    assert bonuses["attack_roll_bonus"] == 0

def test_calculate_talent_bonuses_defense(mock_get_talent_details):
    character_context = {
        "talents": ["Might Mastery"] # Might doesn't help defense usually, but let's say we have a Reflexes talent
    }
    
    # Mock a Reflexes talent
    MOCK_TALENT_DATA["Reflexes Mastery"] = {
        "talent_name": "Reflexes Mastery",
        "modifiers": [
            {"type": "contested_check", "stat": "Reflexes", "bonus": 2}
        ]
    }
    character_context["talents"] = ["Reflexes Mastery"]
    
    tags = ["Light Armor", "Reflexes"]
    bonuses = rules.calculate_talent_bonuses(character_context, "defense_roll", tags)
    
    # Expected:
    # Reflexes Mastery: +2 to contested_check:Reflexes (defense_roll_bonus)
    
    assert bonuses["defense_roll_bonus"] == 2
