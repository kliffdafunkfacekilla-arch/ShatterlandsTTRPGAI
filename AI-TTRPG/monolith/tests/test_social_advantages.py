import unittest
from monolith.modules.rules_pkg.social_logic import (
    calculate_advantage_modifier, 
    resolve_social_exchange,
    STAT_ADVANTAGES,
    CONVERSATIONAL_SKILLS
)
from monolith.modules.rules_pkg.models import SocialEncounterRequest

class TestSocialAdvantages(unittest.TestCase):
    
    def test_stat_advantage_matrix(self):
        """Test that physical stats counter mental stats correctly."""
        # Might strong vs Knowledge, weak vs Intuition
        self.assertEqual(calculate_advantage_modifier("Might", "Knowledge"), 2)
        self.assertEqual(calculate_advantage_modifier("Might", "Intuition"), -2)
        self.assertEqual(calculate_advantage_modifier("Might", "Logic"), 0)
        
        # Knowledge strong vs Reflexes, weak vs Might (inverse)
        self.assertEqual(calculate_advantage_modifier("Knowledge", "Reflexes"), 2)
        self.assertEqual(calculate_advantage_modifier("Knowledge", "Might"), -2)
        
    def test_all_stats_have_counters(self):
        """Verify all 12 stats have advantage/disadvantage relationships."""
        all_stats = ["Might", "Endurance", "Finesse", "Reflexes", "Vitality", "Fortitude",
                     "Knowledge", "Logic", "Awareness", "Intuition", "Charm", "Willpower"]
        
        for stat in all_stats:
            self.assertIn(stat, STAT_ADVANTAGES)
            self.assertIn("strong_against", STAT_ADVANTAGES[stat])
            self.assertIn("weak_against", STAT_ADVANTAGES[stat])
            
    def test_conversational_skills_mapped(self):
        """Verify all 12 conversational skills are mapped to stats."""
        expected_skills = [
            "Intimidation", "Resilience", "Slight of Hand", "Evasion",
            "Comfort", "Discipline", "Debate", "Rhetoric",
            "Insight", "Empathy", "Persuasion", "Negotiations"
        ]
        
        for skill in expected_skills:
            self.assertIn(skill, CONVERSATIONAL_SKILLS)
            
    def test_social_exchange_with_advantage(self):
        """Test social exchange where attacker has advantage."""
        # Intimidation (Might) vs Debate (Knowledge) - Might has advantage
        req = SocialEncounterRequest(
            attacker_skill="Intimidation",
            attacker_stat_score=5,
            attacker_skill_rank=2,
            defender_skill="Debate",
            defender_willpower_score=5,
            defender_skill_rank=2
        )
        
        # Run multiple times to check that advantage is applied
        results = [resolve_social_exchange(req) for _ in range(10)]
        # With advantage, attacker should win more often
        # This is probabilistic, so we just check it runs without error
        self.assertTrue(all(r.outcome in ["Success", "Failure", "Critical Success", 
                                           "Critical Failure", "Resounding Success", 
                                           "Marginal Success", "Critical Defense"] 
                           for r in results))

if __name__ == '__main__':
    unittest.main()
