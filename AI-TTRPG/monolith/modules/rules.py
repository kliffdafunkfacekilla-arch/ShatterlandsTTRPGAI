# AI-TTRPG/monolith/modules/rules.py
"""
Fully self-contained Rules Engine module for the monolith.

This module loads all game data from its internal 'rules_pkg/data/'
directory at startup and provides async functions that mirror the
original rules_engine HTTP API, allowing other modules like 'story'
to call it directly.
"""
from typing import Any, Dict, List, Optional
import asyncio
import logging

# Import from this module's own internal package
from .rules_pkg import core as rules_core
from .rules_pkg import models as rules_models
from .rules_pkg import data_loader as rules_data_loader
from .rules_pkg import data_validator as rules_data_validator
from .rules_pkg import talent_logic

logger = logging.getLogger("monolith.rules")

# --- Data Loading ---
# Load all rules data into memory ONCE when this module is first imported
try:
    logger.info("[rules] Loading all game data from 'rules_pkg/data/'...")
    _RULES_DATA = rules_data_loader.load_data()

    # Validate the loaded data
    logger.info("[rules] Validating loaded data...")
    is_valid, errors = rules_data_validator.validate_all_rules_data(_RULES_DATA)
    if not is_valid:
        logger.error("[rules] FATAL: Rules data validation failed!")
        for dataset, errs in errors.items():
            for e in errs:
                logger.error(f"  - [{dataset}] {e}")
        # We can choose to raise an exception to halt startup
        # raise Exception("Rules data validation failed. Halting monolith.")
    else:
        logger.info("[rules] All rules data loaded and validated successfully.")
except Exception as e:
    logger.exception(f"[rules] FATAL: Failed to load or validate rules data: {e}")
    # Create an empty dict to prevent crashes on subsequent calls
    _RULES_DATA = {}

# --- Helper to access cached data ---
def _get_data(key: str) -> Any:
    """Safely gets data from the cached rules dictionary."""
    data = _RULES_DATA.get(key)
    if data is None:
        logger.error(f"[rules] Data key '{key}' not found in cached _RULES_DATA.")
        # Return an empty container of the expected type to prevent crashes
        if key.endswith("_list"):
            return []
        if key.endswith("_map") or key.endswith("_data"):
            return {}
    return data

# --- Public API Functions (NOW SYNCHRONOUS) ---
# (Removed _client: Any and async from all function definitions)
def get_npc_generation_params(template_id: str) -> Dict:
    """Looks up the generation parameters for a given NPC template ID."""
    templates = _get_data("npc_templates")
    template_data = templates.get(template_id)
    if not template_data:
        raise Exception(f"NPC template '{template_id}' not found.")
    return template_data

def get_item_template_params(item_id: str) -> Dict:
    """Calls rules_engine to get definition for an item template ID."""
    templates = _get_data("item_templates")
    template_data = templates.get(item_id)
    if not template_data:
        raise Exception(f"Item template '{item_id}' not found.")
    return template_data

def get_loot_table(loot_table_ref: str) -> Dict:
    """Looks up a loot table by its reference ID."""
    loot_tables = _get_data("loot_tables")
    loot_table = loot_tables.get(loot_table_ref)
    if not loot_table:
        raise Exception(f"Loot table '{loot_table_ref}' not found.")
    return loot_table

def generate_npc_template(generation_request: Dict) -> Dict:
    """Generates a full NPC template."""
    req_schema = rules_models.NpcGenerationRequest(**generation_request)
    return rules_core.generate_npc_template_core(
        request=req_schema,
        all_skills_map=_get_data("all_skills"),
        generation_rules=_get_data("generation_rules"),
    )

def roll_initiative(**stats) -> Dict:
    """Rolls initiative based on the provided attribute scores."""
    req_schema = rules_models.InitiativeRequest(**stats)
    result = rules_core.calculate_initiative(req_schema)
    return result.model_dump() # Convert Pydantic model to dict

def roll_contested_attack(attack_params: Dict) -> Dict:
    """Performs a contested attack roll."""
    req_schema = rules_models.ContestedAttackRequest(**attack_params)
    result = rules_core.calculate_contested_attack(req_schema)
    return result.model_dump()

