# AI-TTRPG/monolith/modules/story_pkg/services.py
"""
This file acts as the service layer for the story module.
It has been refactored to call other monolith modules directly
instead of making HTTP API calls.
"""
import logging
from typing import Any, Dict, List

# --- Monolith Module Imports ---
# Import the public-facing API for each monolith module
from .. import rules as rules_api
from .. import world as world_api
from .. import character as character_api

# Note: map_generator and encounter_generator logic will be
# handled by the monolith orchestrator or called directly by story.py
# --- End Monolith Imports ---
from . import schemas

logger = logging.getLogger("monolith.story.services")

# Note: The _client: Any argument is kept in the function signatures
# to maintain compatibility with combat_handler and interaction_handler,
# but it will not be used.

# --- Rules Engine Functions ---
async def roll_initiative(_client: Any, **stats) -> Dict:
    logger.debug(f"Calling internal rules_api.roll_initiative with {stats.keys()}")
    return await rules_api.roll_initiative(None, **stats)

async def get_npc_generation_params(_client: Any, template_id: str) -> Dict:
    logger.debug(f"Calling internal rules_api.get_npc_generation_params for {template_id}")
    return await rules_api.get_npc_generation_params(None, template_id)

async def get_item_template_params(_client: Any, item_id: str) -> Dict:
    logger.debug(f"Calling internal rules_api.get_item_template_params for {item_id}")
    return await rules_api.get_item_template_params(None, item_id)

async def generate_npc_template(_client: Any, generation_request: Dict) -> Dict:
    logger.debug(f"Calling internal rules_api.generate_npc_template")
    return await rules_api.generate_npc_template(None, generation_request)

async def roll_contested_attack(_client: Any, attack_params: Dict) -> Dict:
    logger.debug(f"Calling internal rules_api.roll_contested_attack")
    return await rules_api.roll_contested_attack(None, attack_params)

async def calculate_damage(_client: Any, damage_params: Dict) -> Dict:
    logger.debug(f"Calling internal rules_api.calculate_damage")
    return await rules_api.calculate_damage(None, damage_params)

async def get_weapon_data(_client: Any, category_name: str, weapon_type: str) -> Dict:
    logger.debug(f"Calling internal rules_api.get_weapon_data for {category_name}")
    return await rules_api.get_weapon_data(None, category_name, weapon_type)

async def get_armor_data(_client: Any, category_name: str) -> Dict:
    logger.debug(f"Calling internal rules_api.get_armor_data for {category_name}")
    return await rules_api.get_armor_data(None, category_name)

# --- World Engine Functions ---
async def get_world_location_context(_client: Any, location_id: int) -> Dict:
    logger.debug(f"Calling internal world_api.get_world_location_context for {location_id}")
    return await world_api.get_world_location_context(None, location_id)

async def update_location_annotations(_client: Any, location_id: int, annotations: Dict[str, Any]) -> Dict:
    logger.debug(f"Calling internal world_api.update_location_annotations for {location_id}")
    return await world_api.update_location_annotations(None, location_id, annotations)

async def spawn_npc_in_world(_client: Any, spawn_request: schemas.OrchestrationSpawnNpc) -> Dict:
    logger.debug(f"Calling internal world_api.spawn_npc_in_world for {spawn_request.template_id}")
    return await world_api.spawn_npc_in_world(None, spawn_request)

async def get_npc_context(_client: Any, npc_instance_id: int) -> Dict:
    logger.debug(f"Calling internal world_api.get_npc_context for {npc_instance_id}")
    return await world_api.get_npc_context(None, npc_instance_id)

async def apply_damage_to_npc(_client: Any, npc_id: int, new_hp: int) -> Dict:
    logger.debug(f"Calling internal world_api.update_npc_state for {npc_id} (HP: {new_hp})")
    update_payload = {"current_hp": new_hp}
    return await world_api.update_npc_state(None, npc_id, update_payload)

async def spawn_item_in_world(_client: Any, spawn_request: schemas.OrchestrationSpawnItem) -> Dict:
    logger.debug(f"Calling internal world_api.spawn_item_in_world for {spawn_request.template_id}")
    return await world_api.spawn_item_in_world(None, spawn_request)

async def delete_item_from_world(_client: Any, item_id: int) -> Dict:
    logger.debug(f"Calling internal world_api.delete_item_from_world for {item_id}")
    return await world_api.delete_item_from_world(None, item_id)

async def update_location_map(_client: Any, location_id: int, map_update: Dict[str, Any]) -> Dict:
    logger.debug(f"Calling internal world_api.update_location_map for {location_id}")
    return await world_api.update_location_map(None, location_id, map_update)

# --- Character Engine Functions ---
async def get_character_context(_client: Any, char_id: str) -> Dict:
    logger.debug(f"Calling internal character_api.get_character_context for {char_id}")
    return await character_api.get_character_context(None, char_id)

async def apply_damage_to_character(_client: Any, char_id: str, damage_amount: int) -> Dict:
    logger.debug(f"Calling internal character_api.apply_damage_to_character for {char_id}")
    return await character_api.apply_damage_to_character(None, char_id, damage_amount)

async def add_item_to_character(_client: Any, char_id: str, item_id: str, quantity: int) -> Dict:
    logger.debug(f"Calling internal character_api.add_item_to_character for {char_id}")
    return await character_api.add_item_to_character(None, char_id, item_id, quantity)

async def remove_item_from_character(_client: Any, char_id: str, item_id: str, quantity: int) -> Dict:
    logger.debug(f"Calling internal character_api.remove_item_from_character for {char_id}")
    return await character_api.remove_item_from_character(None, char_id, item_id, quantity)
