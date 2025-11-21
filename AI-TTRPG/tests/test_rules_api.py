import unittest
import sys
from unittest.mock import MagicMock

# Mock pydantic
mock_pydantic = MagicMock()
mock_pydantic.BaseModel = object
mock_pydantic.Field = MagicMock()
mock_pydantic.field_validator = MagicMock()
sys.modules["pydantic"] = mock_pydantic

from monolith.modules import rules

class TestRulesAPI(unittest.TestCase):
    def test_get_talent_details(self):
        # Test Single Stat Mastery
        talent = rules.get_talent_details("Overpowering Presence")
        self.assertIsNotNone(talent)
        self.assertEqual(talent.get("stat"), "Might")
        self.assertTrue(len(talent.get("modifiers", [])) > 0)

        # Test Dual Stat Focus
        talent = rules.get_talent_details("Colossal Physique")
        self.assertIsNotNone(talent)
        self.assertEqual(talent.get("score"), 14)
        
        # Test Non-existent
        talent = rules.get_talent_details("Fake Talent")
        self.assertEqual(talent, {})

if __name__ == '__main__':
    unittest.main()