def calculate_damage(damage_params: Dict) -> Dict:
    """Calculates final damage."""
    req_schema = rules_models.DamageRequest(**damage_params)
    result = rules_core.calculate_damage(req_schema)
    return result.model_dump()

def get_weapon_data(category_name: str, weapon_type: str) -> Dict:
    # (This function's logic is unchanged)
    if weapon_type == "melee":
        data = _get_data("melee_weapons").get(category_name)
    elif weapon_type == "ranged":
        data = _get_data("ranged_weapons").get(category_name)
    else:
        raise Exception(f"Unknown weapon type: {weapon_type}")

    if not data:
        logger.warning(f"Weapon category '{category_name}' not found. Defaulting to 'Unarmed/Fist Weapons'.")
        data = _get_data("melee_weapons").get("Unarmed/Fist Weapons")
    if not data: return {"skill": "Unarmed/Fist Weapons", "skill_stat": "Fortitude", "damage": "1d4", "penalty": 0}
    return data

def get_armor_data(category_name: str) -> Dict:
    # (This function's logic is unchanged)
    data = _get_data("armor").get(category_name)
    if not data:
        logger.warning(f"Armor category '{category_name}' not found. Defaulting to 'Natural/Unarmored'.")
        data = _get_data("armor").get("Natural/Unarmored")
    if not data: return {"skill": "Natural/Unarmored", "skill_stat": "Fortitude", "dr": 0}
    return data

def get_all_abilities() -> Dict:
    """Returns the full abilities data structure."""
    return _get_data("ability_data")

def get_all_ability_schools() -> List[str]:
    """Returns a list of all ability school names."""
    return list(_get_data("ability_data").keys())

def get_all_skills() -> Dict:
    """Returns the full skills map."""
    return _get_data("all_skills")

def get_all_stats() -> List[str]:
    """Returns the list of stats."""
    return _get_data("stats_list")

def get_all_talents_data() -> Dict:
    """Returns the full structured talents data."""
    return _get_data("talent_data")

def get_talent_details(talent_name: str) -> Dict:
    """
    Looks up a specific talent by name and returns its details.
    This searches through all talent categories.
    """
    all_data = _get_data("talent_data")
    if not all_data:
        return {}

    # Search Single Stat Mastery
    for t in all_data.get("single_stat_mastery", []):
        if t.get("talent_name") == talent_name:
            return t

    # Search Dual Stat Focus
    for t in all_data.get("dual_stat_focus", []):
        if t.get("talent_name") == talent_name:
            return t

    # Search Skill Mastery (Nested)
    skill_mastery = all_data.get("single_skill_mastery", {})
    for category, skills in skill_mastery.items():
        if isinstance(skills, list):
            for skill_entry in skills:
                for t in skill_entry.get("talents", []):
                    if t.get("talent_name") == talent_name:
                        return t

    return {}

def get_ability_school(school_name: str) -> Dict:
    """Looks up a single ability school."""
    school = _get_data("ability_data").get(school_name)
    if not school:
        raise Exception(f"Ability school '{school_name}' not found.")
    return {
        "school": school_name,
        "resource_pool": school.get("resource_pool", school.get("resource")),
        "associated_stat": school.get("associated_stat", "Unknown"),
        "tiers": school.get("branches", [])
    }

# (get_origin_choices, get_childhood_choices, etc. are all now sync)
def get_origin_choices() -> List[Dict]:
    return _get_data("origin_choices")

def get_childhood_choices() -> List[Dict]:
    return _get_data("childhood_choices")

def get_coming_of_age_choices() -> List[Dict]:
    return _get_data("coming_of_age_choices")

def get_training_choices() -> List[Dict]:
    return _get_data("training_choices")

def get_devotion_choices() -> List[Dict]:
    return _get_data("devotion_choices")

def find_eligible_talents_api(payload: Dict) -> List[Dict]:
    """API-compatible wrapper for finding talents."""
    stats = payload.get("stats", {})
    skills = payload.get("skills", {})
    talents = rules_core.find_eligible_talents(
        stats_in=stats,
        skills_in=skills,
        talent_data=_get_data("talent_data"),
        stats_list=_get_data("stats_list"),
        all_skills_map=_get_data("all_skills")
    )
    return [t.model_dump() for t in talents]

