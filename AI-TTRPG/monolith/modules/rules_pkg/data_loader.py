import json
import os
import logging
from typing import Any, List, Dict, Optional # <--- THE MISSING KEY

logger = logging.getLogger("monolith.rules.data_loader")

# --- GLOBAL DATA CONTAINERS ---
STATS_AND_SKILLS = {}
KINGDOM_FEATURES = {}
ABILITY_DATA = {}
TALENT_DATA = {}
STATUS_EFFECTS = {}
ITEM_TEMPLATES = {}
LOOT_TABLES = {}
NPC_TEMPLATES = {}
ORIGIN_CHOICES = []
CHILDHOOD_CHOICES = []
COMING_OF_AGE_CHOICES = []
TRAINING_CHOICES = []
DEVOTION_CHOICES = []
MELEE_WEAPONS = {}
RANGED_WEAPONS = {}
ARMOR_DATA = {}
SKILL_MAPPINGS = {}
SKILL_MAP = {} # New simple map
STATS_LIST = [] # New simple list

def get_data_dir():
    # Assumes this file is in modules/rules_pkg/
    return os.path.join(os.path.dirname(__file__), "data")

def load_json_data(filename: str) -> Any:
    filepath = os.path.join(get_data_dir(), filename)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            logger.info(f"Loaded {filename}")
            return data
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding {filename}: {e}")
        return {}

    for category_data in kingdom_data.values():
        if not isinstance(category_data, dict):
            continue
        for kingdom_list in category_data.values():
            if isinstance(kingdom_list, list):
                for feature in kingdom_list:
                    if not isinstance(feature, dict):
                        continue
                    feature_name = feature.get("name")
                    if feature_name:
                        feature_stats_map[feature_name] = feature
    print(
        f"Processed {len(feature_stats_map)} kingdom features into flat map."
    )
    return feature_stats_map

def _process_skills() -> (
    tuple[List[str], Dict[str, Dict[str, str]], Dict[str, Dict[str, str]], Dict[str, Any]]
):
    """Processes skills AND RETURNS stats list, categories dict, all_skills dict, AND techniques."""
    stats_data = _load_json("stats_and_skills.json")
    stats_list = stats_data.get("stats", [])
    skill_categories = stats_data.get("skill_categories", {})
    techniques = stats_data.get("techniques", {})
    all_skills = {}
    logger.info("--- Loading Rules Data ---")
    
    STATS_AND_SKILLS = load_json_data("stats_and_skills.json")
    STATS_LIST = STATS_AND_SKILLS.get("stats", [])
    skill_categories = STATS_AND_SKILLS.get("skill_categories", {})
    temp_skill_map = {}
    for category in skill_categories.values():
        for skill_name, governing_stat in category.items():
            temp_skill_map[skill_name] = {"governing_stat": governing_stat}
    SKILL_MAP = temp_skill_map


    if not stats_list:
        print("FATAL ERROR: 'stats' list not found or empty in stats_and_skills.json")
        return [], {}, {}, {}

    for category, skills_dict in skill_categories.items():
        if isinstance(skills_dict, dict):
            for skill_name, governing_stat in skills_dict.items():
                if governing_stat not in stats_list:
                    print(
                        f"Warning: Skill '{skill_name}' has invalid governing stat '{governing_stat}'. Skipping."
                    )
                    continue

                all_skills[skill_name] = {"category": category, "stat": governing_stat}
        else:
            print(
                f"Warning: Expected dict for skills in category '{category}', got {type(skills_dict)}. Skipping category."
            )

    print(f"Processed {len(all_skills)} skills into master map.")
    print(f"Processed {len(techniques)} techniques.")
    return stats_list, skill_categories, all_skills, techniques

