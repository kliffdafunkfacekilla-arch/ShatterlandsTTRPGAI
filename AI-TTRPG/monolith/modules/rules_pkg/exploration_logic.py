from typing import Dict, List, Tuple
from .models import RestRequest, RestResponse, StealthRequest, StealthResponse
import random

# --- REST SYSTEM ---

def calculate_rest_benefits(request: RestRequest) -> RestResponse:
    """
    Calculates HP/Resource recovery based on rest quality.
    """
    # Base recovery
    hp_recovery = 0
    resources = {}
    buffs = []
    fatigue_removed = 0
    
    # Quality Score (0-15)
    quality_score = request.comfort_level + request.security_level + request.food_quality
    
    # Duration Factor
    hours = request.duration_hours
    
    if hours >= 8:
        # Long Rest
        hp_recovery = quality_score * 2  # Example formula
        fatigue_removed = 1
        if quality_score > 10:
            buffs.append("Well Rested")
            
        # Prep Focus
        if request.prep_focus == "tend_wounds":
            hp_recovery += 5
        elif request.prep_focus == "meditate":
            resources["Focus"] = 10 # Example resource
        elif request.prep_focus == "inspire":
            buffs.append("Inspired")
            
    elif hours >= 1:
        # Short Rest
        hp_recovery = quality_score // 2
        if request.prep_focus == "tend_wounds":
            hp_recovery += 2
            
    return RestResponse(
        hp_recovered=hp_recovery,
        resources_recovered=resources,
        buffs_gained=buffs,
        fatigue_removed=fatigue_removed
    )

# --- STEALTH SYSTEM ---

def calculate_stealth_score(request: StealthRequest) -> StealthResponse:
    """
    Calculates stealth score vs detection.
    """
    d20 = random.randint(1, 20)
    
    # Formula: d20 + Agility + Skill - Armor Penalty + Env Mods
    modifier = request.agility_score + request.stealth_skill_rank - request.armor_penalty + request.environmental_modifiers
    total = d20 + modifier
    
    # Calculate Detection DC based on difficulty tier
    # Trivial: 5, Easy: 10, Medium: 15, Hard: 20, Extreme: 25
    dc_map = {
        "trivial": 5,
        "easy": 10,
        "medium": 15,
        "hard": 20,
        "extreme": 25
    }
    base_dc = dc_map.get(request.difficulty_tier.lower(), 15)
    
    # Note: Environmental modifiers in the request apply to the STEALTH ROLL (user bonus).
    # If we wanted environment to affect DC (detection difficulty), we would adjust base_dc.
    # For now, we assume 'environmental_modifiers' covers the net advantage.
    
    return StealthResponse(
        stealth_score=total,
        detection_dc=base_dc
    )

# --- MOVEMENT SYSTEM ---

def calculate_movement_stats(
    might: int, reflexes: int, awareness: int, fortitude: int
) -> Dict[str, int]:
    """
    Calculates base movement speed and terrain modifiers.
    User Rule: "movement stat based on might reflexes awarness and fortitude"
    """
    # Base Speed
    # Example: Average of stats * factor
    base_speed = (might + reflexes + awareness + fortitude) // 4
    
    # Minimum speed 20ft?
    speed_ft = 20 + (base_speed * 5)
    
    return {
        "base_speed_ft": speed_ft,
        "difficult_terrain_cost": 2, # Standard 2x cost
        "climb_speed": speed_ft // 2,
        "swim_speed": speed_ft // 2
    }

def calculate_operation_stat(
    vitality: int, intuition: int, charm: int, knowledge: int
) -> int:
    """
    Calculates Operation Stat for using gear/tech.
    User Rule: "vitality intuition charm and knowledge determines your operation stat"
    """
    return (vitality + intuition + charm + knowledge) // 4

def calculate_weight_capacity(
    endurance: int, logic: int, finesse: int, willpower: int
) -> float:
    """
    Calculates Weight Capacity.
    User Rule: "whieght capacity based on , endurrence , logic, finesse, and willpower"
    """
    # Example: Sum * 10 lbs
    return (endurance + logic + finesse + willpower) * 5.0
