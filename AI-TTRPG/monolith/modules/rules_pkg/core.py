# core.py
import random
import math
from typing import Dict, List, Optional, Any

# Use relative import for models within the same package
from . import models
from .models import RollResult, TalentInfo, FeatureStatsResponse


def calculate_modifier(score: int) -> int:
    """
    Calculates the standard attribute modifier from a score.

    Formula: floor((Score - 10) / 2).

    Args:
        score (int): The raw attribute score (e.g., 10, 15, 8).

    Returns:
        int: The calculated modifier (e.g., 0, +2, -1).
    """
    if not isinstance(score, int):
        # Basic type check for safety
        print(
            f"Warning: calculate_modifier received non-integer score: {score}. Using 10."
        )
        score = 10
    return math.floor((score - 10) / 2)


def generate_npc_template_core(
    request: models.NpcGenerationRequest,
    all_skills_map: Dict[str, Dict[str, str]],
    generation_rules: Dict[str, Any]
) -> Dict: # Returns a dict matching NpcTemplateResponse structure
    """
    Generates a full NPC template based on high-level request parameters.

    This function combines base stats from the kingdom (species), style modifiers,
    HP scaling, suggested abilities, and skill ranks to create a complete NPC stat block.

    Args:
        request (models.NpcGenerationRequest): The parameters guiding the generation (kingdom, style, difficulty, etc.).
        all_skills_map (Dict[str, Dict[str, str]]): A mapping of all available skills.
        generation_rules (Dict[str, Any]): The ruleset defining base stats, modifiers, and scaling factors.

    Returns:
        Dict: A dictionary structure matching `NpcTemplateResponse`, containing stats, skills, abilities, and derived values.
    """
    # 1. Determine Base Stats
    kingdom_stats = generation_rules.get("base_stats_by_kingdom", {})
    base_stats = kingdom_stats.get(request.kingdom.lower())

    if base_stats is None:
        base_stats = kingdom_stats.get("mammal", {})

    final_stats = base_stats.copy()

    # 2. Apply Style Modifiers
    offense_mods = generation_rules.get("stat_modifiers_by_style", {}).get("offense", {}).get(request.offense_style.lower(), {})
    defense_mods = generation_rules.get("stat_modifiers_by_style", {}).get("defense", {}).get(request.defense_style.lower(), {})

    all_mods = {**offense_mods, **defense_mods}

    for stat, mod_str in all_mods.items():
        if stat in final_stats:
            try:
                modifier = int(mod_str.replace('+', ''))
                final_stats[stat] += modifier
                final_stats[stat] = max(1, final_stats[stat])
            except ValueError:
                print(f"Warning: Invalid modifier format '{mod_str}' for stat '{stat}'")

    # 3. Calculate HP
    base_hp = final_stats.get("Endurance", 10) + final_stats.get("Vitality", 10) * 2
    hp_multiplier = generation_rules.get("hp_scaling_by_difficulty", {}).get(request.difficulty.lower(), 1.0)
    max_hp = int(base_hp * hp_multiplier)

    # 4. Determine Abilities
    abilities = []
    if request.ability_focus and request.ability_focus in generation_rules.get("ability_suggestions", {}):
        suggested = generation_rules["ability_suggestions"][request.ability_focus]
        if suggested:
            abilities.append(suggested[0])

    # 5. Determine Skills
    skills = {skill_name: 0 for skill_name in all_skills_map.keys()}

    skill_rules = generation_rules.get("skills_by_style_and_difficulty", {})
    offense_skills_for_diff = skill_rules.get("offense", {}).get(request.offense_style.lower(), {}).get(request.difficulty.lower(), [])
    defense_skills_for_diff = skill_rules.get("defense", {}).get(request.defense_style.lower(), {}).get(request.difficulty.lower(), [])
    skill_rank_value = skill_rules.get("skill_ranks", {}).get(request.difficulty.lower(), 1)
    skills_to_rank = set(offense_skills_for_diff + defense_skills_for_diff)

    for skill_name in skills_to_rank:
        if skill_name in skills:
            skills[skill_name] = skill_rank_value

    # 6. ID, Name, Description, Behavior Tags
    generated_id = f"procgen_{request.biome or 'unk'}_{request.kingdom}_{request.offense_style}_{request.difficulty}_{random.randint(100,999)}"
    name = request.custom_name or f"{request.difficulty.capitalize()} {request.kingdom.capitalize()} {request.offense_style.replace('_',' ').title()}"
    description = f"A {request.difficulty} {request.kingdom} exhibiting a {request.offense_style} style and {request.defense_style} defense."
    if request.biome:
        description += f" Adapted to the {request.biome}."

    behavior_tags = generation_rules.get("behavior_map",{}).get(request.behavior.lower(), [])

    # 7. Build Response
    return {"generated_id": generated_id, "name": name, "description": description, "stats": final_stats, "skills": skills, "abilities": abilities, "max_hp": max_hp, "behavior_tags": behavior_tags, "loot_table_ref": f"{request.kingdom}_{request.difficulty}_loot"}


