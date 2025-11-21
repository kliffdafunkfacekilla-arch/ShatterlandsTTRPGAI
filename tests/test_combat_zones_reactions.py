import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add monolith root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../AI-TTRPG/monolith")))

from modules.story_pkg import combat_handler, models, schemas
from modules.character_pkg import services as char_services
from sqlalchemy.orm import Session

class MockDB:
    def commit(self): pass
    def refresh(self, obj): pass
    def add(self, obj): pass

class TestCombatZonesReactions(unittest.TestCase):

    def setUp(self):
        self.db = MockDB()
        self.combat = models.CombatEncounter(
            id=1,
            location_id=1,
            status="active",
            turn_order=["player_1", "npc_1"],
            current_turn_index=0,
            participants=[],
            active_zones=[],
            pending_reaction=None
        )
        self.combat.participants = [
            models.CombatParticipant(actor_id="player_1", actor_type="player", ability_usage={}),
            models.CombatParticipant(actor_id="npc_1", actor_type="npc", ability_usage={})
        ]
        self.log = []

    def test_create_area(self):
        effect = {
            "effect_id": "Fire Wall",
            "shape": "radius",
            "range": 1,
            "duration": 3,
            "zone_effects": [{"trigger": "on_enter", "type": "direct_damage"}]
        }
        defender_ctx = {"position_x": 5, "position_y": 5} # Target center

        combat_handler._handle_effect_create_area(
            self.db, self.combat, "player_1", "npc_1", {}, defender_ctx, self.log, effect
        )

        self.assertEqual(len(self.combat.active_zones), 1)
        zone = self.combat.active_zones[0]
        self.assertEqual(zone["name"], "Fire Wall")
        self.assertEqual(len(zone["tiles"]), 9) # Radius 1 = 3x3 = 9 tiles
        print("Zone created successfully.")

    @patch("modules.story_pkg.combat_handler._handle_effect_direct_damage")
    def test_zone_trigger_on_enter(self, mock_damage):
        # Setup Zone
        zone = {
            "id": "z1", "tiles": [[5,5]],
            "effects": [{"trigger": "on_enter", "type": "direct_damage"}],
            "name": "Fire"
        }
        self.combat.active_zones = [zone]

        # Trigger
        triggered = combat_handler._process_zone_triggers(
            self.db, self.combat, "player_1", "on_enter", [5,5], self.log
        )

        self.assertTrue(triggered)
        mock_damage.assert_called()
        print("Zone trigger confirmed.")

    @patch("modules.story_pkg.combat_handler.get_actor_context")
    def test_reaction_check(self, mock_get_ctx):
        # Setup Player with Threat Zone
        mock_get_ctx.side_effect = lambda aid: ("player", {"status_effects": ["Threat Zone"], "position_x": 0, "position_y": 0})

        player_p = self.combat.participants[0] # player_1

        event_data = {
            "old_coords": [0, 1], # Adjacent (Distance 1)
            "new_coords": [0, 5]  # Far away (Distance 5) -> Leaves range 3
        }

        reaction = combat_handler._check_for_player_reaction(
            self.db, self.combat, "actor_move", "npc_1", self.log, event_data
        )

        self.assertIsNotNone(reaction)
        self.assertEqual(reaction["reactor_id"], "player_1")
        self.assertEqual(reaction["reaction_name"], "Opportunity Attack")
        print("Reaction correctly identified.")

    def test_cleanup_zones(self):
        zone = {"id": "z1", "duration": 1, "name": "Short Lived"}
        self.combat.active_zones = [zone]
        self.combat.current_turn_index = 0 # End of round trigger

        combat_handler._cleanup_expired_zones(self.combat, self.log)
        self.assertEqual(len(self.combat.active_zones), 0)
        print("Zone cleanup successful.")

    @patch("modules.story_pkg.combat_handler._handle_basic_attack")
    @patch("modules.story_pkg.combat_handler.get_actor_context")
    @patch("modules.story_pkg.combat_handler.check_combat_end_condition")
    def test_resolve_reaction_turn_advance(self, mock_check_end, mock_get_ctx, mock_attack):
        # Setup Pending Reaction
        self.combat.pending_reaction = {
            "reactor_id": "player_1",
            "trigger_id": "npc_1",
            "reaction_name": "Opportunity Attack"
        }
        self.combat.current_turn_index = 1 # NPC's turn

        action = schemas.PlayerActionRequest(
            action="resolve_reaction",
            ready_action_details={"decision": "execute"}
        )

        mock_get_ctx.return_value = ("player", {"current_hp": 10, "max_hp": 10})
        mock_check_end.return_value = False

        response = combat_handler.handle_player_action(
            self.db, self.combat, "player_1", action
        )

        self.assertTrue(response.success)
        # Verify turn advanced (1 -> 0 for 2 participants)
        self.assertEqual(self.combat.current_turn_index, 0)
        print("Reaction resolved and turn advanced.")

if __name__ == '__main__':
    unittest.main()
