from typing import Dict, List, Tuple
from .models import SocialEncounterRequest, SocialEncounterResponse
import random

# Stat Advantage Matrix
# Physical stats (A-F) vs Mental stats (G-L)
# Each physical stat is strong against one mental stat and weak against another
STAT_ADVANTAGES = {
    # Physical Stats
    "Might": {"strong_against": "Knowledge", "weak_against": "Intuition"},
    "Endurance": {"strong_against": "Logic", "weak_against": "Charm"},
    "Finesse": {"strong_against": "Awareness", "weak_against": "Willpower"},
    "Reflexes": {"strong_against": "Intuition", "weak_against": "Knowledge"},
    "Vitality": {"strong_against": "Charm", "weak_against": "Logic"},
    "Fortitude": {"strong_against": "Willpower", "weak_against": "Awareness"},
    
    # Mental Stats (inverse of physical)
    "Knowledge": {"strong_against": "Reflexes", "weak_against": "Might"},
    "Logic": {"strong_against": "Vitality", "weak_against": "Endurance"},
    "Awareness": {"strong_against": "Fortitude", "weak_against": "Finesse"},
    "Intuition": {"strong_against": "Might", "weak_against": "Reflexes"},
    "Charm": {"strong_against": "Endurance", "weak_against": "Vitality"},
    "Willpower": {"strong_against": "Finesse", "weak_against": "Fortitude"}
}

# Conversational Skills mapped to their stats
CONVERSATIONAL_SKILLS = {
    "Intimidation": "Might",
    "Resilience": "Endurance",
    "Slight of Hand": "Finesse",
    "Evasion": "Reflexes",
    "Comfort": "Vitality",
    "Discipline": "Fortitude",
    "Debate": "Knowledge",
    "Rhetoric": "Logic",
    "Insight": "Awareness",
    "Empathy": "Intuition",
    "Persuasion": "Charm",
    "Negotiations": "Willpower"
}

def calculate_advantage_modifier(attacker_stat: str, defender_stat: str) -> int:
    """
    Calculates the advantage modifier based on stat matchup.
    Returns: +2 for advantage, -2 for disadvantage, 0 for neutral.
    """
    if attacker_stat not in STAT_ADVANTAGES or defender_stat not in STAT_ADVANTAGES:
        return 0
    
    advantages = STAT_ADVANTAGES[attacker_stat]
    
    if advantages["strong_against"] == defender_stat:
        return 2
    elif advantages["weak_against"] == defender_stat:
        return -2
    else:
        return 0

def resolve_social_exchange(request: SocialEncounterRequest) -> SocialEncounterResponse:
    """
    Resolves a single exchange in a social encounter.
    Mechanic: Attacker rolls d20 + Stat + Skill vs Defender's d20 + Stat + Skill.
    Stat advantages apply bonuses/penalties.
    """
    
    # Get the stats for the skills being used
    attacker_base_stat = CONVERSATIONAL_SKILLS.get(request.attacker_skill, "Charm")
    defender_base_stat = CONVERSATIONAL_SKILLS.get(request.defender_skill, "Willpower") if hasattr(request, 'defender_skill') and request.defender_skill else "Willpower"
    
    # Calculate advantage modifier
    advantage_mod = calculate_advantage_modifier(attacker_base_stat, defender_base_stat)
    
    # Attacker Roll
    attacker_d20 = random.randint(1, 20)
    attacker_modifier = request.attacker_stat_score + request.attacker_skill_rank + request.context_modifiers + advantage_mod
    attacker_total = attacker_d20 + attacker_modifier
    
    # Defender Roll (contested)
    defender_d20 = random.randint(1, 20)
    defender_modifier = request.defender_willpower_score + request.defender_skill_rank
    defender_total = defender_d20 + defender_modifier
    
    # Determine outcome
    margin = attacker_total - defender_total
    outcome = "Failure"
    composure_damage = 0
    
    if attacker_d20 == 20:
        outcome = "Critical Success"
        composure_damage = 3 + (request.attacker_stat_score // 2)
    elif attacker_d20 == 1:
        outcome = "Critical Failure"
        # Attacker may take composure damage on fumble
    elif defender_d20 == 20:
        outcome = "Critical Defense"
        # Defender completely shuts down the attempt
    elif margin >= 10:
        outcome = "Resounding Success"
        composure_damage = 2
    elif margin >= 5:
        outcome = "Success"
        composure_damage = 1
    elif margin >= 0:
        outcome = "Marginal Success"
        composure_damage = 1
    else:
        outcome = "Failure"
        
    return SocialEncounterResponse(
        roll_value=attacker_d20,
        total_value=attacker_total,
        target_dc=defender_total,
        outcome=outcome,
        composure_damage=composure_damage
    )