def calculate_skill_mt_bonus(rank: int) -> int:
    """
    Calculates the Mastery Tier (MT) bonus derived from a skill rank.

    Assumption: Bonus = floor(Rank / 3).
    Example:
        - Rank 0-2 -> +0
        - Rank 3-5 -> +1
        - Rank 6-8 -> +2

    Args:
        rank (int): The skill rank.

    Returns:
        int: The calculated mastery tier bonus.
    """
    if not isinstance(rank, int) or rank < 0:
        print(
            f"Warning: calculate_skill_mt_bonus received invalid rank: {rank}. Using 0."
        )
        rank = 0
    return math.floor(rank / 3)


def calculate_xp_for_level(level: int) -> int:
    """
    Calculates the total experience points required to reach the NEXT level.

    Formula: Current Level * 1000.

    Args:
        level (int): The character's current level.

    Returns:
        int: The total XP required for the next level.
    """
    if level < 1: return 1000
    return level * 1000


# --- Dice Rolling ---


def _roll_d20() -> int:
    return random.randint(1, 20)


def _roll_d6() -> int:
    return random.randint(1, 6)


def parse_dice_string(dice_str: str) -> (int, int):
    """
    Parses a standard dice notation string (e.g., '2d6') into its components.

    Args:
        dice_str (str): The dice string to parse. Accepts '0' for no roll.

    Returns:
        (int, int): A tuple containing (number_of_dice, sides_per_die).

    Raises:
        ValueError: If the string format is invalid or components are non-integer.
    """
    if dice_str == "0":
        return 0, 0
    if "d" not in dice_str:
        raise ValueError(f"Invalid dice string format: '{dice_str}'")

    parts = dice_str.lower().split("d")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        raise ValueError(f"Invalid dice string format: '{dice_str}'")

    return int(parts[0]), int(parts[1])


def _roll_dice(num_dice: int, sides: int) -> int:
    """
    Rolls a specified number of dice with a given number of sides.

    Args:
        num_dice (int): The number of dice to roll.
        sides (int): The number of sides on each die.

    Returns:
        int: The sum of the rolled results.
    """
    if num_dice == 0:
        return 0
    return sum(random.randint(1, sides) for _ in range(num_dice))


