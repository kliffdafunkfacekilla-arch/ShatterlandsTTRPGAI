# tests/test_combat_talents.py
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['fastapi'] = MagicMock()
sys.modules['httpx'] = MagicMock()
sys.modules['pydantic'] = MagicMock()

# Mock internal modules that import external dependencies
sys.modules['monolith.modules.story_pkg.crud'] = MagicMock()
sys.modules['monolith.modules.story_pkg.models'] = MagicMock()
sys.modules['monolith.modules.story_pkg.schemas'] = MagicMock()
sys.modules['monolith.modules.story_pkg.database'] = MagicMock()
sys.modules['monolith.modules.rules'] = MagicMock()
sys.modules['monolith.modules.rules_pkg'] = MagicMock() # Added this
sys.modules['monolith.modules.rules_pkg.core'] = MagicMock() # Added this
sys.modules['monolith.modules.world'] = MagicMock() # Added this
sys.modules['monolith.modules.character'] = MagicMock() # Added this

from monolith.modules.story_pkg import combat_handler
from monolith.modules.story_pkg import services

# Inject missing helper functions into combat_handler if they aren't found
if not hasattr(combat_handler, 'get_skill_rank'):
    combat_handler.get_skill_rank = MagicMock()
if not hasattr(combat_handler, 'get_stat_score'):
    combat_handler.get_stat_score = MagicMock()
if not hasattr(combat_handler, 'get_equipped_weapon'):
    combat_handler.get_equipped_weapon = MagicMock(return_value=("Melee", "Sword"))
if not hasattr(combat_handler, 'get_equipped_armor'):
    combat_handler.get_equipped_armor = MagicMock(return_value="Heavy")
if not hasattr(combat_handler, 'get_actor_context'):
    combat_handler.get_actor_context = MagicMock(return_value=("player", {}))

class TestCombatTalents(unittest.TestCase):

    @patch('monolith.modules.story_pkg.services.rules_api')
    @patch('monolith.modules.story_pkg.services.roll_contested_attack')
    @patch('monolith.modules.story_pkg.services.get_weapon_data')
    @patch('monolith.modules.story_pkg.services.get_armor_data')
    def test_handle_basic_attack_with_talents(self, mock_get_armor, mock_get_weapon, mock_roll, mock_rules):
        # Setup mocks
        mock_get_weapon.return_value = {"skill_stat": "Might", "skill": "Great Weapons", "penalty": 0}
        mock_get_armor.return_value = {"skill_stat": "Reflexes", "skill": "Natural/Unarmored", "dr": 0}
        
        # Configure injected mocks
        combat_handler.get_stat_score.return_value = 10
        combat_handler.get_skill_rank.return_value = 1
        
        # Mock talent bonuses
        # Attacker gets +2
        mock_rules.calculate_talent_bonuses.side_effect = [
            {"attack_roll_bonus": 2}, # Attacker call
            {"defense_roll_bonus": 0}  # Defender call
        ]
        
        # Dummy contexts
        attacker_context = {"id": "player_1", "talents": ["Strong"]}
        defender_context = {"id": "npc_1"}
        
        # Call the function
        combat_handler._handle_basic_attack(
            db=MagicMock(),
            combat=MagicMock(),
            actor_id="player_1",
            target_id="npc_1",
            attacker_context=attacker_context,
            defender_context=defender_context,
            log=[]
        )
        
        # Verify roll_contested_attack was called with the bonus
        args, kwargs = mock_roll.call_args
        attack_params = args[0]
        
        # Check if bonus was applied (0 base + 2 talent = 2)
        self.assertEqual(attack_params["attacker_attack_roll_bonus"], 2)

if __name__ == '__main__':
    unittest.main()
