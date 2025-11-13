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

# --- Public API Functions (mirroring original HTTP API) ---
async def get_npc_generation_params(_client: Any, template_id: str) -> Dict:
    """Looks up the generation parameters for a given NPC template ID."""
    templates = _get_data("npc_templates")
    template_data = templates.get(template_id)
    if not template_data:
        raise Exception(f"NPC template '{template_id}' not found.")
    return template_data

async def get_item_template_params(_client: Any, item_id: str) -> Dict:
    """Calls rules_engine to get definition for an item template ID."""
    templates = _get_data("item_templates")
    template_data = templates.get(item_id)
    if not template_data:
        raise Exception(f"Item template '{item_id}' not found.")
    return template_data

async def generate_npc_template(_client: Any, generation_request: Dict) -> Dict:
    """Generates a full NPC template."""
    req_schema = rules_models.NpcGenerationRequest(**generation_request)
    return rules_core.generate_npc_template_core(
        request=req_schema,
        all_skills_map=_get_data("all_skills"),
        generation_rules=_get_data("generation_rules"),
    )

async def roll_initiative(_client: Any, **stats) -> Dict:
    """Rolls initiative based on the provided attribute scores."""
    req_schema = rules_models.InitiativeRequest(**stats)
    result = rules_core.calculate_initiative(req_schema)
    return result.model_dump() # Convert Pydantic model to dict

async def roll_contested_attack(_client: Any, attack_params: Dict) -> Dict:
    """Performs a contested attack roll."""
    req_schema = rules_models.ContestedAttackRequest(**attack_params)
    result = rules_core.calculate_contested_attack(req_schema)
    return result.model_dump()

async def calculate_damage(_client: Any, damage_params: Dict) -> Dict:
    """Calculates final damage."""
    req_schema = rules_models.DamageRequest(**damage_params)
    result = rules_core.calculate_damage(req_schema)
    return result.model_dump()

async def get_weapon_data(_client: Any, category_name: str, weapon_type: str) -> Dict:
    """Looks up the stats for a specific weapon category."""
    if weapon_type == "melee":
        data = _get_data("melee_weapons").get(category_name)
    elif weapon_type == "ranged":
        data = _get_data("ranged_weapons").get(category_name)
    else:
        raise Exception(f"Unknown weapon type: {weapon_type}")

    if not data:
        # Fallback to Brawling/Unarmed
        logger.warning(f"Weapon category '{category_name}' not found. Defaulting to 'Unarmed/Fist Weapons'.")
        data = _get_data("melee_weapons").get("Unarmed/Fist Weapons")
        if not data: # Handle deep fallback
             return {"skill": "Unarmed/Fist Weapons", "skill_stat": "Fortitude", "damage": "1d4", "penalty": 0}

    return data

async def get_armor_data(_client: Any, category_name: str) -> Dict:
    """Looks up the stats for a specific armor category."""
    data = _get_data("armor").get(category_name)
    if not data:
         # Fallback to Unarmored
        logger.warning(f"Armor category '{category_name}' not found. Defaulting to 'Natural/Unarmored'.")
        data = _get_data("armor").get("Natural/Unarmored")
        if not data: # Handle deep fallback
            return {"skill": "Natural/Unarmored", "skill_stat": "Fortitude", "dr": 0}

    return data

def register(orchestrator) -> None:
    # This module is now self-contained. It doesn't need to subscribe
    # to the event bus, but it's loaded and its data is cached.
    # Other modules (like 'story') will import and call its functions.
    logger.info("[rules] module registered (self-contained logic)")