def calculate_contested_attack(
    attack_data: models.ContestedAttackRequest,
) -> models.ContestedAttackResponse:
    """
    Performs a contested attack roll logic (Attacker vs Defender).

    This function calculates the total rolls for both the attacker and defender,
    incorporating stats, skill ranks, and all provided pre-aggregated modifiers.
    It determines the outcome (hit, miss, crit, etc.) and the margin of success.

    Args:
        attack_data (models.ContestedAttackRequest): The full parameters for the attack resolution.

    Returns:
        models.ContestedAttackResponse: The detailed results of the contest.
    """

    # NOTE: We no longer need to look up weapon/armor data here,
    # as the necessary stats (Stat Scores, Skill Ranks, Weapon Penalty)
    # and aggregated bonuses/penalties are provided directly in attack_data.

    # --- Roll Dice ---
    attacker_roll = _roll_d20()
    defender_roll = _roll_d20()

    # --- Calculate Attacker Total ---
    attacker_stat_mod = calculate_modifier(attack_data.attacker_attacking_stat_score)
    attacker_skill_bonus = calculate_skill_mt_bonus(
        attack_data.attacker_skill_rank
    )  # Still uses +1 per rank
    attacker_total_modifier = (
        attacker_stat_mod
        + attacker_skill_bonus
        + attack_data.attacker_attack_roll_bonus
        - attack_data.attacker_attack_roll_penalty  # Use new specific fields
    )
    attacker_final_total = attacker_roll + attacker_total_modifier

    # --- Calculate Defender Total ---
    defender_stat_mod = calculate_modifier(attack_data.defender_armor_stat_score)
    defender_skill_bonus = calculate_skill_mt_bonus(
        attack_data.defender_armor_skill_rank
    )  # Still uses +1 per rank
    # Weapon penalty still comes from request (story_engine looks it up)
    defender_total_modifier = (
        defender_stat_mod
        + defender_skill_bonus
        - attack_data.defender_weapon_penalty
        + attack_data.defender_defense_roll_bonus
        - attack_data.defender_defense_roll_penalty  # Use new specific fields
    )
    defender_final_total = defender_roll + defender_total_modifier

    # --- Determine Outcome (Logic remains the same) ---
    margin = attacker_final_total - defender_final_total
    outcome = "miss"
    if attacker_roll == 1:
        outcome = "critical_fumble"
    elif attacker_roll == 20:
        outcome = "critical_hit"
    elif margin >= 5:
        outcome = "solid_hit"
    elif margin >= 0:
        outcome = "hit"

    # --- Return Response (Remains the same structure) ---
    return models.ContestedAttackResponse(
        attacker_roll=attacker_roll,
        attacker_stat_mod=attacker_stat_mod,
        attacker_skill_bonus=attacker_skill_bonus,
        attacker_total_modifier=attacker_total_modifier,
        attacker_final_total=attacker_final_total,
        defender_roll=defender_roll,
        defender_stat_mod=defender_stat_mod,
        defender_skill_bonus=defender_skill_bonus,
        defender_total_modifier=defender_total_modifier,
        defender_final_total=defender_final_total,
        outcome=outcome,
        margin=margin,
    )


def calculate_damage(damage_data: models.DamageRequest) -> models.DamageResponse:
    """
    Calculates the final damage of an attack.

    This function handles dice rolling, stat bonuses, misc damage bonuses/penalties,
    and the application of the defender's Damage Reduction (DR).

    Args:
        damage_data (models.DamageRequest): The full parameters for damage calculation.

    Returns:
        models.DamageResponse: The detailed breakdown of the damage calculation.
    """

    # NOTE: We no longer need to look up weapon/armor data here,
    # as base dice, relevant stat, damage bonus, DR modifier, and base DR
    # are provided directly in damage_data.

    # --- 1. Parse Dice String & Roll ---
    try:
        # Handle multi-hit like '(x2)'? Assume caller handles this or provides combined dice.
        # Handle AoE? Assume single target damage here.
        # We just parse the dice string provided.
        num_dice, die_type = parse_dice_string(damage_data.base_damage_dice)
    except ValueError as e:
        print(f"Error parsing dice string in core calculate_damage: {e}")
        # Return zero damage
        return models.DamageResponse(
            damage_roll_details=[],
            base_roll_total=0,
            stat_bonus=0,
            misc_bonus=0,
            subtotal_damage=0,
            damage_reduction_applied=0,
            final_damage=0,
        )

    rolls, roll_total = _roll_dice(num_dice, die_type)

    # --- 2. Calculate Stat Bonus ---
    stat_bonus = calculate_modifier(damage_data.relevant_stat_score)

    # --- 3. Calculate Subtotal ---
    subtotal = (
        roll_total
        + stat_bonus
        + damage_data.attacker_damage_bonus
        - damage_data.attacker_damage_penalty  # Use new specific fields
    )

    # --- 4. Apply Modified DR ---
    # Calculate effective DR after applying attacker's modifier (e.g., from Great Weapons)
    effective_dr = max(
        0, damage_data.defender_base_dr - damage_data.attacker_dr_modifier
    )

    dr_applied = min(subtotal, effective_dr)  # DR applied cannot exceed subtotal
    final_damage = max(0, subtotal - effective_dr)  # Final damage is at least 0

    # --- 5. Return Response (Remains the same structure) ---
    return models.DamageResponse(
        damage_roll_details=rolls,
        base_roll_total=roll_total,
        stat_bonus=stat_bonus,
        misc_bonus=damage_data.attacker_damage_bonus
        - damage_data.attacker_damage_penalty,  # Reflect net bonus in response
        subtotal_damage=subtotal,
        damage_reduction_applied=dr_applied,
        final_damage=final_damage,
    )


