# AI-TTRPG/monolith/modules/rules_pkg/talent_logic.py
from typing import Dict, List, Any, Optional
import logging
import json
import os
from . import data_loader
from .models_inventory import PassiveModifier

logger = logging.getLogger("monolith.rules.talent_logic")

# Load talent tier configuration
TALENT_TIER_CONFIG = {}
_config_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "talent_tiers.json")
if os.path.exists(_config_path):
    try:
        with open(_config_path, 'r') as f:
            TALENT_TIER_CONFIG = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load talent_tiers.json: {e}")
        TALENT_TIER_CONFIG = {"tier_requirements": {}}
else:
    logger.warning(f"talent_tiers.json not found at {_config_path}, using empty config")
    TALENT_TIER_CONFIG = {"tier_requirements": {}}

def calculate_talent_bonuses(
    character_context: Dict[str, Any],
    action_type: str,
    tags: Optional[List[str]] = None
) -> Dict[str, int]:
    """
    Calculates the total bonuses from a character's active talents for a specific action.

    Args:
        character_context: Full character context including 'talents' (list of names or dicts).
        action_type: 'attack_roll', 'defense_roll', 'damage', 'skill_check', 'initiative'.
        tags: List of tags (e.g. 'Sword', 'Melee', 'Might').
    """
    bonuses = {
        "attack_roll_bonus": 0,
        "defense_roll_bonus": 0,
        "damage_bonus": 0,
        "skill_check_bonus": 0,
        "stat_check_bonus": 0,
        "initiative_bonus": 0
    }

    tags = tags or []
    active_talents = character_context.get("talents", [])

    all_talents_data = data_loader.TALENT_DATA
    if not all_talents_data:
        return bonuses

    # Convert active talents list to a Set of names for fast lookup
    character_talent_names = set()
    for t in active_talents:
        if isinstance(t, dict):
            character_talent_names.add(t.get("name"))
        elif isinstance(t, str):
            character_talent_names.add(t)

    found_modifiers = []

    # Helper to extract modifiers from a generic talent definition
    def extract_mods_if_active(talent_def):
        # Check if talent definition name matches one of character's active talents
        t_name = talent_def.get("talent_name") or talent_def.get("name")
        if t_name in character_talent_names:
            if "modifiers" in talent_def:
                found_modifiers.extend(talent_def["modifiers"])

    # 1. Scan Single Stat Talents
    for t in all_talents_data.get("single_stat_mastery", []):
        extract_mods_if_active(t)

    # 2. Scan Dual Stat Talents
    for t in all_talents_data.get("dual_stat_focus", []):
        extract_mods_if_active(t)

    # 3. Scan Skill Mastery Talents
    # Structure: { "Combat": [ { "skill": "Brawling", "talents": [...] } ] }
    for category_list in all_talents_data.get("single_skill_mastery", {}).values():
        for skill_group in category_list:
            for talent_def in skill_group.get("talents", []):
                extract_mods_if_active(talent_def)

    # Apply valid modifiers to bonuses
    for mod in found_modifiers:
        mod_type = mod.get("type")
        mod_bonus = mod.get("bonus", 0)

        # Filter by Action Type
        # E.g., if we are calculating 'damage', skip modifiers that aren't 'damage_bonus'
        is_applicable = False

        if action_type == "attack_roll":
            if mod_type in ["attack_roll", "contested_check", "attack_bonus"]:
                is_applicable = True
        elif action_type == "defense_roll":
            if mod_type in ["defense_roll", "defense_bonus", "ac_bonus"]:
                is_applicable = True
        elif action_type == "damage":
            if mod_type in ["damage", "damage_bonus"]:
                is_applicable = True
        elif action_type == "initiative":
            if mod_type in ["initiative", "initiative_bonus"]:
                is_applicable = True

        if not is_applicable:
            continue

        # Filter by Tags (if modifier requires specific tags)
        # e.g. Talent requires 'Melee' tag, action has 'Ranged' -> Skip
        required_tags = mod.get("required_tags", [])
        if required_tags:
            # Match IF all required tags are present in the action's tags
            if not all(req in tags for req in required_tags):
                continue

        # Filter by specific Stat/Skill context
        # e.g. Modifier applies only to "Might" checks
        target_stat = mod.get("stat")
        if target_stat and target_stat not in tags:
            continue

        target_skill = mod.get("skill")
        if target_skill and target_skill not in tags:
            continue

        # Accumulate Bonuses
        if action_type == "attack_roll":
            bonuses["attack_roll_bonus"] += mod_bonus
        elif action_type == "defense_roll":
            bonuses["defense_roll_bonus"] += mod_bonus
        elif action_type == "damage":
            bonuses["damage_bonus"] += mod_bonus
        elif action_type == "initiative":
            bonuses["initiative_bonus"] += mod_bonus

    return bonuses


