"""
Integration tests for Map Flavor feature.
Focuses on LLM Service validation and data persistence.
"""
import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Add AI-TTRPG to path to handle the hyphenated directory name
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../AI-TTRPG')))

from monolith.modules.map_pkg import models as map_models
from monolith.modules.ai_dm_pkg.llm_service import LLMService
from monolith.modules.world_pkg import crud as world_crud


class TestFlavorIntegration(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()
        self.llm_service = LLMService()
        # Mock the internal model to avoid real API calls
        self.llm_service.model = MagicMock()

    def test_llm_service_schema_validation_success(self):
        """Test that valid JSON from LLM is parsed correctly."""
        valid_json = """
        {
            "environment_description": "A spooky forest.",
            "visuals": ["Twisted trees", "Fog"],
            "sounds": ["Creaking wood"],
            "smells": ["Damp earth"],
            "combat_hits": ["You smash it against a tree."],
            "combat_misses": ["You trip over a root."],
            "spell_casts": ["Shadows gather."],
            "enemy_intros": ["A wolf howls."]
        }
        """
        mock_response = MagicMock()
        mock_response.text = valid_json
        self.llm_service.model.generate_content.return_value = mock_response

        result = self.llm_service.generate_map_flavor(["forest"])
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['environment_description'], "A spooky forest.")
        self.assertEqual(result['visuals'], ["Twisted trees", "Fog"])

    def test_llm_service_schema_validation_failure(self):
        """Test that invalid JSON triggers fallback."""
        invalid_json = "{ 'this is not valid json' }"
        mock_response = MagicMock()
        mock_response.text = invalid_json
        self.llm_service.model.generate_content.return_value = mock_response

        result = self.llm_service.generate_map_flavor(["forest"])
        
        # Should return fallback
        self.assertIn("environment_description", result)
        self.assertEqual(result['environment_description'], "A quiet area with nothing notable.")

    def test_llm_service_no_model_fallback(self):
        """Test that missing model triggers fallback."""
        service_no_model = LLMService()
        service_no_model.model = None
        
        result = service_no_model.generate_map_flavor(["dungeon"])
        
        # Should return fallback
        self.assertIn("environment_description", result)
        self.assertEqual(result['environment_description'], "A quiet area with nothing notable.")

    def test_map_flavor_context_model(self):
        """Test that MapFlavorContext Pydantic model validates correctly."""
        # Valid data
        valid_data = {
            "environment_description": "Test environment",
            "visuals": ["Visual 1", "Visual 2"],
            "sounds": ["Sound 1"],
            "smells": ["Smell 1"],
            "combat_hits": ["Hit 1", "Hit 2"],
            "combat_misses": ["Miss 1"],
            "spell_casts": ["Spell 1"],
            "enemy_intros": ["Intro 1"]
        }
        
        flavor = map_models.MapFlavorContext(**valid_data)
        self.assertEqual(flavor.environment_description, "Test environment")
        self.assertEqual(len(flavor.visuals), 2)
        
        # Test defaults
        minimal_flavor = map_models.MapFlavorContext()
        self.assertEqual(minimal_flavor.environment_description, "A generic area.")
        self.assertEqual(minimal_flavor.visuals, [])


if __name__ == '__main__':
    unittest.main()