def calculate_initiative(stats: models.InitiativeRequest) -> models.InitiativeResponse:
    """
    Calculates initiative based on the Fulcrum rules:
    d20 + B Mod + D Mod + F Mod + H Mod + J Mod + L Mod
    """
    roll = _roll_d20()

    # Calculate modifiers using the helper function
    mod_b = calculate_modifier(stats.endurance)
    mod_d = calculate_modifier(stats.reflexes) # CHANGED from stats.agility
    mod_f = calculate_modifier(stats.fortitude)
    mod_h = calculate_modifier(stats.logic)
    mod_j = calculate_modifier(stats.intuition)
    mod_l = calculate_modifier(stats.willpower)

    modifier_details = {
        "Endurance (B) Mod": mod_b,
        "Reflexes (D) Mod": mod_d, # CHANGED from Agility
        "Fortitude (F) Mod": mod_f,
        "Logic (H) Mod": mod_h,
        "Intuition (J) Mod": mod_j,
        "Willpower (L) Mod": mod_l,
    }

    total_modifier = sum(modifier_details.values())
    total_initiative = roll + total_modifier

    return models.InitiativeResponse(
        roll_value=roll,
        modifier_details=modifier_details,
        total_initiative=total_initiative,
    )


# --- Core Validation Logic ---


def calculate_skill_check(stat_mod: int, skill_rank: int, dc: int) -> RollResult:
    """
    Performs a standard d20 skill check.

    Args:
        stat_mod (int): The relevant attribute modifier.
        skill_rank (int): The character's rank in the skill.
        dc (int): The Difficulty Class to beat.

    Returns:
        RollResult: The outcome of the check.
    """
    roll = _roll_d20()
    total = roll + stat_mod + skill_rank
    success = total >= dc
    crit_success = roll == 20
    crit_fail = roll == 1
    sre_triggered = crit_success or crit_fail

    return RollResult(
        roll_value=roll,
        total_value=total,
        dc=dc,
        is_success=success,
        is_critical_success=crit_success,
        is_critical_failure=crit_fail,
        sre_triggered=sre_triggered,
    )


def calculate_ability_check(rank: int, stat_mod: int, tier: int) -> RollResult:
    """
    Performs a d20 Ability check against a DC determined by the ability's Tier.

    DC Tiers:
    - Tier 1-3: DC 12
    - Tier 4-6: DC 14
    - Tier 7-9: DC 16
    - Tier 10+: DC 20

    Args:
        rank (int): The character's rank in the ability school.
        stat_mod (int): The associated attribute modifier.
        tier (int): The tier of the ability being used.

    Returns:
        RollResult: The outcome of the check.
    """
    if tier <= 3:
        dc = 12
    elif tier <= 6:
        dc = 14
    elif tier <= 9:
        dc = 16
    else:
        dc = 20  # Assuming T10 might exist implicitly or have a higher DC

    roll = _roll_d20()
    total = roll + rank + stat_mod
    success = total >= dc
    crit_success = roll == 20
    crit_fail = roll == 1

    return RollResult(
        roll_value=roll,
        total_value=total,
        dc=dc,
        is_success=success,
        is_critical_success=crit_success,
        is_critical_failure=crit_fail,
        sre_triggered=False,
    )


# --- Core Lookup Logic ---


def get_kingdom_feature_stats(
    feature_name: str, feature_map: Dict[str, Any]
) -> FeatureStatsResponse:
    """
    Looks up the statistic modifiers associated with a specific kingdom feature (species trait).

    Args:
        feature_name (str): The name of the feature to look up.
        feature_map (Dict[str, Any]): The loaded map of features and their stats.

    Returns:
        FeatureStatsResponse: The feature name and its modifiers.

    Raises:
        ValueError: If the map is missing or the feature is not found.
    """
    if not feature_map:
        raise ValueError("Feature map not provided or empty.")
    if feature_name not in feature_map:
        raise ValueError(f"Feature '{feature_name}' not found in provided rules map.")
    feature_data = feature_map[feature_name]
    mods_data = feature_data.get("mods", {})
    return FeatureStatsResponse(
        name=feature_data.get("name", feature_name), mods=mods_data
    )


