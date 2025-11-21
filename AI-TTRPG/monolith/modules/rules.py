import logging
from typing import List, Dict, Any
from .rules_pkg import data_loader, core, models, talent_logic

logger = logging.getLogger("monolith.rules")

# --- DATA ACCESSORS ---

def get_all_kingdoms() -> List[str]:
    """
    Returns the list of Kingdoms. 
    If data_loader fails, returns a Safe Mode fallback.
    """
    # 1. Try to get real data
    if data_loader.KINGDOM_FEATURES:
        f1_data = data_loader.KINGDOM_FEATURES.get("F1", {})
        if f1_data:
            return list(f1_data.keys())
            
    # 2. Fallback (Safe Mode) - Ensures UI never breaks
    logger.warning("Kingdom data missing. Using fallback list.")
    return ["Mammal", "Reptile", "Avian", "Aquatic", "Insect", "Plant"]

def get_all_ability_schools() -> List[str]:
    """Returns list of Schools."""
    if data_loader.ABILITY_DATA:
        return list(data_loader.ABILITY_DATA.keys())
    return ["Force", "Bastion", "Form", "Vector", "Create", "Element", "Life", "Death", "Space", "Time", "Mind", "Soul"]

def get_features_for_kingdom(kingdom: str) -> Dict[str, List[str]]:
    """Returns feature options for the UI."""
    features = {}
    # Fallback for safety
    if not data_loader.KINGDOM_FEATURES:
        for i in range(1, 10): features[f"F{i}"] = [f"Generic Feature {i}"]
        return features

    for i in range(1, 10):
        f_key = f"F{i}"
        feature_data = data_loader.KINGDOM_FEATURES.get(f_key, {})
        lookup_key = "All" if f_key == "F9" else kingdom
        options = feature_data.get(lookup_key, [])
        features[f_key] = [opt["name"] for opt in options if "name" in opt]
    
    return features

# --- WRAPPERS FOR BACKGROUNDS ---
def get_origin_choices() -> List[str]:
    return [item["name"] for item in data_loader.ORIGIN_CHOICES]

def get_childhood_choices() -> List[str]:
    return [item["name"] for item in data_loader.CHILDHOOD_CHOICES]

def get_coming_of_age_choices() -> List[str]:
    return [item["name"] for item in data_loader.COMING_OF_AGE_CHOICES]

def get_training_choices() -> List[str]:
    return [item["name"] for item in data_loader.TRAINING_CHOICES]

def get_devotion_choices() -> List[str]:
    return [item["name"] for item in data_loader.DEVOTION_CHOICES]

# --- LOGIC WRAPPERS ---

def calculate_creation_preview(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Dry Run calculation for Wizard UI."""
    stats = {s: 10 for s in data_loader.STATS_LIST}
    if not stats: # Fallback if stats list empty
         stats = {"Might": 10, "Endurance": 10, "Finesse": 10, "Reflexes": 10, "Vitality": 10, "Fortitude": 10, "Knowledge": 10, "Logic": 10, "Awareness": 10, "Intuition": 10, "Charm": 10, "Willpower": 10}
         
    skills = {}
    
    # Apply Mods (Stubbed for safety, real logic in services.py/core.py)
    # This allows the UI to proceed even if calculation logic has a bug
    return {
        "calculated_stats": stats,
        "calculated_skills": [],
        "eligible_talents": [{"name": "Basic Strike"}, {"name": "Defensive Stance"}] # Stub return
    }

def get_all_stats() -> List[str]:
    return data_loader.STATS_LIST

def get_ability_data(ability_name: str) -> Dict[str, Any]:
    # Flatten search
    if not data_loader.ABILITY_DATA: return {}
    for school, data in data_loader.ABILITY_DATA.items():
        for branch in data.get("branches", []):
            for tier in branch.get("tiers", []):
                if tier.get("name") == ability_name:
                    return tier
    return {}

def resolve_stat(context: dict, default: str, tags: list, check_type: str) -> str:
    # Wrapper for core logic
    return core.resolve_governing_stat(default, context, data_loader.TALENT_DATA, tags, check_type)

def calculate_talent_bonuses(context: dict, action: str, tags: list) -> dict:
    return talent_logic.calculate_talent_bonuses(context, action, tags)

def register(orchestrator):
    """
    Registers the rules module with the orchestrator.
    Since rules are mostly static data lookups, there might not be
    many event subscriptions, but this function is required by the
    module loader.
    """
    logger.info("Rules module registered.")
    # Future: Subscribe to rule-change events if dynamic rules are implemented.