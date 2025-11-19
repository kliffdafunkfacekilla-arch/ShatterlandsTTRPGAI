# tests/test_talent_logic.py
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from monolith.modules.rules_pkg import talent_logic

class TestTalentLogic(unittest.TestCase):

    def setUp(self):
        # Mock data_loader to provide test talent data
        self.mock_data = {
            "single_stat_mastery": [
                {
                    "talent_name": "Test Might Talent",
                    "modifiers": [
                        {"type": "contested_check", "stat": "Might", "bonus": 2}
                    ]
                }
            ],
            "dual_stat_focus": [],
            "single_skill_mastery": {}
        }
        
        # Patch the data_loader in talent_logic
        self.patcher = patch('monolith.modules.rules_pkg.talent_logic.data_loader')
        self.mock_loader = self.patcher.start()
        self.mock_loader.TALENT_DATA = self.mock_data

    def tearDown(self):
        self.patcher.stop()

    def test_calculate_bonuses_basic(self):
        character_context = {
            "talents": ["Test Might Talent"]
        }
        
        # Test matching tag
        bonuses = talent_logic.calculate_talent_bonuses(
            character_context, 
            "contested_check", 
            tags=["Might"]
        )
        self.assertEqual(bonuses["attack_roll_bonus"], 2)
        self.assertEqual(bonuses["defense_roll_bonus"], 2)

    def test_calculate_bonuses_no_match(self):
        character_context = {
            "talents": ["Test Might Talent"]
        }
        
        # Test non-matching tag (Intimidation vs Might)
        bonuses = talent_logic.calculate_talent_bonuses(
            character_context, 
            "contested_check", 
            tags=["Intimidation"]
        )
        # Should be 0 because the modifier requires 'stat': 'Might' and we passed 'Intimidation'
        # Wait, logic says: if target_stat and target_stat not in tags: continue
        self.assertEqual(bonuses["attack_roll_bonus"], 0)

    def test_calculate_bonuses_wrong_action(self):
        character_context = {
            "talents": ["Test Might Talent"]
        }
        
        # Test wrong action type
        bonuses = talent_logic.calculate_talent_bonuses(
            character_context, 
            "damage_roll", 
            tags=["Might"]
        )
        self.assertEqual(bonuses["damage_bonus"], 0)

if __name__ == '__main__':
    unittest.main()