def get_skills_by_category(
    skill_categories_map: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """
    Returns the mapping of skill categories to their list of skills.

    Args:
        skill_categories_map (Dict[str, List[str]]): The loaded skill category map.

    Returns:
        Dict[str, List[str]]: The requested map.

    Raises:
        ValueError: If the map is empty.
    """
    if not skill_categories_map:
        raise ValueError("Skill categories map not provided or empty.")
    return skill_categories_map


def get_skill_for_category(category_name: str, skill_map: Dict[str, str]) -> str:
    """
    Resolves the governing skill for a given equipment or weapon category.

    Args:
        category_name (str): The name of the equipment category (e.g., 'Heavy Blades').
        skill_map (Dict[str, str]): The loaded map linking categories to skills.

    Returns:
        str: The name of the governing skill.

    Raises:
        ValueError: If the category is not found in the map.
    """
    if not skill_map:
        raise ValueError("Skill map not provided or empty.")
    if category_name not in skill_map:
        raise ValueError(f"Category '{category_name}' not found in skill map.")
    return skill_map[category_name]


def get_status_effect(
    status_name: str, status_effects_data: Dict[str, Any]
) -> models.StatusEffectResponse:
    """
    Retrieves the definition and effects for a specific status condition by name.

    Performs a case-insensitive lookup against the provided data.

    Args:
        status_name (str): The name of the status effect (e.g., 'Poisoned').
        status_effects_data (Dict[str, Any]): The loaded status effect data.

    Returns:
        models.StatusEffectResponse: The structured status effect data.

    Raises:
        ValueError: If the status effect is not found.
    """

    status_data = None
    found_key = None
    # Case-insensitive lookup
    for key, value in status_effects_data.items():
        if key.lower() == status_name.lower():
            status_data = value
            found_key = key  # Store the original key casing
            break

    if not status_data:
        raise ValueError(
            f"Status effect '{status_name}' not found in loaded status_effects.json."
        )

    # Construct the response model using data from the found dictionary.
    # Ensure the keys used here (.get("field_name")) exactly match the keys
    # within each status object in your status_effects.json
    try:
        response_data = {
            "name": status_data.get(
                "name", found_key
            ),  # Use defined name or fallback to the key
            "description": status_data.get("description", "No description."),
            "effects": status_data.get("effects", []),
            "type": status_data.get("type", "unknown"),
            "duration_type": status_data.get("duration_type", "condition"),
            "default_duration": status_data.get(
                "default_duration"
            ),  # Will be None if missing
            # Add mappings for any other fields you added to the StatusEffectResponse model
        }
        return models.StatusEffectResponse(**response_data)
    except Exception as e:
        # This might happen if the JSON data doesn't match the Pydantic model
        print(f"Error creating StatusEffectResponse for '{found_key}': {e}")
        raise ValueError(
            f"Data structure mismatch for status '{found_key}'. Check JSON against models.py. Error: {e}"
        )


def get_injury_effects(
    request: models.InjuryLookupRequest, injury_effects_data: Dict[str, Any]
) -> models.InjuryEffectResponse:
    """
    Resolves the effects of a specific injury based on location and severity.

    Args:
        request (models.InjuryLookupRequest): The injury details (location, sub-location, severity).
        injury_effects_data (Dict[str, Any]): The loaded injury data map.

    Returns:
        models.InjuryEffectResponse: The name and effects of the injury.

    Raises:
        ValueError: If the location, sub-location, or severity is invalid.
    """
    location_data = injury_effects_data.get(request.location)
    if not location_data:
        raise ValueError(f"Invalid injury location: '{request.location}'")

    sub_location_data = location_data.get(request.sub_location)
    if not sub_location_data:
        raise ValueError(
            f"Invalid sub-location '{request.sub_location}' for location '{request.location}'"
        )

    severity_data = sub_location_data.get(str(request.severity))
    if not severity_data:
        # This case should ideally not be hit if request model validation is working (ge=1, le=5)
        raise ValueError(
            f"Invalid severity '{request.severity}' for injury at '{request.location} - {request.sub_location}'"
        )

    return models.InjuryEffectResponse(
        severity_name=severity_data.get("name", "Unknown"),
        effects=severity_data.get("effects", []),
    )


def find_eligible_talents(
    stats_in: Dict[str, int],
    skills_in: Dict[str, int],  # {skill_name: rank}
    talent_data: Dict[str, Any],
    stats_list: List[str],
    all_skills_map: Dict[str, Dict[str, str]],
) -> List[TalentInfo]:
    """
    Identifies all talents a character qualifies for based on their stats and skills.

    Checks against Single Stat Mastery, Dual Stat Focus, and Single Skill Mastery prerequisites.

    Args:
        stats_in (Dict[str, int]): Character's stat scores.
        skills_in (Dict[str, int]): Character's skill ranks (mapping skill name to rank).
        talent_data (Dict[str, Any]): The full loaded talent data structure.
        stats_list (List[str]): List of valid stat names.
        all_skills_map (Dict[str, Dict[str, str]]): Master mapping of all skills.

    Returns:
        List[TalentInfo]: A list of talents the character is eligible for.
    """
    unlocked_talents = []

    if not talent_data or not stats_list or not all_skills_map:
        print(
            "Warning: Missing required data (talents, stats list, or skills map) for talent lookup."
        )
        return []

    stats_complete = {stat: stats_in.get(stat, 0) for stat in stats_list}
    skills_complete = skills_in  # Assumes skills_in is {skill_name: rank}

    # --- 1. Check Single Stat Mastery ---
    for talent_group in talent_data.get("single_stat_mastery", []):
        stat_name = talent_group.get("stat")
        if not stat_name:
            continue
        current_stat_score = stats_complete.get(stat_name, 0)
        # Check 'score' field (ensure talents.json uses 'score')
        required_score = talent_group.get("score")
        if required_score is not None and current_stat_score >= required_score:
            unlocked_talents.append(
                TalentInfo(
                    name=talent_group.get("talent_name", "Unknown Talent"),
                    source=f"Stat: {stat_name} {required_score}",
                    effect=talent_group.get("effect", ""),
                        modifiers=[models.PassiveModifier(**m) for m in talent_group.get("modifiers", [])]
                )
            )

    # --- 2. Check Dual Stat Synergy ---
    for talent in talent_data.get("dual_stat_focus", []):
        req_score = talent.get("score", 99)  # Check 'score' field
        stats_pair = talent.get("stats", [])  # FIXED: Changed 'paired_stats' to 'stats' to match JSON
        if len(stats_pair) == 2:
            stat1, stat2 = stats_pair
            if (
                stats_complete.get(stat1, 0) >= req_score
                and stats_complete.get(stat2, 0) >= req_score
            ):
                unlocked_talents.append(
                    TalentInfo(
                        name=talent.get(
                            "talent_name", "Unknown Talent"
                        ),  # Check 'talent_name' field
                        source=f"Dual Stat: {stat1} & {stat2} {req_score}",
                        effect=talent.get("effect", ""),
                            modifiers=[models.PassiveModifier(**m) for m in talent.get("modifiers", [])]
                    )
                )

    # --- 3. Check Skill Mastery ---
    for category_key, category_list in talent_data.get(
        "single_skill_mastery", {}
    ).items():
        if isinstance(category_list, list):
            for skill_group in category_list:
                skill_name = skill_group.get("skill")
                if (
                    skill_name and skill_name in all_skills_map
                ):  # Check against provided map
                    current_skill_rank = skills_complete.get(skill_name, 0)
                    for talent in skill_group.get("talents", []):
                        # Check both 'tier' and 'prerequisite_mt' keys for flexibility
                        tier_name = talent.get("tier", talent.get("prerequisite_mt"))
                        req_rank = 99
                        if tier_name and tier_name.startswith("MT"):
                            try:
                                req_rank = int(tier_name.replace("MT", ""))
                            except ValueError:
                                pass

                        if current_skill_rank >= req_rank:
                            unlocked_talents.append(
                                TalentInfo(
                                    name=talent.get(
                                        "talent_name", "Unknown Talent"
                                    ),  # Check 'talent_name' field
                                    source=f"Skill: {skill_name} ({tier_name})",
                                    effect=talent.get("effect", ""),
                                    modifiers=[models.PassiveModifier(**m) for m in talent.get("modifiers", [])]
                                )
                            )
                elif skill_name:
                    print(
                        f"Warning: Skill '{skill_name}' from talent data not found in master skill map."
                    )

    return unlocked_talents


def apply_passive_modifiers(
    stats: Dict[str, int],
    skills: Dict[str, int],
    talents: List[TalentInfo],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Aggregates modifiers from talents and applies them to stats/skills/rolls.
    Returns a dictionary of aggregated bonuses.
    """
    aggregated = {
        "stat_bonuses": {},
        "skill_bonuses": {},
        "roll_bonuses": {}, # e.g. "contested_check:Might", "save_roll:Poison"
        "action_cost_reductions": {},
        "rerolls": [],
        "resource_restores": [],
        "damage_bonuses": 0,
        "dr_bonuses": 0,
        "resource_max_bonuses": {},
        "initiative_bonus": 0,
        "defense_bonuses": {},
        "immunities": [],
        "ignored_penalties": [],
        "damage_reduction": {}
    }
    
    for talent in talents:
        for mod in talent.modifiers:
            # TODO: Check conditions here if context is provided
            
            # Convert Pydantic model values to local variables for cleaner logic
            # PassiveModifier uses: effect_type, target, value
            # We map these to the logic previously used with dict keys

            m_type = mod.effect_type
            m_target = mod.target
            m_value = mod.value

            if m_type == "stat_bonus" and m_target:
                aggregated["stat_bonuses"][m_target] = aggregated["stat_bonuses"].get(m_target, 0) + m_value
            elif m_type == "skill_bonus" and m_target:
                aggregated["skill_bonuses"][m_target] = aggregated["skill_bonuses"].get(m_target, 0) + m_value
            elif m_type == "contested_check" and m_target:
                key = f"contested_check:{m_target}"
                aggregated["roll_bonuses"][key] = aggregated["roll_bonuses"].get(key, 0) + m_value
            elif m_type == "save_roll" and m_target:
                key = f"save_roll:{m_target}"
                aggregated["roll_bonuses"][key] = aggregated["roll_bonuses"].get(key, 0) + m_value
            elif m_type == "damage_bonus":
                aggregated["damage_bonuses"] += m_value
            elif m_type == "dr_bonus":
                aggregated["dr_bonuses"] += m_value
            elif m_type == "resource_max" and m_target:
                 res_name = m_target
                 if res_name:
                    aggregated["resource_max_bonuses"][res_name] = aggregated["resource_max_bonuses"].get(res_name, 0) + m_value
            elif m_type == "initiative":
                aggregated["initiative_bonus"] += m_value
            elif m_type == "skill_check" and m_target:
                aggregated["skill_bonuses"][m_target] = aggregated["skill_bonuses"].get(m_target, 0) + m_value
            elif m_type == "action_cost_reduction":
                key = m_target or "general"
                aggregated["action_cost_reductions"][key] = mod # Store full object for complex data
            elif m_type == "reroll_on_failure":
                aggregated["rerolls"].append(mod)
            elif m_type == "resource_restore_on_check" or m_type == "resource_restore_on_trigger":
                aggregated["resource_restores"].append(mod)
            elif m_type == "damage_reduction":
                 # Assuming this is a flat DR bonus if 'value' is non-zero/present
                 if m_value:
                    aggregated["dr_bonuses"] += m_value
                 else:
                    aggregated["damage_reduction"][m_target or "general"] = mod
            elif m_type == "ignore_status_penalty" or m_type == "ignore_terrain_penalty":
                aggregated["ignored_penalties"].append(mod)
            elif m_type == "initiative_advantage":
                aggregated["roll_bonuses"]["initiative_advantage"] = True
            elif m_type == "composure_loss_reduction":
                aggregated["defense_bonuses"]["composure_dr"] = aggregated["defense_bonuses"].get("composure_dr", 0) + m_value
            elif m_type == "unlock_action":
                pass
            elif m_type == "rule_override" or m_type == "defense_override":
                pass
            elif m_type == "derived_stat":
                pass 
            
    return aggregated


def calculate_base_vitals(request: models.BaseVitalsRequest) -> models.BaseVitalsResponse:
    """
    Calculates Max HP and Composure based on the specific 6-stat split.
    Scale: Base + Level + Sum(Stat Mods).
    """
    stats = request.stats
    level = request.level

    # 1. Define Stat Groups
    hp_stats = ["Endurance", "Vitality", "Reflexes", "Logic", "Awareness", "Willpower"]
    composure_stats = ["Might", "Finesse", "Fortitude", "Knowledge", "Intuition", "Charm"]

    # 2. Calculate HP
    # Formula: 10 (Base) + Level + Sum(Modifiers of HP Stats)
    hp_mod_sum = sum(calculate_modifier(stats.get(s, 10)) for s in hp_stats)
    max_hp = 10 + level + hp_mod_sum
    max_hp = max(5, max_hp) # Minimum floor

    # 3. Calculate Composure
    # Formula: 10 (Base) + Level + Sum(Modifiers of Composure Stats)
    comp_mod_sum = sum(calculate_modifier(stats.get(s, 10)) for s in composure_stats)
    max_composure = 10 + level + comp_mod_sum
    max_composure = max(5, max_composure)

    # 4. Calculate Resource Pools (Dual-Stat Modifiers)
    # Formula: 5 (Base) + (Stat1 Modifier + Stat2 Modifier)
    chi_mod = calculate_modifier(stats.get("Finesse", 10)) + calculate_modifier(stats.get("Reflexes", 10))
    stamina_mod = calculate_modifier(stats.get("Endurance", 10)) + calculate_modifier(stats.get("Vitality", 10))
    guile_mod = calculate_modifier(stats.get("Finesse", 10)) + calculate_modifier(stats.get("Knowledge", 10))
    presence_mod = calculate_modifier(stats.get("Might", 10)) + calculate_modifier(stats.get("Charm", 10))
    tactics_mod = calculate_modifier(stats.get("Awareness", 10)) + calculate_modifier(stats.get("Logic", 10))
    instinct_mod = calculate_modifier(stats.get("Intuition", 10)) + calculate_modifier(stats.get("Willpower", 10))

    resources = {
        "Chi": {"max": 5 + chi_mod},
        "Stamina": {"max": 5 + stamina_mod},
        "Guile": {"max": 5 + guile_mod},
        "Presence": {"max": 5 + presence_mod},
        "Tactics": {"max": 5 + tactics_mod},
        "Instinct": {"max": 5 + instinct_mod},
    }

    # Set current to max for initial creation, ensuring a minimum of 1
    for pool in resources.values():
        if pool["max"] < 1:
            pool["max"] = 1
        pool["current"] = pool["max"]

    return models.BaseVitalsResponse(
        max_hp=max_hp,
        max_composure=max_composure,
        resources=resources
    )


def validate_ability_unlock(request: models.AbilityPurchaseRequest) -> models.AbilityPurchaseResponse:
    """
    The Gatekeeper Logic: Checks Economy, Duplicates, and Vertical Hierarchy.
    """
    target = request.target_ability
    target_id = target.to_id()

    # 1. Economy Check
    if request.available_ap < 1:
        return models.AbilityPurchaseResponse(
            success=False,
            message="Insufficient Funds (Need 1 AP)",
            remaining_ap=request.available_ap
        )

    # 2. Duplicate Check
    if target_id in request.current_unlocks:
        return models.AbilityPurchaseResponse(
            success=False,
            message="Ability Node already unlocked",
            remaining_ap=request.available_ap
        )

    # 3. Hierarchy Check (Vertical Ladder)
    if target.tier == 1:
        # Tier 1 is the root, always allowed if school is valid (assumed valid here)
        pass
    else:
        # Recursive Check: Must own n-1
        required_id = target.get_prerequisite_id()
        if required_id not in request.current_unlocks:
            return models.AbilityPurchaseResponse(
                success=False,
                message=f"Prerequisite missing: Must own {required_id} to unlock Tier {target.tier}",
                remaining_ap=request.available_ap
            )

    # Success
    return models.AbilityPurchaseResponse(
        success=True,
        message=f"Unlocked {target_id}",
        remaining_ap=request.available_ap - 1,
        new_unlock=target_id
    )