def get_status_effect_data(status_name: str) -> Dict:
    data = _get_data("status_effects").get(status_name)
    if not data:
        raise Exception(f"Status effect '{status_name}' not found.")
    return data

def get_all_status_effects() -> Dict:
    """Returns the full status effects data map."""
    return _get_data("status_effects")

def calculate_base_vitals_api(payload: Dict) -> Dict:
    """API-compatible wrapper for calculating vitals."""
    req_schema = rules_models.BaseVitalsRequest(**payload)
    result = rules_core.calculate_base_vitals(req_schema.stats)
    return result.model_dump()

def calculate_talent_bonuses(character_context: Dict, action_type: str, tags: List[str] = None) -> Dict[str, int]:
    """Calculates bonuses from talents using the new PassiveModifier system."""
    tags = tags or []
    active_talents_names = character_context.get("talents", [])
    
    # Hydrate TalentInfo objects
    hydrated_talents = []
    for t_name in active_talents_names:
        if isinstance(t_name, str):
            t_data = get_talent_details(t_name)
            if t_data:
                # Convert to TalentInfo
                hydrated_talents.append(
                    rules_models.TalentInfo(
                        name=t_data.get("talent_name", t_name),
                        source="Hydrated",
                        effect=t_data.get("effect", ""),
                        modifiers=[rules_models.PassiveModifier(**m) for m in t_data.get("modifiers", [])]
                    )
                )
        elif isinstance(t_name, dict):
             # Already a dict (maybe from find_eligible_talents_api?)
             # If it has modifiers, use them.
             hydrated_talents.append(
                rules_models.TalentInfo(
                    name=t_name.get("name", "Unknown"),
                    source=t_name.get("source", ""),
                    effect=t_name.get("effect", ""),
                    modifiers=[rules_models.PassiveModifier(**m) for m in t_name.get("modifiers", [])]
                )
             )

    # Apply Modifiers
    # We pass empty stats/skills because we are just aggregating bonuses here, 
    # not checking prerequisites (which are assumed met if talent is active).
    # However, some conditional modifiers might need stats/skills. 
    # For now, we assume static bonuses.
    aggregated = rules_core.apply_passive_modifiers({}, {}, hydrated_talents)
    
    bonuses = {
        "attack_roll_bonus": 0,
        "defense_roll_bonus": 0,
        "damage_bonus": 0,
        "skill_check_bonus": 0,
        "stat_check_bonus": 0,
        "initiative_bonus": 0
    }

    # Map aggregated results to requested action
    if action_type == "attack_roll":
        # Check for generic attack bonuses (if any)
        # Check for Contested Check bonuses matching the stat
        for tag in tags:
            key = f"contested_check:{tag}"
            if key in aggregated["roll_bonuses"]:
                bonuses["attack_roll_bonus"] += aggregated["roll_bonuses"][key]
        
        # Check for Skill bonuses
        # We need to know which skill is being used. It's not explicitly passed as "skill:Name" in tags usually.
        # But tags might contain the skill name if it's a weapon category?
        # Actually, weapon categories ARE skills (e.g. "Swords", "Bows").
        for tag in tags:
            if tag in aggregated["skill_bonuses"]:
                bonuses["attack_roll_bonus"] += aggregated["skill_bonuses"][tag]

    elif action_type == "defense_roll":
        for tag in tags:
            key = f"contested_check:{tag}" # e.g. contested_check:Reflexes
            if key in aggregated["roll_bonuses"]:
                bonuses["defense_roll_bonus"] += aggregated["roll_bonuses"][key]
        
        # Defense skills (e.g. Light Armor, Heavy Armor)
        for tag in tags:
            if tag in aggregated["skill_bonuses"]:
                bonuses["defense_roll_bonus"] += aggregated["skill_bonuses"][tag]

    elif action_type == "damage_roll":
        bonuses["damage_bonus"] += aggregated["damage_bonuses"]
    
    return bonuses

def register(orchestrator) -> None:
    logger.info("[rules] module registered (self-contained logic)")
