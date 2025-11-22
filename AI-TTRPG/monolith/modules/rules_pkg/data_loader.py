import json
import os
import logging
from typing import Any, List, Dict, Optional
from monolith.modules.rules_pkg import models

logger = logging.getLogger("monolith.rules.data_loader")

class RulesEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RulesEngine, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        self.stats_and_skills: Optional[models.StatsAndSkills] = None
        self.kingdom_features: Dict[str, Dict[str, List[models.KingdomFeature]]] = {}
        self.abilities: Dict[str, models.AbilityClass] = {}
        self.talents: Dict[str, Any] = {} # TODO: Strict typing
        self.items: Dict[str, models.ItemTemplate] = {}
        self.loot_tables: Dict[str, Any] = {}
        self.npc_templates: Dict[str, Any] = {}
        self.status_effects: Dict[str, Any] = {}
        
        # Lists
        self.origin_choices: List[Any] = []
        self.childhood_choices: List[Any] = []
        self.coming_of_age_choices: List[Any] = []
        self.training_choices: List[Any] = []
        self.devotion_choices: List[Any] = []
        
        # Legacy/Other
        self.melee_weapons: Dict[str, Any] = {}
        self.ranged_weapons: Dict[str, Any] = {}
        self.armor_data: Dict[str, Any] = {}
        self.skill_mappings: Dict[str, Any] = {}
        
        self.initialized = True

    def load_json(self, filename: str, model: Optional[Any] = None) -> Any:
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if model:
                    try:
                        # Handle Dict structures for specific models
                        if model == models.StatsAndSkills:
                            return model(**data)
                        elif model == Dict[str, models.ItemTemplate]:
                            return {k: models.ItemTemplate(**v) for k, v in data.items()}
                        elif model == Dict[str, models.AbilityClass]:
                             return {k: models.AbilityClass(**v) for k, v in data.items()}
                        # Add other specific model handlers as needed
                        return data 
                    except Exception as e:
                        logger.error(f"Validation error for {filename}: {e}")
                        return data # Fallback to raw data on validation failure for now
                return data
        except FileNotFoundError:
            logger.error(f"File not found: {filename}")
            return {} if not model else None
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding {filename}: {e}")
            return {} if not model else None

    def load_all_data(self):
        logger.info("--- RulesEngine: Loading Data ---")
        
        self.stats_and_skills = self.load_json("stats_and_skills.json", models.StatsAndSkills)
        self.kingdom_features = self.load_json("kingdom_features.json") # Complex nested dict, skip validation for now
        self.abilities = self.load_json("abilities.json", Dict[str, models.AbilityClass])
        self.talents = self.load_json("talents.json")
        self.items = self.load_json("item_templates.json", Dict[str, models.ItemTemplate])
        
        self.status_effects = self.load_json("status_effects.json")
        self.loot_tables = self.load_json("loot_tables.json")
        self.npc_templates = self.load_json("npc_templates.json")
        
        self.melee_weapons = self.load_json("melee_weapons.json")
        self.ranged_weapons = self.load_json("ranged_weapons.json")
        self.armor_data = self.load_json("armor.json")
        self.skill_mappings = self.load_json("skill_mappings.json")
        
        self.origin_choices = self.load_json("origin_choices.json")
        self.childhood_choices = self.load_json("childhood_choices.json")
        self.coming_of_age_choices = self.load_json("coming_of_age_choices.json")
        self.training_choices = self.load_json("training_choices.json")
        self.devotion_choices = self.load_json("devotion_choices.json")
        
        logger.info("--- RulesEngine: Data Load Complete ---")

# Singleton Instance
rules_engine = RulesEngine()

# --- GLOBAL PROXIES (For Backward Compatibility) ---
# These will be populated after load_all_data is called
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
SKILL_MAP = {}
STATS_LIST = []

def load_all_data():
    """Loads all data via RulesEngine and populates globals."""
    global STATS_AND_SKILLS, KINGDOM_FEATURES, ABILITY_DATA, TALENT_DATA
    global STATUS_EFFECTS, ITEM_TEMPLATES, LOOT_TABLES, NPC_TEMPLATES
    global ORIGIN_CHOICES, CHILDHOOD_CHOICES, COMING_OF_AGE_CHOICES
    global TRAINING_CHOICES, DEVOTION_CHOICES
    global MELEE_WEAPONS, RANGED_WEAPONS, ARMOR_DATA
    global SKILL_MAPPINGS, SKILL_MAP, STATS_LIST

    rules_engine.load_all_data()
    
    # Populate globals from engine
    if rules_engine.stats_and_skills:
        STATS_AND_SKILLS = rules_engine.stats_and_skills.model_dump()
        STATS_LIST = rules_engine.stats_and_skills.stats
        SKILL_MAP = rules_engine.stats_and_skills.skill_categories # Note: Structure might differ slightly, check usage
    
    KINGDOM_FEATURES = rules_engine.kingdom_features
    
    # For models, we might need to dump them to dicts if consumers expect dicts
    # But for now, let's see if we can pass objects or if we need to dump.
    # Existing code likely expects dicts.
    
    ABILITY_DATA = {k: v.model_dump() for k, v in rules_engine.abilities.items()}
    TALENT_DATA = rules_engine.talents
    ITEM_TEMPLATES = {k: v.model_dump() for k, v in rules_engine.items.items()}
    
    STATUS_EFFECTS = rules_engine.status_effects
    LOOT_TABLES = rules_engine.loot_tables
    NPC_TEMPLATES = rules_engine.npc_templates
    
    MELEE_WEAPONS = rules_engine.melee_weapons
    RANGED_WEAPONS = rules_engine.ranged_weapons
    ARMOR_DATA = rules_engine.armor_data
    SKILL_MAPPINGS = rules_engine.skill_mappings
    
    ORIGIN_CHOICES = rules_engine.origin_choices
    CHILDHOOD_CHOICES = rules_engine.childhood_choices
    COMING_OF_AGE_CHOICES = rules_engine.coming_of_age_choices
    TRAINING_CHOICES = rules_engine.training_choices
    DEVOTION_CHOICES = rules_engine.devotion_choices

def get_item_template(template_id: str) -> Optional[Dict[str, Any]]:
    # Use the engine but return dict for compatibility
    item = rules_engine.items.get(template_id)
    return item.model_dump() if item else None

def load_json_data(filename: str) -> Any:
    # Deprecated direct access
    return rules_engine.load_json(filename)