def find_eligible_talents(stats: Dict[str, int], skills: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Finds all talents a character is eligible for based on their stats and skills.
    """
    eligible_talents = []
    all_talents_data = data_loader.TALENT_DATA
    if not all_talents_data:
        logger.warning("Talent data not loaded in talent_logic.")
        return eligible_talents

    # 1. Single Stat Mastery
    for talent in all_talents_data.get("single_stat_mastery", []):
        required_stat = talent.get("stat")
        required_score = talent.get("score")
        if required_stat and required_score and stats.get(required_stat, 0) >= required_score:
            eligible_talents.append(talent)

    # 2. Dual Stat Focus
    for talent in all_talents_data.get("dual_stat_focus", []):
        required_stats = talent.get("stats", [])
        required_score = talent.get("score")
        if len(required_stats) == 2 and required_score:
            stat1_score = stats.get(required_stats[0], 0)
            stat2_score = stats.get(required_stats[1], 0)
            if stat1_score >= required_score and stat2_score >= required_score:
                eligible_talents.append(talent)

    # 3. Single Skill Mastery
    for category_name, skill_groups in all_talents_data.get("single_skill_mastery", {}).items():
        for skill_group in skill_groups:
            skill_name = skill_group.get("skill")
            if skill_name and skill_name in skills:
                skill_rank = skills[skill_name].get("rank", 0)
                for talent in skill_group.get("talents", []):
                    tier = talent.get("tier", "")
                    # Use data-driven tier configuration
                    tier_config = TALENT_TIER_CONFIG.get("tier_requirements", {}).get(tier)
                    if tier_config:
                        required_rank = tier_config.get("required_rank", 0)
                    else:
                        # Fallback for undefined tiers
                        logger.warning(f"Unknown tier '{tier}' for talent, defaulting to rank 0")
                        required_rank = 0

                    if skill_rank >= required_rank:
                        eligible_talents.append(talent)

    return eligible_talents


def get_talent_modifiers(character_talents: List[str]) -> List[PassiveModifier]:
    """
    Aggregates all passive modifiers from a character's learned talents.
    """
    modifiers: List[PassiveModifier] = []
    all_talents_data = data_loader.TALENT_DATA
    if not all_talents_data:
        logger.warning("Talent data not loaded in talent_logic.")
        return modifiers

    # Create a flat map of all talents for easier lookup
    talent_map = {}
    for talent in all_talents_data.get("single_stat_mastery", []):
        talent_map[talent["talent_name"]] = talent
    for talent in all_talents_data.get("dual_stat_focus", []):
        talent_map[talent["talent_name"]] = talent
    for category in all_talents_data.get("single_skill_mastery", {}).values():
        for skill_group in category:
            for talent in skill_group.get("talents", []):
                talent_name = talent.get("talent_name") or talent.get("name")
                if talent_name:
                    talent_map[talent_name] = talent

    for talent_name in character_talents:
        talent_data = talent_map.get(talent_name)
        if not talent_data:
            # logger.warning(f"Could not find data for talent: {talent_name}")
            continue

        for mod in talent_data.get("modifiers", []):
            try:
                # Basic validation
                if "type" in mod and "bonus" in mod:
                    effect_type = "UNKNOWN"
                    if mod["type"] in ["contested_check", "skill_check", "stat_check"]:
                        effect_type = "STAT_MODIFIER"
                    else:
                        effect_type = mod["type"].upper() + "_MODIFIER"

                    modifiers.append(PassiveModifier(
                        effect_type=effect_type,
                        target=mod.get("stat") or mod.get("skill") or "general",
                        value=mod["bonus"],
                        source_id=talent_name
                    ))
            except Exception as e:
                logger.error(f"Failed to parse modifier for talent {talent_name}: {mod}. Error: {e}")

    return modifiers
