import unittest
import os
import shutil
import sys

# Add AI-TTRPG to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'AI-TTRPG')))

from monolith.modules.lore import LoreManager

class TestLoreManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary lore directory for testing
        self.test_lore_dir = "tests/temp_lore"
        os.makedirs(self.test_lore_dir, exist_ok=True)
        
        # Create dummy lore files
        with open(os.path.join(self.test_lore_dir, "foundations.txt"), "w", encoding="utf-8") as f:
            f.write("This is the foundation lore.")
            
        with open(os.path.join(self.test_lore_dir, "Coastal_Theocracy.txt"), "w", encoding="utf-8") as f:
            f.write("Lore about the Coastal Theocracy.")
            
        with open(os.path.join(self.test_lore_dir, "Canopy_Clans.txt"), "w", encoding="utf-8") as f:
            f.write("Lore about the Canopy Clans.")

    def tearDown(self):
        # Clean up
        if os.path.exists(self.test_lore_dir):
            shutil.rmtree(self.test_lore_dir)

    def test_load_lore(self):
        manager = LoreManager(lore_dir=self.test_lore_dir)
        self.assertIn("foundations.txt", manager.lore_cache)
        self.assertIn("Coastal_Theocracy.txt", manager.lore_cache)
        self.assertEqual(manager.lore_cache["foundations.txt"], "This is the foundation lore.")

    def test_get_lore_context_no_tags(self):
        manager = LoreManager(lore_dir=self.test_lore_dir)
        context = manager.get_lore_context()
        self.assertIn("This is the foundation lore.", context)

    def test_get_lore_context_with_tags(self):
        manager = LoreManager(lore_dir=self.test_lore_dir)
        
        # Test direct filename match
        context = manager.get_lore_context(tags=["Coastal"])
        self.assertIn("Lore about the Coastal Theocracy.", context)
        self.assertNotIn("Lore about the Canopy Clans.", context)
        
        # Test keyword mapping (assuming "forest" maps to Canopy_Clans)
        context = manager.get_lore_context(tags=["forest"])
        self.assertIn("Lore about the Canopy Clans.", context)

    def test_get_lore_context_fallback(self):
        manager = LoreManager(lore_dir=self.test_lore_dir)
        # Unknown tag should fallback to foundations
        context = manager.get_lore_context(tags=["UnknownTag"])
        self.assertIn("This is the foundation lore.", context)

if __name__ == "__main__":
    unittest.main()
