import logging
from typing import List, Dict, Any
from .rules_pkg import data_loader, core, models, talent_logic

logger = logging.getLogger("monolith.rules")

# Data accessors

def get_all_kingdoms() -> List[str]:
    """Returns list of Kingdoms, fallback if missing."""
    if data_loader.KINGDOM_FEATURES:
        f1 = data_loader.KINGDOM_FEATURES.get("F1", {})
        if f1:
            return list(f1.keys())
    logger.warning("Kingdom data missing. Using fallback list.")
    return ["Mammal", "Reptile", "Avian", "Aquatic", "Insect", "Plant"]

def get_all_ability_schools() -> List[str]:
    if data_loader.ABILITY_DATA:
        return list(data_loader.ABILITY_DATA.keys())
    return ["Force", "Bastion", "Form", "Vector", "Create", "Element", "Life", "Death", "Space", "Time", "Mind", "Soul"]

def get_features_for_kingdom(kingdom: str) -> Dict[str, List[str]]:
    features = {}
    if not data_loader.KINGDOM_FEATURES:
        # Fallback if data is missing
        for i in range(1, 10):
            features[f"F{i}"] = [f"Generic Feature {i}"]
        return features
    
    # Dynamically iterate over all keys (F1, F2, F9, etc.)
    # We filter for keys starting with 'F' followed by digits to be safe
    feature_keys = [k for k in data_loader.KINGDOM_FEATURES.keys() if k.startswith("F") and k[1:].isdigit()]
    
    # Sort keys numerically (F1, F2, ... F9, F10)
    feature_keys.sort(key=lambda x: int(x[1:]))

    for f_key in feature_keys:
        feature_data = data_loader.KINGDOM_FEATURES.get(f_key, {})
        # F9 (and potentially others in future) uses "All" instead of specific kingdoms
        lookup_key = "All" if "All" in feature_data else kingdom
        
        # If the specific kingdom isn't found and "All" isn't there, try "All" as fallback
        if lookup_key not in feature_data and "All" in feature_data:
            lookup_key = "All"

        options = feature_data.get(lookup_key, [])
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

# Logic wrappers

def calculate_creation_preview(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Dry run calculation for Wizard UI."""
    stats = {s: 10 for s in data_loader.STATS_LIST}
    if not stats:
        stats = {"Might": 10, "Endurance": 10, "Finesse": 10, "Reflexes": 10, "Vitality": 10, "Fortitude": 10, "Knowledge": 10, "Logic": 10, "Awareness": 10, "Intuition": 10, "Charm": 10, "Willpower": 10}
    skills = {}
    return {"calculated_stats": stats, "calculated_skills": [], "eligible_talents": [{"name": "Basic Strike"}, {"name": "Defensive Stance"}]}

def get_all_stats() -> List[str]:
    return data_loader.STATS_LIST

def get_all_skills() -> List[str]:
    return list(data_loader.SKILL_MAP.keys())

def get_all_talents_data() -> Dict[str, Any]:
    """Returns structured talent data."""
    return data_loader.TALENT_DATA

def get_ability_school(school_name: str) -> Dict[str, Any]:
    """Returns data for a specific ability school."""
    if not data_loader.ABILITY_DATA:
        return {}
    return data_loader.ABILITY_DATA.get(school_name, {})

def get_ability_data(ability_name: str) -> Dict[str, Any]:
    if not data_loader.ABILITY_DATA:
        return {}
    for school, data in data_loader.ABILITY_DATA.items():
        for branch in data.get("branches", []):
            for tier in branch.get("tiers", []):
                if tier.get("name") == ability_name:
                    return tier
    return {}

def resolve_stat(context: dict, default: str, tags: list, check_type: str) -> str:
    return core.resolve_governing_stat(default, context, data_loader.TALENT_DATA, tags, check_type)

def calculate_talent_bonuses(context: dict, action: str, tags: list) -> dict:
    return talent_logic.calculate_talent_bonuses(context, action, tags)

def _get_data(data_key: str) -> Any:
    mapping = {
        "kingdom_features_data": "kingdom_features.json",
        "ability_data": "abilities.json",
        "stats_and_skills": "stats_and_skills.json",
        "talents": "talents.json",
        "status_effects": "status_effects.json",
        "item_templates": "item_templates.json",
        "loot_tables": "loot_tables.json",
        "npc_templates": "npc_templates.json",
        "melee_weapons": "melee_weapons.json",
        "ranged_weapons": "ranged_weapons.json",
        "armor": "armor.json",
        "skill_mappings": "skill_mappings.json",
    }
    filename = mapping.get(data_key)
    if not filename:
        logger.warning(f"_get_data unknown key {data_key}")
        return {}
    return data_loader.load_json_data(filename)

    if action_type == "attack_roll":
        for tag in tags:
            key = f"contested_check:{tag}"
            if key in aggregated["roll_bonuses"]:
                bonuses["attack_roll_bonus"] += aggregated["roll_bonuses"][key]
        for tag in tags:
            if tag in aggregated["skill_bonuses"]:
                bonuses["attack_roll_bonus"] += aggregated["skill_bonuses"][tag]

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
# Load data on import
try:
    data_loader.load_all_data()
except Exception as e:

    logger.error(f"Failed to load rule data on import: {e}")


    logger.error(f"Failed to load rule data on import: {e}")
 main
