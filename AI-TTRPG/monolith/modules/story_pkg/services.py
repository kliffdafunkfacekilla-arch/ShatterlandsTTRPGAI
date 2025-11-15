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
def roll_initiative(**stats) -> Dict:
    logger.debug(f"Calling internal rules_api.roll_initiative with {stats.keys()}")
    return rules_api.roll_initiative(**stats)

def get_npc_generation_params(template_id: str) -> Dict:
    logger.debug(f"Calling internal rules_api.get_npc_generation_params for {template_id}")
    return rules_api.get_npc_generation_params(template_id)

def get_item_template_params(item_id: str) -> Dict:
    logger.debug(f"Calling internal rules_api.get_item_template_params for {item_id}")
    return rules_api.get_item_template_params(item_id)

def generate_npc_template(generation_request: Dict) -> Dict:
    logger.debug(f"Calling internal rules_api.generate_npc_template")
    return rules_api.generate_npc_template(generation_request)

def roll_contested_attack(attack_params: Dict) -> Dict:
    logger.debug(f"Calling internal rules_api.roll_contested_attack")
    return rules_api.roll_contested_attack(attack_params)

def calculate_damage(damage_params: Dict) -> Dict:
    logger.debug(f"Calling internal rules_api.calculate_damage")
    return rules_api.calculate_damage(damage_params)

def get_weapon_data(category_name: str, weapon_type: str) -> Dict:
    logger.debug(f"Calling internal rules_api.get_weapon_data for {category_name}")
    return rules_api.get_weapon_data(category_name, weapon_type)

def get_armor_data(category_name: str) -> Dict:
    logger.debug(f"Calling internal rules_api.get_armor_data for {category_name}")
    return rules_api.get_armor_data(category_name)

# --- World Engine Functions ---
def get_world_location_context(location_id: int) -> Dict:
    logger.debug(f"Calling internal world_api.get_world_location_context for {location_id}")
    return world_api.get_world_location_context(location_id)

def update_location_annotations(location_id: int, annotations: Dict[str, Any]) -> Dict:
    logger.debug(f"Calling internal world_api.update_location_annotations for {location_id}")
    return world_api.update_location_annotations(location_id, annotations)

def spawn_npc_in_world(spawn_request: schemas.OrchestrationSpawnNpc) -> Dict:
    logger.debug(f"Calling internal world_api.spawn_npc_in_world for {spawn_request.template_id}")
    return world_api.spawn_npc_in_world(spawn_request)

def get_npc_context(npc_instance_id: int) -> Dict:
    logger.debug(f"Calling internal world_api.get_npc_context for {npc_instance_id}")
    return world_api.get_npc_context(npc_instance_id)

def apply_damage_to_npc(npc_id: int, new_hp: int) -> Dict:
    logger.debug(f"Calling internal world_api.update_npc_state for {npc_id} (HP: {new_hp})")
    update_payload = {"current_hp": new_hp}
    return world_api.update_npc_state(npc_id, update_payload)

def spawn_item_in_world(spawn_request: schemas.OrchestrationSpawnItem) -> Dict:
    logger.debug(f"Calling internal world_api.spawn_item_in_world for {spawn_request.template_id}")
    return world_api.spawn_item_in_world(spawn_request)

def delete_item_from_world(item_id: int) -> Dict:
    logger.debug(f"Calling internal world_api.delete_item_from_world for {item_id}")
    return world_api.delete_item_from_world(item_id)

def update_location_map(location_id: int, map_update: Dict[str, Any]) -> Dict:
    logger.debug(f"Calling internal world_api.update_location_map for {location_id}")
    return world_api.update_location_map(location_id, map_update)

# --- Character Engine Functions ---
def get_character_context(char_id: str) -> Dict:
    logger.debug(f"Calling internal character_api.get_character_context for {char_id}")
    return char_api.get_character_context(char_id)

def apply_damage_to_character(char_id: str, damage_amount: int) -> Dict:
    logger.debug(f"Calling internal character_api.apply_damage_to_character for {char_id}")
    return char_api.apply_damage_to_character(char_id, damage_amount)

def apply_healing_to_character(char_id: str, amount: int):
    """Applies healing to a character. Fire and forget."""
    logger.debug(f"Calling internal character_api.apply_healing_to_character for {char_id}")
    return character_api.apply_healing_to_character(char_id, amount)

def add_item_to_character(char_id: str, item_id: str, quantity: int) -> Dict:
    logger.debug(f"Calling internal character_api.add_item_to_character for {char_id}")
    return char_api.add_item_to_character(char_id, item_id, quantity)

def remove_item_from_character(char_id: str, item_id: str, quantity: int) -> Dict:
    logger.debug(f"Calling internal character_api.remove_item_from_character for {char_id}")
    return char_api.remove_item_from_character(char_id, item_id, quantity)