# --- ADD THIS NEW HELPER FUNCTION ---
def _build_ability_map(ability_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes the nested ability data into a flat map for fast lookups.
    The key is the ability 'name', value is the ability data dict.
    """
    ability_map = {}
    for school_name, school_data in ability_data.items():
        if not isinstance(school_data, dict): continue
        for branch in school_data.get("branches", []):
            if not isinstance(branch, dict): continue
            for tier in branch.get("tiers", []):
                if not isinstance(tier, dict): continue

                ability_name = tier.get("name")
                if ability_name:
                    # Add reference to parent school for resource/stat lookups
                    tier["_school_resource"] = school_data.get("resource")
                    tier["_school_stat"] = school_data.get("associated_stat")
                    ability_map[ability_name] = tier
                else:
                    # This will catch all the T2-T9 abilities we haven't refactored
                    pass

    print(f"Processed {len(ability_map)} abilities into fast lookup map.")
    return ability_map
# --- END NEW FUNCTION ---

# --- Main Loading Function ---
# Global variables to hold the loaded data
STATS_LIST: List[str] = []
SKILL_CATEGORIES: Dict[str, List[str]] = {}
ALL_SKILLS: Dict[str, Dict[str, str]] = {}
TECHNIQUES: Dict[str, Any] = {} # <-- ADD THIS NEW GLOBAL
ABILITY_DATA: Dict[str, Any] = {}
ABILITY_MAP: Dict[str, Any] = {} # <-- ADD THIS NEW GLOBAL
TALENT_DATA: Dict[str, Any] = {}
FEATURE_STATS_MAP: Dict[str, Any] = {}
KINGDOM_FEATURES_DATA: Dict[str, Any] = {}
MELEE_WEAPONS: Dict[str, Any] = {}
RANGED_WEAPONS: Dict[str, Any] = {}
ARMOR: Dict[str, Any] = {}
INJURY_EFFECTS: Dict[str, Any] = {}
STATUS_EFFECTS: Dict[str, Any] = {}
EQUIPMENT_CATEGORY_TO_SKILL_MAP: Dict[str, str] = {}
NPC_TEMPLATES: Dict[str, Any] = {}
ITEM_TEMPLATES: Dict[str, Any] = {}
GENERATION_RULES: Dict[str, Any] = {} # ADDED: New global for NPC rules

# --- ADD NEW BACKGROUND GLOBALS ---
ORIGIN_CHOICES: List[Dict[str, Any]] = []
CHILDHOOD_CHOICES: List[Dict[str, Any]] = []
COMING_OF_AGE_CHOICES: List[Dict[str, Any]] = []
TRAINING_CHOICES: List[Dict[str, Any]] = []
DEVOTION_CHOICES: List[Dict[str, Any]] = []
# --- END ADD ---

def load_data() -> Dict[str, Any]:
    """Loads all rules data and returns it in a dictionary."""
    global STATS_LIST, SKILL_CATEGORIES, ALL_SKILLS, TECHNIQUES, ABILITY_DATA, ABILITY_MAP, TALENT_DATA, FEATURE_STATS_MAP, GENERATION_RULES
    global MELEE_WEAPONS, RANGED_WEAPONS, ARMOR, INJURY_EFFECTS, STATUS_EFFECTS, EQUIPMENT_CATEGORY_TO_SKILL_MAP, KINGDOM_FEATURES_DATA, NPC_TEMPLATES, ITEM_TEMPLATES
    global ORIGIN_CHOICES, CHILDHOOD_CHOICES, COMING_OF_AGE_CHOICES, TRAINING_CHOICES, DEVOTION_CHOICES

    print("Starting data loading process...")
    loaded_data = {}
    try:
        # Load stats and skills
        STATS_LIST, SKILL_CATEGORIES, ALL_SKILLS, TECHNIQUES = _process_skills()

        # Load abilities
        ABILITY_DATA = _load_json("abilities.json")
        if not isinstance(ABILITY_DATA, dict):
            print(
                f"--- WARNING: ABILITY_DATA did NOT load as a dictionary. Type: {type(ABILITY_DATA)} ---"
            )
            ABILITY_DATA = {}

        # --- NEW: Build the fast lookup map ---
        ABILITY_MAP = _build_ability_map(ABILITY_DATA)
        # --- END NEW ---

        # Load talents
        TALENT_DATA = _load_json("talents.json")
        if not isinstance(TALENT_DATA, dict):
            print(
                f"--- WARNING: TALENT_DATA did NOT load as a dictionary. Type: {type(TALENT_DATA)} ---"
            )
            TALENT_DATA = {}

        # Process kingdom features (flat map for lookups)
        FEATURE_STATS_MAP = _process_kingdom_features()

        # Load kingdom features (full structure for creation)
        KINGDOM_FEATURES_DATA = _load_json("kingdom_features.json")

        # Load combat data
        MELEE_WEAPONS = _load_json("melee_weapons.json")
        RANGED_WEAPONS = _load_json("ranged_weapons.json")
        ARMOR = _load_json("armor.json")

        # Load skill mappings
        EQUIPMENT_CATEGORY_TO_SKILL_MAP = _load_json("skill_mappings.json")

        # Load injury data
        INJURY_EFFECTS = _load_json("injury_effects.json")

        # Load Status Effects
        status_file = os.path.join(DATA_DIR, "status_effects.json")
        try:
            if os.path.exists(status_file):
                with open(status_file, "r", encoding="utf-8") as f:
                    STATUS_EFFECTS = json.load(f)
                print(
                    f"Loaded {len(STATUS_EFFECTS)} status effect definitions from status_effects.json."
                )
            else:
                print(
                    f"WARNING: status_effects.json not found at {status_file}. Status lookup will fail."
                )
                STATUS_EFFECTS = {}
        except json.JSONDecodeError as e:
            print(f"ERROR decoding status_effects.json: {e}. Status lookup will fail.")
            STATUS_EFFECTS = {}
        except Exception as e:
            print(f"ERROR loading status_effects.json: {e}. Status lookup will fail.")
            STATUS_EFFECTS = {}

        # --- LOAD NEW BACKGROUND CHOICES ---
        ORIGIN_CHOICES = _load_json("origin_choices.json")
        CHILDHOOD_CHOICES = _load_json("childhood_choices.json")
        COMING_OF_AGE_CHOICES = _load_json("coming_of_age_choices.json")
        TRAINING_CHOICES = _load_json("training_choices.json")
        DEVOTION_CHOICES = _load_json("devotion_choices.json")
        # --- END LOAD ---

        NPC_TEMPLATES = _load_json("npc_templates.json")
        ITEM_TEMPLATES = _load_json("item_templates.json")
        GENERATION_RULES = _load_json("generation_rules.json") # ADDED: Load NPC rules

        loaded_data = {
            "stats_list": STATS_LIST,
            "skill_categories": SKILL_CATEGORIES,
            "all_skills": ALL_SKILLS,
            "techniques": TECHNIQUES,
            "ability_data": ABILITY_DATA, # The full structure for char creation
            "ability_map": ABILITY_MAP, # The fast map for combat
            "talent_data": TALENT_DATA,
            "feature_stats_map": FEATURE_STATS_MAP,
            "kingdom_features_data": KINGDOM_FEATURES_DATA,
            "melee_weapons": MELEE_WEAPONS,
            "ranged_weapons": RANGED_WEAPONS,
            "armor": ARMOR,
            "injury_effects": INJURY_EFFECTS,
            "status_effects": STATUS_EFFECTS,
            "equipment_category_to_skill_map": EQUIPMENT_CATEGORY_TO_SKILL_MAP,
            # --- ADD TO RETURN DICT ---
            "origin_choices": ORIGIN_CHOICES,
            "childhood_choices": CHILDHOOD_CHOICES,
            "coming_of_age_choices": COMING_OF_AGE_CHOICES,
            "training_choices": TRAINING_CHOICES,
            "devotion_choices": DEVOTION_CHOICES,
            # --- END ADD ---
            "npc_templates": NPC_TEMPLATES,
            "item_templates": ITEM_TEMPLATES,
            "generation_rules": GENERATION_RULES, # ADDED: Return NPC rules
        }

        print(f"DEBUG: STATS_LIST len: {len(STATS_LIST)}")
        print(f"DEBUG: ALL_SKILLS len: {len(ALL_SKILLS)}")
        print(f"DEBUG: ABILITY_DATA len: {len(ABILITY_DATA)}")
        print(f"DEBUG: ABILITY_MAP len: {len(ABILITY_MAP)}")
        print(f"DEBUG: TALENT_DATA len: {len(TALENT_DATA)}")
        print(f"DEBUG: FEATURE_STATS_MAP len: {len(FEATURE_STATS_MAP)}")
        print(
            f"DEBUG: KINGDOM_FEATURES_DATA keys: {len(KINGDOM_FEATURES_DATA.keys())}"
        )
        print(f"Loaded {len(MELEE_WEAPONS)} melee weapon categories.")
        print(f"Loaded {len(RANGED_WEAPONS)} ranged weapon categories.")
        print(f"Loaded {len(ARMOR)} armor categories.")
        print(f"Loaded {len(EQUIPMENT_CATEGORY_TO_SKILL_MAP)} skill mappings.")
        print(f"Loaded {len(INJURY_EFFECTS)} major injury locations.")
        print(f"Loaded {len(STATUS_EFFECTS)} status effect definitions.")
        # --- ADD PRINT STATEMENTS ---
        print(f"Loaded {len(ORIGIN_CHOICES)} origin choices.")
        print(f"Loaded {len(CHILDHOOD_CHOICES)} childhood choices.")
        print(f"Loaded {len(COMING_OF_AGE_CHOICES)} coming of age choices.")
        print(f"Loaded {len(TRAINING_CHOICES)} training choices.")
        print(f"Loaded {len(DEVOTION_CHOICES)} devotion choices.")
        print(f"Loaded {len(NPC_TEMPLATES)} NPC templates.")
        print(f"Loaded {len(ITEM_TEMPLATES)} item templates.")
        print(f"Loaded {len(GENERATION_RULES)} NPC generation rule sections.") # ADDED print
        # --- END ADD ---

        print("--- Rules Engine Data Parsed Successfully ---")
        return loaded_data

    except Exception as e:
        print(f"FATAL ERROR during load_data execution: {e}")
        raise

def get_item_template(item_id: str) -> Optional[Item]:
    """
    Retrieves and validates a single item template from the loaded data.
    """
    if not ITEM_TEMPLATES:
        load_data()

    item_data = ITEM_TEMPLATES.get(item_id)
    if not item_data:
        print(f"ERROR: Item template not found for ID: {item_id}")
        return None

    try:
        return Item.model_validate(item_data)
    except ValidationError as e:
        print(f"ERROR: Pydantic validation failed for item '{item_id}': {e}")
        return None

    SKILL_MAP = STATS_AND_SKILLS.get("skills", {})

    # --- THE CRITICAL FIX: Load Kingdom Features ---
    KINGDOM_FEATURES = load_json_data("kingdom_features.json")
    
    ABILITY_DATA = load_json_data("abilities.json")
    TALENT_DATA = load_json_data("talents.json")
    STATUS_EFFECTS = load_json_data("status_effects.json")
    ITEM_TEMPLATES = load_json_data("item_templates.json")
    LOOT_TABLES = load_json_data("loot_tables.json")
    NPC_TEMPLATES = load_json_data("npc_templates.json")
    
    MELEE_WEAPONS = load_json_data("melee_weapons.json")
    RANGED_WEAPONS = load_json_data("ranged_weapons.json")
    ARMOR_DATA = load_json_data("armor.json")
    SKILL_MAPPINGS = load_json_data("skill_mappings.json")

    # Load Lists (Handle list vs dict structure safely)
    def load_list(fname):
        d = load_json_data(fname)
        if isinstance(d, list): return d
        return []

    ORIGIN_CHOICES = load_list("origin_choices.json")
    CHILDHOOD_CHOICES = load_list("childhood_choices.json")
    COMING_OF_AGE_CHOICES = load_list("coming_of_age_choices.json")
    TRAINING_CHOICES = load_list("training_choices.json")
    DEVOTION_CHOICES = load_list("devotion_choices.json")
    
    logger.info("--- Rules Data Load Complete ---")

def get_item_template(template_id: str) -> Optional[Dict[str, Any]]:
    return ITEM_TEMPLATES.get(template_id)
main
