# AI-TTRPG/monolith/modules/rules.py
"""
Fully self-contained Rules Engine module for the monolith.

This module loads all game data from its internal 'rules_pkg/data/'
directory at startup and provides functions that mirror the
original rules_engine API.
"""
from typing import Any, Dict, List, Optional
import logging

# Import from this module's own internal package
from .rules_pkg import core as rules_core
# Alias 'core' for user code compatibility
from .rules_pkg import core as core
from .rules_pkg import models as rules_models
from .rules_pkg import models as models # Alias for user code
from .rules_pkg import data_loader
from .rules_pkg import data_validator as rules_data_validator
from .rules_pkg import talent_logic

logger = logging.getLogger("monolith.rules")

# --- Data Loading ---
try:
    logger.info("[rules] Loading all game data from 'rules_pkg/data/'...")
    _RULES_DATA = data_loader.load_data()

    # Validate the loaded data
    is_valid, errors = rules_data_validator.validate_all_rules_data(_RULES_DATA)
    if not is_valid:
        logger.error("[rules] FATAL: Rules data validation failed!")
        for dataset, errs in errors.items():
            for e in errs:
                logger.error(f"  - [{dataset}] {e}")
    else:
        logger.info("[rules] All rules data loaded and validated successfully.")
except Exception as e:
    logger.exception(f"[rules] FATAL: Failed to load or validate rules data: {e}")
    _RULES_DATA = {}

# --- Helper to access cached data ---
def _get_data(key: str) -> Any:
    """Safely gets data from the cached rules dictionary."""
    data = _RULES_DATA.get(key)
    if data is None:
        logger.error(f"[rules] Data key '{key}' not found in cached _RULES_DATA.")
        if key.endswith("_list"): return []
        if key.endswith("_map") or key.endswith("_data"): return {}
    return data

# =============================================================================
# --- 1. DATA ACCESSORS (The Menu) - NEW ---
# =============================================================================

def get_all_kingdoms() -> List[str]:
    """Returns keys from F1 in kingdom_features.json (e.g. ['Mammal', 'Reptile'])"""
    if not data_loader.KINGDOM_FEATURES_DATA:
        return []
    return list(data_loader.KINGDOM_FEATURES_DATA.get("F1", {}).keys())

def get_features_for_kingdom(kingdom: str) -> Dict[str, List[str]]:
    """
    Returns options for F1-F9 based on the selected kingdom.
    """
    features = {}
    if not data_loader.KINGDOM_FEATURES_DATA:
        return features

    for i in range(1, 10):
        f_key = f"F{i}"
        feature_data = data_loader.KINGDOM_FEATURES_DATA.get(f_key, {})
        # F9 (Capstone) is usually under "All", others are under the Kingdom name
        lookup_key = "All" if f_key == "F9" else kingdom

        # Get the list of options (dictionaries)
        options = feature_data.get(lookup_key, [])

        # Extract just the names for the UI dropdowns
        features[f_key] = [opt["name"] for opt in options if "name" in opt]

    return features

def get_origin_choices() -> List[Dict[str, Any]]:
    return data_loader.ORIGIN_CHOICES

def get_childhood_choices() -> List[Dict[str, Any]]:
    return data_loader.CHILDHOOD_CHOICES

def get_coming_of_age_choices() -> List[Dict[str, Any]]:
    return data_loader.COMING_OF_AGE_CHOICES

def get_training_choices() -> List[Dict[str, Any]]:
    return data_loader.TRAINING_CHOICES

def get_devotion_choices() -> List[Dict[str, Any]]:
    return data_loader.DEVOTION_CHOICES


# =============================================================================
# --- 2. CALCULATION LOGIC (The Math) - NEW ---
# =============================================================================

