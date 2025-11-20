import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from monolith.modules.character_pkg.database import Base
from monolith.modules.character_pkg import models, services, schemas
from monolith.modules.rules_pkg.models_inventory import Item

# Mock rules data
MOCK_ITEM_TEMPLATES = {
    "item_sword": {
        "name": "Sword", "item_type": "weapon", "category": "blade", "weight": 2.0,
        "slots": ["main_hand", "off_hand"], "damage_dice": "1d8"
    },
    "item_shield": {
        "name": "Shield", "item_type": "armor", "category": "shield", "weight": 4.0,
        "slots": ["off_hand"], "dr": 2
    },
    "item_ring": {
        "name": "Ring", "item_type": "accessory", "category": "jewelry", "weight": 0.1,
        "slots": ["ring_l1", "ring_r1"], "value": 50
    },
    "item_helmet": {
        "name": "Helmet", "item_type": "armor", "category": "plate", "weight": 3.0,
        "slots": ["head"], "dr": 2
    }
}

class TestCharacterServices(unittest.TestCase):
    def setUp(self):
        # Setup in-memory DB
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        # Create a test character
        self.character = models.Character(
            id="char_1",
            name="Test Char",
            kingdom="Test Kingdom",
            level=1,
            stats={"Might": 10},
            skills={},
            max_hp=10,
            current_hp=10,
            max_composure=10,
            current_composure=10,
            resource_pools={},
            talents=[],
            abilities=[],
            inventory={"item_sword": 1, "item_shield": 1, "item_ring": 2},
            equipment={
                "combat": {},
                "accessories": {},
                "equipped_gear": None
            },
            status_effects=[],
            injuries=[],
            current_location_id=1,
            position_x=0,
            position_y=0
        )
        self.db.add(self.character)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    @patch("monolith.modules.character_pkg.services.get_item_template")
    def test_equip_item_valid(self, mock_get_item):
        def side_effect(item_id):
            if item_id in MOCK_ITEM_TEMPLATES:
                return Item(**MOCK_ITEM_TEMPLATES[item_id])
            return None
        mock_get_item.side_effect = side_effect
        
        # Equip sword to main_hand
        updated_char = services.equip_item(self.db, "char_1", "item_sword", "main_hand")
        
        self.assertIsNotNone(updated_char)
        # Using 'id' instead of 'item_id' as per services logic (stores the whole model dump + id)
        self.assertEqual(updated_char.equipment["combat"]["main_hand"]["id"], "item_sword")
        # Inventory should decrease
        self.assertNotIn("item_sword", updated_char.inventory) # started with 1, used 1

    @patch("monolith.modules.character_pkg.services.get_item_template")
    def test_equip_item_invalid_slot(self, mock_get_item):
        def side_effect(item_id):
            if item_id in MOCK_ITEM_TEMPLATES:
                return Item(**MOCK_ITEM_TEMPLATES[item_id])
            return None
        mock_get_item.side_effect = side_effect
        
        # Try to equip sword to head
        updated_char = services.equip_item(self.db, "char_1", "item_sword", "head")
        
        self.assertIsNone(updated_char)
        # Verify nothing changed
        char = services.get_character(self.db, "char_1")
        self.assertIsNone(char.equipment["combat"].get("head"))

    @patch("monolith.modules.character_pkg.services.get_item_template")
    def test_equip_accessory(self, mock_get_item):
        def side_effect(item_id):
            if item_id in MOCK_ITEM_TEMPLATES:
                return Item(**MOCK_ITEM_TEMPLATES[item_id])
            return None
        mock_get_item.side_effect = side_effect
        
        updated_char = services.equip_item(self.db, "char_1", "item_ring", "ring_l1")
        
        self.assertIsNotNone(updated_char)
        self.assertEqual(updated_char.equipment["accessories"]["ring_l1"]["id"], "item_ring")
        self.assertEqual(updated_char.inventory["item_ring"], 1) # started with 2

    @patch("monolith.modules.character_pkg.services.get_item_template")
    def test_equip_swap(self, mock_get_item):
        # To test swap properly, let's use a different item compatible with same slot if possible,
        # or just verify inventory count.
        # Let's add a different weapon "item_axe" to mock
        MOCK_ITEM_TEMPLATES["item_axe"] = {
            "name": "Axe", "item_type": "weapon", "category": "axe", "weight": 3.0,
            "slots": ["main_hand"], "damage_dice": "1d10"
        }

        def side_effect(item_id):
            if item_id in MOCK_ITEM_TEMPLATES:
                return Item(**MOCK_ITEM_TEMPLATES[item_id])
            return None
        mock_get_item.side_effect = side_effect

        # First equip sword
        services.equip_item(self.db, "char_1", "item_sword", "main_hand")

        # Add another sword to inventory
        services.add_item_to_character(self.db, "char_1", "item_sword", 1)

        services.add_item_to_character(self.db, "char_1", "item_axe", 1)
        
        # Equip Axe to main_hand (swapping out Sword)
        updated_char = services.equip_item(self.db, "char_1", "item_axe", "main_hand")
        
        self.assertEqual(updated_char.equipment["combat"]["main_hand"]["id"], "item_axe")
        # Sword should be back in inventory
        self.assertEqual(updated_char.inventory.get("item_sword"), 2)
        # Axe should be removed from inventory
        self.assertNotIn("item_axe", updated_char.inventory)

if __name__ == '__main__':
    unittest.main()
