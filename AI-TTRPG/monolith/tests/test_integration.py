import unittest
from monolith.modules.rules_pkg import core
from monolith.modules.rules_pkg.models import (
    SocialEncounterRequest, RestRequest, StealthRequest
)
from monolith.modules.rules_pkg.models_inventory import Inventory, Item

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.engine = core.RulesEngine()
        
    def test_derived_stats(self):
        stats = {
            "Might": 10, "Reflexes": 10, "Awareness": 10, "Fortitude": 10,
            "Vitality": 10, "Intuition": 10, "Charm": 10, "Knowledge": 10,
            "Endurance": 10, "Logic": 10, "Finesse": 10, "Willpower": 10
        }
        derived = self.engine.calculate_derived_stats(stats)
        
        # Movement: (10+10+10+10)//4 = 10. Speed = 20 + 50 = 70
        self.assertEqual(derived["movement"]["base_speed_ft"], 70)
        
        # Operation: (10+10+10+10)//4 = 10
        self.assertEqual(derived["operation_stat"], 10)
        
        # Weight Cap: (10+10+10+10)*5 = 200.0
        self.assertEqual(derived["weight_capacity"], 200.0)

    def test_inventory_flow(self):
        inv = Inventory()
        sword = Item(
            name="Test Sword", type="weapon", category="Great Weapons",
            weight=10.0, slots=["Main Hand"], damage_dice="1d12"
        )
        inv.items.append(sword)
        
        # Equip
        success, msg = self.engine.equip_item(inv, sword, "Main Hand")
        self.assertTrue(success)
        self.assertEqual(inv.equipped_slots["Main Hand"], sword)
        self.assertNotIn(sword, inv.items)
        
        # Encumbrance
        # Weight 10. Cap 100. Should be Light.
        status = self.engine.calculate_encumbrance(inv, 100.0)
        self.assertEqual(status, "Light")
        
        # Use Potion
        potion = Item(
            name="Potion", type="consumable", category="potion",
            effects=[{"type": "heal", "value": 10, "description": "Heals"}]
        )
        inv.items.append(potion)
        success, msg, effect = self.engine.use_item(inv, potion)
        self.assertTrue(success)
        self.assertEqual(effect["heal"], 10)
        self.assertNotIn(potion, inv.items)

    def test_social_encounter(self):
        req = SocialEncounterRequest(
            attacker_skill="Intimidation",
            attacker_stat_score=5,
            attacker_skill_rank=2,
            defender_willpower_score=2,
            defender_skill_rank=0
        )
        res = self.engine.resolve_social_encounter(req)
        self.assertIn(res.outcome, ["Success", "Failure", "Critical Success", "Critical Failure", "resounding_success"])
        
    def test_rest(self):
        req = RestRequest(
            comfort_level=5, security_level=5, food_quality=5,
            prep_focus="tend_wounds", duration_hours=8
        )
        res = self.engine.calculate_rest(req)
        # Quality 15. HP = 30 + 5 = 35.
        self.assertEqual(res.hp_recovered, 35)
        self.assertIn("Well Rested", res.buffs_gained)

if __name__ == '__main__':
    unittest.main()