def calculate_creation_preview(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs a 'Dry Run' of character creation.
    Calculates final Stats and finds Eligible Talents based on choices.
    """
    # A. Initialize Base Stats (Default 10)
    stats = {s: 10 for s in data_loader.STATS_LIST}
    skills = {} # {skill_name: rank}

    # B. Apply Kingdom/Feature Modifiers
    kingdom = request_data.get('kingdom', "Mammal")
    feature_choices = request_data.get('features', {}) # { "F1": "ChoiceName", ... }

    # Logic to apply +2 modifiers found in JSON
    def apply_mod_dict(mods):
        for val_str, stat_list in mods.items():
            try:
                val = int(val_str.replace("+", ""))
                for stat in stat_list:
                    if stat in stats:
                        stats[stat] += val
            except ValueError:
                pass

    # Iterate F1-F9
    for f_id, choice_name in feature_choices.items():
        f_data_group = data_loader.KINGDOM_FEATURES_DATA.get(f_id, {})
        lookup_key = "All" if f_id == "F9" else kingdom
        options = f_data_group.get(lookup_key, [])

        # Find the specific choice dictionary
        choice_def = next((item for item in options if item["name"] == choice_name), None)
        if choice_def and "mods" in choice_def:
            apply_mod_dict(choice_def["mods"])

    # C. Apply Background Skills (Grant Rank 1)
    bg_choices = request_data.get('backgrounds', {})
    bg_map = {
        "origin": data_loader.ORIGIN_CHOICES,
        "childhood": data_loader.CHILDHOOD_CHOICES,
        "coming_of_age": data_loader.COMING_OF_AGE_CHOICES,
        "training": data_loader.TRAINING_CHOICES,
        "devotion": data_loader.DEVOTION_CHOICES
    }

    for cat, choice_name in bg_choices.items():
        source_list = bg_map.get(cat, [])
        selection = next((x for x in source_list if x["name"] == choice_name), None)
        if selection and "skills" in selection:
            for sk in selection["skills"]:
                skills[sk] = 1

    # D. Calculate Eligible Talents using Core Logic
    eligible_talents = core.find_eligible_talents(
        stats,
        skills,
        data_loader.TALENT_DATA,
        data_loader.STATS_LIST,
        data_loader.ALL_SKILLS
    )

    # Serialize talents for the UI
    serialized_talents = []
    for t in eligible_talents:
        if hasattr(t, 'dict'):
            serialized_talents.append(t.dict())
        elif hasattr(t, '__dict__'):
            serialized_talents.append(t.__dict__)
        else:
            serialized_talents.append(t)

    return {
        "calculated_stats": stats,
        "calculated_skills": list(skills.keys()),
        "eligible_talents": serialized_talents
    }

# =============================================================================
# --- 3. MAINTENANCE & PRESERVED FUNCTIONS ---
# =============================================================================

def get_all_stats() -> List[str]:
    return data_loader.STATS_LIST

def calculate_base_vitals_api(payload: dict):
    stats = payload.get("stats", {})
    level = payload.get("level", 1)
    req = models.BaseVitalsRequest(stats=stats, level=level)
    return core.calculate_base_vitals(req)

# --- Preserved Combat Functions ---

def get_npc_generation_params(template_id: str) -> Dict:
    templates = _get_data("npc_templates")
    template_data = templates.get(template_id)
    if not template_data:
        raise Exception(f"NPC template '{template_id}' not found.")
    return template_data

def get_item_template_params(item_id: str) -> Dict:
    templates = _get_data("item_templates")
    template_data = templates.get(item_id)
    if not template_data:
        raise Exception(f"Item template '{item_id}' not found.")
    return template_data

def get_loot_table(loot_table_ref: str) -> Dict:
    loot_tables = _get_data("loot_tables") or {}
    return loot_tables.get(loot_table_ref) or {}

def generate_npc_template(generation_request: Dict) -> Dict:
    req_schema = rules_models.NpcGenerationRequest(**generation_request)
    return rules_core.generate_npc_template_core(
        request=req_schema,
        all_skills_map=_get_data("all_skills"),
        generation_rules=_get_data("generation_rules"),
    )

def roll_initiative(**stats) -> Dict:
    req_schema = rules_models.InitiativeRequest(**stats)
    result = rules_core.calculate_initiative(req_schema)
    return result.model_dump()

def roll_contested_attack(attack_params: Dict) -> Dict:
    req_schema = rules_models.ContestedAttackRequest(**attack_params)
    result = rules_core.calculate_contested_attack(req_schema)
    return result.model_dump()

def calculate_damage(damage_params: Dict) -> Dict:
    req_schema = rules_models.DamageRequest(**damage_params)
    result = rules_core.calculate_damage(req_schema)
    return result.model_dump()

def get_weapon_data(category_name: str, weapon_type: str) -> Dict:
    if weapon_type == "melee":
        data = _get_data("melee_weapons").get(category_name)
    elif weapon_type == "ranged":
        data = _get_data("ranged_weapons").get(category_name)
    else:
        raise Exception(f"Unknown weapon type: {weapon_type}")
    if not data:
        data = _get_data("melee_weapons").get("Unarmed/Fist Weapons")
    return data or {"skill": "Unarmed/Fist Weapons", "skill_stat": "Fortitude", "damage": "1d4", "penalty": 0}

def get_armor_data(category_name: str) -> Dict:
    data = _get_data("armor").get(category_name)
    if not data:
        data = _get_data("armor").get("Natural/Unarmored")
    return data or {"skill": "Natural/Unarmored", "skill_stat": "Fortitude", "dr": 0}

def get_all_abilities() -> Dict:
    return _get_data("ability_data")

def get_all_ability_schools() -> List[str]:
    # Using the data_loader directly is consistent with Section 1.
    if not data_loader.ABILITY_DATA:
        return []
    return list(data_loader.ABILITY_DATA.keys())

def get_all_skills() -> Dict:
    return _get_data("all_skills")

def get_all_talents_data() -> Dict:
    return _get_data("talent_data")

def get_talent_details(talent_name: str) -> Dict:
    all_data = _get_data("talent_data")
    if not all_data: return {}
    for t in all_data.get("single_stat_mastery", []):
        if t.get("talent_name") == talent_name: return t
    for t in all_data.get("dual_stat_focus", []):
        if t.get("talent_name") == talent_name: return t
    skill_mastery = all_data.get("single_skill_mastery", {})
    for category, skills in skill_mastery.items():
        if isinstance(skills, list):
            for skill_entry in skills:
                for t in skill_entry.get("talents", []):
                    if t.get("talent_name") == talent_name: return t
    return {}

def get_ability_school(school_name: str) -> Dict:
    school = _get_data("ability_data").get(school_name)
    if not school:
        raise Exception(f"Ability school '{school_name}' not found.")
    return {
        "school": school_name,
        "resource_pool": school.get("resource_pool", school.get("resource")),
        "associated_stat": school.get("associated_stat", "Unknown"),
        "tiers": school.get("branches", [])
    }

def get_ability_data(ability_name: str) -> Optional[Dict]:
    """
    Searches all schools and branches to find a specific ability definition.
    """
    all_data = _get_data("ability_data")
    if not all_data: return None

    for school, data in all_data.items():
        for branch in data.get("branches", []):
            for tier in branch.get("tiers", []):
                if tier.get("name") == ability_name:
                    # return a copy so we don't mutate the cache
                    return tier.copy()
    return None

def get_status_effect_data(status_name: str) -> Dict:
    data = _get_data("status_effects").get(status_name)
    if not data:
        raise Exception(f"Status effect '{status_name}' not found.")
    return data

def get_all_status_effects() -> Dict:
    return _get_data("status_effects")

def calculate_talent_bonuses(character_context: Dict, action_type: str, tags: List[str] = None) -> Dict[str, int]:
    tags = tags or []
    active_talents_names = character_context.get("talents", [])
    
    hydrated_talents = []
    for t_name in active_talents_names:
        if isinstance(t_name, str):
            t_data = get_talent_details(t_name)
            if t_data:
                modifiers = []
                for m in t_data.get("modifiers", []):
                    effect_type = m.get("effect_type") or m.get("type")
                    target = m.get("target") or m.get("stat") or m.get("skill")
                    value = m.get("value") or m.get("bonus") or m.get("amount")

                    if effect_type and target and value is not None:
                        modifiers.append(rules_models.PassiveModifier(
                            effect_type=effect_type,
                            target=target,
                            value=value,
                            source_id=t_data.get("talent_name", t_name)
                        ))

                hydrated_talents.append(
                    rules_models.TalentInfo(
                        name=t_data.get("talent_name", t_name),
                        source="Hydrated",
                        effect=t_data.get("effect", ""),
                        modifiers=modifiers
                    )
                )
        elif isinstance(t_name, dict):
             modifiers = []
             for m in t_name.get("modifiers", []):
                 effect_type = m.get("effect_type") or m.get("type")
                 target = m.get("target") or m.get("stat") or m.get("skill")
                 value = m.get("value") or m.get("bonus") or m.get("amount")

                 if effect_type and target and value is not None:
                     modifiers.append(rules_models.PassiveModifier(
                         effect_type=effect_type,
                         target=target,
                         value=value,
                         source_id=t_name.get("name", "Unknown")
                     ))

             hydrated_talents.append(
                rules_models.TalentInfo(
                    name=t_name.get("name", "Unknown"),
                    source=t_name.get("source", ""),
                    effect=t_name.get("effect", ""),
                    modifiers=modifiers
                )
             )

    aggregated = rules_core.apply_passive_modifiers({}, {}, hydrated_talents)
    
    bonuses = {
        "attack_roll_bonus": 0,
        "defense_roll_bonus": 0,
        "damage_bonus": 0,
        "skill_check_bonus": 0,
        "stat_check_bonus": 0,
        "initiative_bonus": 0
    }

    if action_type == "attack_roll":
        for tag in tags:
            key = f"contested_check:{tag}"
            if key in aggregated["roll_bonuses"]:
                bonuses["attack_roll_bonus"] += aggregated["roll_bonuses"][key]
        for tag in tags:
            if tag in aggregated["skill_bonuses"]:
                bonuses["attack_roll_bonus"] += aggregated["skill_bonuses"][tag]

<<<<<<< Updated upstream
    elif action_type == "defense_roll":
        for tag in tags:
            key = f"contested_check:{tag}"
            if key in aggregated["roll_bonuses"]:
                bonuses["defense_roll_bonus"] += aggregated["roll_bonuses"][key]
        for tag in tags:
            if tag in aggregated["skill_bonuses"]:
                bonuses["defense_roll_bonus"] += aggregated["skill_bonuses"][tag]

    elif action_type == "damage_roll":
        bonuses["damage_bonus"] += aggregated["damage_bonuses"]
    
    return bonuses

def get_injury_effects(location: str, severity: str) -> Dict:
    # Wrapper for safety as combat_handler depends on it
    # (Actual implementation requires looking up injury effects data which is in INJURY_EFFECTS global)
    # _get_data("injury_effects")
    injury_data = _get_data("injury_effects")
    if not injury_data: return {}

    loc_data = injury_data.get(location, {})
    sub_loc = loc_data.get("Torso", {}) # Defaulting sub-location

    # Severity string to int mapping
    sev_int = "1"
    if severity.lower() == "minor": sev_int = "1"
    elif severity.lower() == "major": sev_int = "3"

    return sub_loc.get(sev_int, {})

def find_eligible_talents_api(payload: Dict) -> List[Dict]:
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

def register(orchestrator) -> None:
    logger.info("[rules] module registered (self-contained logic)")
=======
# Load data on import
try:
    data_loader.load_all_data()
except Exception as e:
    logger.error(f"Failed to load rule data on import: {e}")
>>>>>>> Stashed changes
