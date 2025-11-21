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

def load_all_data():
    """Loads all JSON rule files into global variables."""
    global STATS_AND_SKILLS, KINGDOM_FEATURES, ABILITY_DATA, TALENT_DATA
    global STATUS_EFFECTS, ITEM_TEMPLATES, LOOT_TABLES, NPC_TEMPLATES
    global ORIGIN_CHOICES, CHILDHOOD_CHOICES, COMING_OF_AGE_CHOICES
    global TRAINING_CHOICES, DEVOTION_CHOICES
    global MELEE_WEAPONS, RANGED_WEAPONS, ARMOR_DATA
    global SKILL_MAPPINGS, SKILL_MAP, STATS_LIST

    logger.info("--- Loading Rules Data ---")
    
    STATS_AND_SKILLS = load_json_data("stats_and_skills.json")
    STATS_LIST = STATS_AND_SKILLS.get("stats", [])
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