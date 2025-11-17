# AI-TTRPG/monolith/modules/story_pkg/combat_handler.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
import httpx
from typing import List, Dict, Any, Tuple, Optional, Callable
from . import crud, models, schemas, services
# --- ADDED THIS IMPORT ---
from ..rules_pkg import core as rules_core
# --- END ADD ---
import random
import re
import logging

logger = logging.getLogger("monolith.story.combat")

# --- Combat Reward Helper ---
async def _grant_combat_rewards(db: Session, combat: models.CombatEncounter, log: List[str]):
def _grant_combat_rewards(db: Session, combat: models.CombatEncounter, log: List[str]):
    """
    Calculates and grants rewards (items, XP, etc.) upon combat victory.
    """
    logger.info(f"Granting rewards for combat {combat.id}")

    # 1. Find the player(s)
    player_ids = [p.actor_id for p in combat.participants if p.actor_type == "player" and p.actor_id]
    if not player_ids:
        log.append("No surviving players to grant rewards to.")
        return

    # For now, give all loot to the first player
    primary_player_id = player_ids[0]

    # 2. Loop over defeated NPCs
    for p in combat.participants:
        if p.actor_type == "npc":
            try:
                # Check if NPC is dead
                _, npc_context = await get_actor_context(p.actor_id)
                _, npc_context = get_actor_context(p.actor_id)
                if npc_context.get("current_hp", 0) > 0:
                    continue # Skip living NPCs

                template_id = npc_context.get("template_id")
                if not template_id:
                    continue

                # 3. Get loot table info from rules
                template_data = services.get_npc_generation_params(template_id)
                loot_table_ref = template_data.get("loot_table_ref")

                # 4. Get loot table data and roll for drops
                # --- MODIFIED: Call new service function ---
                template_data = await services.get_npc_generation_params(template_id)
                loot_table_ref = template_data.get("loot_table_ref")
                template_data = services.get_npc_generation_params(template_id)
                loot_table_ref = template_data.get("loot_table_ref")

                if not loot_table_ref:
                    continue

                # 4. Get loot table data and roll for drops
                loot_table = await services.get_loot_table(loot_table_ref)
                for item_id, loot_info in loot_table.items():
                    if random.random() < loot_info.get("chance", 0):
                        quantity = loot_info.get("quantity", 1)
                        await services.add_item_to_character(primary_player_id, item_id, quantity)
                loot_table = services.get_loot_table(loot_table_ref)
                for item_id, loot_info in loot_table.items():
                    if random.random() < loot_info.get("chance", 0):
                        quantity = loot_info.get("quantity", 1)
                        # --- END MODIFIED ---
                        services.add_item_to_character(primary_player_id, item_id, quantity)
                        log.append(f"The {template_id} dropped {item_id} (x{quantity})!")

                # TODO: Add XP rewards

            except Exception as e:
                logger.exception(f"Failed to grant loot for {p.actor_id}: {e}")

# --- Combat Logic Helpers ---
def _find_spawn_points(map_data: List[List[int]], num_points: int) -> List[List[int]]:
    # ... (this function is unchanged) ...
    if not map_data:
        logger.warning("Map data is empty, cannot find spawn points.")
        return [[5, 5]] * num_points
    valid_spawns = []
    height = len(map_data)
    width = len(map_data[0]) if height > 0 else 0
    for y in range(height):
        for x in range(width):
            tile_id = map_data[y][x]
            if tile_id in [0, 3]: # 0=Grass, 3=Stone Floor
                valid_spawns.append([x, y])
    if not valid_spawns:
        logger.warning("No valid spawn tiles found on map. Falling back to default.")
        return [[5, 5]] * num_points
    random.shuffle(valid_spawns)
    return [valid_spawns[i % len(valid_spawns)] for i in range(num_points)]

def _extract_initiative_stats(stats_dict: Dict) -> Dict:
    # This function is now correct based on our previous fix
    # ... (this function is unchanged) ...
    return {
        "endurance": stats_dict.get("Endurance", 10),
        "reflexes": stats_dict.get("Reflexes", 10),
        "fortitude": stats_dict.get("Fortitude", 10),
        "logic": stats_dict.get("Logic", 10),
        "intuition": stats_dict.get("Intuition", 10),
        "willpower": stats_dict.get("Willpower", 10),
    }

async def start_combat(db: Session, start_request: schemas.CombatStartRequest) -> models.CombatEncounter:
    # ... (this function is unchanged) ...
    logger.info(f"Starting combat at location {start_request.location_id}")
    participants_data: List[Tuple[str, str, int]] = []
    spawned_npc_details: List[Dict] = []
    spawn_points = []
    try:
        location_context = await services.get_world_location_context(start_request.location_id)
def start_combat(db: Session, start_request: schemas.CombatStartRequest) -> models.CombatEncounter:
    logger.info(f"Starting combat at location {start_request.location_id}")
    participants_data: List[Tuple[str, str, int]] = []
    spawned_npc_details: List[Dict] = []

    spawn_points = []
    try:
        location_context = services.get_world_location_context(start_request.location_id)
        map_data = location_context.get("generated_map_data")
        num_npcs = len(start_request.npc_template_ids)
        spawn_points = _find_spawn_points(map_data, num_npcs)
    except Exception as e:
        logger.exception(f"Error finding spawn points: {e}.")
        spawn_points = [[5, 5]] * len(start_request.npc_template_ids)

    for i, template_id in enumerate(start_request.npc_template_ids):
        try:
            coords = spawn_points[i]
            template_lookup = services.get_npc_generation_params(template_id)
            generation_params = template_lookup.get("generation_params")
            if not generation_params: continue

        # --- Use spawn_points from map if available ---
        map_spawn_points = location_context.get("spawn_points", {}).get("enemy")
        if map_spawn_points and len(map_spawn_points) >= num_npcs:
            random.shuffle(map_spawn_points)
            spawn_points = map_spawn_points[:num_npcs]
            logger.info(f"Using pre-defined spawn points from map: {spawn_points}")
        else:
            logger.warning("Not enough pre-defined spawn points, generating new ones.")
            spawn_points = _find_spawn_points(map_data, num_npcs)

    except Exception as e:
        logger.exception(f"Error finding spawn points: {e}.")
        spawn_points = [[5, 5]] * len(start_request.npc_template_ids)
    for i, template_id in enumerate(start_request.npc_template_ids):
        try:
            coords = spawn_points[i]
            template_lookup = await services.get_npc_generation_params(template_id)
            generation_params = template_lookup.get("generation_params")
            if not generation_params: continue
            full_npc_template = await services.generate_npc_template(generation_params)
            template_lookup = services.get_npc_generation_params(template_id)
            generation_params = template_lookup.get("generation_params")
            if not generation_params:
                logger.error(f"No generation_params found for template_id: {template_id}")
                continue

            full_npc_template = services.generate_npc_template(generation_params)

            npc_max_hp = full_npc_template.get("max_hp", 10)
            npc_abilities = full_npc_template.get("abilities", []) # Get abilities

            spawn_data = schemas.OrchestrationSpawnNpc(
                template_id=template_id,
                location_id=start_request.location_id,
                coordinates=coords,
                current_hp=npc_max_hp,
                max_hp=npc_max_hp,
                behavior_tags=full_npc_template.get("behavior_tags", ["aggressive"]),
                abilities=npc_abilities
            )
            npc_instance_data = services.spawn_npc_in_world(spawn_data)
            )
            npc_instance_data = await services.spawn_npc_in_world(spawn_data)
            npc_instance_data = services.spawn_npc_in_world(spawn_data)

            # --- MANUALLY ADD ABILITIES ---
            try:
                services.world_api.update_npc_state(npc_instance_data['id'], {"abilities": npc_abilities})
                logger.info(f"Manually added abilities {npc_abilities} to NPC {npc_instance_data['id']}")
            except Exception as e_abil:
                logger.error(f"Failed to manually add abilities to NPC: {e_abil}")
            # --- END FIX ---

            spawned_npc_details.append(npc_instance_data)
        except Exception as e:
            logger.exception(f"Unexpected error spawning NPC template '{template_id}': {e}")
            continue

    for player_id_str in start_request.player_ids:
        try:
            if not isinstance(player_id_str, str) or not player_id_str.startswith("player_"):
                continue
            char_context = services.get_character_context(player_id_str)
            player_stats = char_context.get("stats", {})
            stats_for_init = _extract_initiative_stats(player_stats)
            init_result = services.roll_initiative(**stats_for_init)
            char_context = await services.get_character_context(player_id_str)
            char_context = services.get_character_context(player_id_str)
            player_stats = char_context.get("stats", {})
            stats_for_init = _extract_initiative_stats(player_stats)
            init_result = await services.roll_initiative(**stats_for_init)
            initiative_total = init_result.get("total_initiative", 0)
            participants_data.append((player_id_str, "player", initiative_total))
        except Exception as e:
            logger.exception(f"Unexpected error processing Player {player_id_str}: {e}")
            participants_data.append((player_id_str, "player", 0))

    for npc_data in spawned_npc_details:
        actor_id_str = f"npc_{npc_data.get('id')}"
        try:
            # We already have the full template from spawn, no need to regen
    for npc_data in spawned_npc_details:
        actor_id_str = f"npc_{npc_data.get('id')}"
        try:
            npc_context = await services.get_npc_context(npc_data.get('id'))
            npc_context = services.get_npc_context(npc_data.get('id'))
            template_id = npc_context.get("template_id", "")
            if not template_id:
                npc_stats = {}
            else:
                template_lookup = services.get_npc_generation_params(template_id)
                generation_params = template_lookup.get("generation_params")
                full_npc_template = services.generate_npc_template(generation_params)
                npc_stats = full_npc_template.get("stats", {})

            stats_for_init = _extract_initiative_stats(npc_stats)
            init_result = services.roll_initiative(**stats_for_init)
                template_lookup = await services.get_npc_generation_params(template_id)
                generation_params = template_lookup.get("generation_params")
                full_npc_template = await services.generate_npc_template(generation_params)
                npc_stats = full_npc_template.get("stats", {})
                if not generation_params:
                    logger.error(f"No generation_params found for NPC {template_id} during init roll.")
                    npc_stats = {}
                else:
                    full_npc_template = services.generate_npc_template(generation_params)
                    npc_stats = full_npc_template.get("stats", {})

            stats_for_init = _extract_initiative_stats(npc_stats)
            init_result = await services.roll_initiative(**stats_for_init)
            initiative_total = init_result.get("total_initiative", 0)
            participants_data.append((actor_id_str, "npc", initiative_total))
        except Exception as e:
            logger.exception(f"Unexpected error processing NPC {npc_data.get('id')}: {e}")
            participants_data.append((actor_id_str, "npc", 0))

    if not participants_data:
        raise HTTPException(status_code=400, detail="Cannot start combat: No valid participants found.")

    participants_data.sort(key=lambda x: x[2], reverse=True)
    turn_order = [p[0] for p in participants_data]

    db_combat = crud.create_combat_encounter(db, location_id=start_request.location_id, turn_order=turn_order)
    for actor_id, actor_type, initiative in participants_data:
        crud.create_combat_participant(db, combat_id=db_combat.id, actor_id=actor_id, actor_type=actor_type, initiative=initiative)

    db.refresh(db_combat)
    return db_combat

    if not participants_data:
        raise HTTPException(status_code=400, detail="Cannot start combat: No valid participants found.")
    participants_data.sort(key=lambda x: x[2], reverse=True)
    turn_order = [p[0] for p in participants_data]
    db_combat = crud.create_combat_encounter(db, location_id=start_request.location_id, turn_order=turn_order)
    for actor_id, actor_type, initiative in participants_data:
        crud.create_combat_participant(db, combat_id=db_combat.id, actor_id=actor_id, actor_type=actor_type, initiative=initiative)
    db.refresh(db_combat)
    return db_combat

async def get_actor_context(actor_id: str) -> Tuple[str, Dict]:
    # ... (this function is unchanged) ...
    logger.debug(f"Getting context for actor: {actor_id}")
    if actor_id.startswith("player_"):
        try:
            context_data = await services.get_character_context(actor_id)
def get_actor_context(actor_id: str) -> Tuple[str, Dict]:
    logger.debug(f"Getting context for actor: {actor_id}")
    if actor_id.startswith("player_"):
        try:
            context_data = services.get_character_context(actor_id)
            return "player", context_data
        except HTTPException as e:
            raise e
    elif actor_id.startswith("npc_"):
        try:
            npc_instance_id = int(actor_id.split("_")[1])
            context_data = await services.get_npc_context(npc_instance_id)
            context_data = services.get_npc_context(npc_instance_id)
            return "npc", context_data
        except (IndexError, ValueError):
            raise HTTPException(status_code=400, detail=f"Invalid NPC actor ID format: {actor_id}")
        except HTTPException as e:
            raise e
    else:
        raise HTTPException(status_code=400, detail=f"Unknown actor ID format: {actor_id}")

def get_stat_score(actor_context: Dict, stat_name: str) -> int:
    # ... (this function is unchanged) ...
    stats = actor_context.get("stats", {})
    return stats.get(stat_name, 10)

def get_skill_rank(actor_context: Dict, skill_name: str) -> int:
    # ... (this function is unchanged) ...
    skills = actor_context.get("skills", {})
    skill_data = skills.get(skill_name)
    if isinstance(skill_data, dict):
        return skill_data.get("rank", 0)
    elif isinstance(skill_data, int):
        return skill_data
    return 0

async def get_equipped_weapon(actor_context: Dict) -> Tuple[Optional[str], Optional[str]]:
    # ... (this function is unchanged) ...
def get_equipped_weapon(actor_context: Dict) -> Tuple[Optional[str], Optional[str]]:
    actor_name = actor_context.get('name', actor_context.get('template_id', 'Unknown Actor'))
    equipment = actor_context.get("equipment")
    if equipment is not None: # Player
        weapon_item_id = equipment.get("weapon")
        if weapon_item_id:
            try:
                item_template = await services.get_item_template_params(weapon_item_id)
                item_template = services.get_item_template_params(weapon_item_id)
                category = item_template.get("category")
                item_type = item_template.get("type")
                if category and item_type in ("melee", "ranged"):
                    return category, item_type
                else:
                    return "Unarmed/Fist Weapons", "melee"
            except Exception as e:
                logger.error(f"Failed to get item template for {weapon_item_id}. Error: {e}.")
                return "Unarmed/Fist Weapons", "melee"
        else:
            return "Unarmed/Fist Weapons", "melee"
    else: # NPC
        npc_skills = actor_context.get("skills", {})
        if npc_skills.get("Great Weapons", 0) > 0: return "Great Weapons", "melee"
        if npc_skills.get("Bows and Firearms", 0) > 0: return "Bows and Firearms", "ranged"
        return "Unarmed/Fist Weapons", "melee"

async def get_equipped_armor(actor_context: Dict) -> Optional[str]:
    # ... (this function is unchanged) ...
def get_equipped_armor(actor_context: Dict) -> Optional[str]:
    actor_name = actor_context.get('name', actor_context.get('template_id', 'Unknown Actor'))
    equipment = actor_context.get("equipment")
    if equipment is not None: # Player
        armor_item_id = equipment.get("armor")
        if armor_item_id:
            try:
                item_template = await services.get_item_template_params(armor_item_id)
                item_template = services.get_item_template_params(armor_item_id)
                category = item_template.get("category")
                item_type = item_template.get("type")
                if category and item_type == "armor":
                    return category
                else:
                    return "Natural/Unarmored"
            except Exception as e:
                logger.error(f"Failed to get item template for {armor_item_id}. Error: {e}.")
                return "Natural/Unarmored"
        else:
            return "Natural/Unarmored"
    else: # NPC
        npc_skills = actor_context.get("skills", {})
        if npc_skills.get("Plate Armor", 0) > 0: return "Plate Armor"
        elif npc_skills.get("Clothing/Utility", 0) > 0: return "Clothing/Utility"
        return "Natural/Unarmored"

async def check_combat_end_condition(db: Session, combat: models.CombatEncounter, log: List[str]) -> bool:
def check_combat_end_condition(db: Session, combat: models.CombatEncounter, log: List[str]) -> bool:
    """Checks if all NPCs or all Players are defeated."""
    players_alive, npcs_alive = False, False

    for p in combat.participants:
        try:
            actor_type, context = await get_actor_context(p.actor_id)
            actor_type, context = get_actor_context(p.actor_id)
            hp = context.get("current_hp", 0)
            if hp > 0:
                if actor_type == "player": players_alive = True
                elif actor_type == "npc": npcs_alive = True
        except HTTPException as e:
            logger.warning(f"Could not get context for {p.actor_id} during end check: {e.detail}.")

    if not players_alive or not npcs_alive:
        if not players_alive:
            end_status = "npcs_win"
            log.append("The party has been defeated!")
        else:
            end_status = "players_win"
            log.append("All enemies have been defeated!")
            # Grant rewards
            await _grant_combat_rewards(db, combat, log)
            _grant_combat_rewards(db, combat, log)

        combat.status = end_status
        db.commit()
        logger.info(f"Combat {combat.id} ended: {end_status}")
        return True
    return False

async def determine_npc_action(db: Session, combat: models.CombatEncounter, npc_actor_id: str) -> Optional[schemas.PlayerActionRequest]:
def determine_npc_action(db: Session, combat: models.CombatEncounter, npc_actor_id: str) -> Optional[schemas.PlayerActionRequest]:
    """
    Determines an NPC's action based on health, behavior tags, and abilities.
    """
    try:
        _, npc_context = await get_actor_context(npc_actor_id)
        _, npc_context = get_actor_context(npc_actor_id)
    except HTTPException:
        logger.error(f"Could not get context for NPC {npc_actor_id} to determine action.")
        return None

    # --- 1. Check for crippling status effects ---
    status_effects = npc_context.get("status_effects", [])
    if "Staggered" in status_effects:
        logger.info(f"NPC {npc_actor_id} is Staggered and skips its turn.")
        # --- FIXED: Called correct function ---
        await services.remove_status_from_npc(int(npc_actor_id.split('_')[1]), "Staggered")
        services.remove_status_from_npc(int(npc_actor_id.split('_')[1]), "Staggered")
        return None # Return None to signify a "wait" action

    # --- 2. Get AI parameters ---
    behavior_tags = npc_context.get("behavior_tags", [])
    npc_current_hp = npc_context.get("current_hp", 1)
    npc_max_hp = npc_context.get("max_hp", 1)
    npc_abilities = npc_context.get("abilities", []) # e.g., ["Minor Heal", "Nausea"]
    npc_abilities = npc_context.get("abilities", [])
    logger.debug(f"NPC {npc_actor_id} has abilities: {npc_abilities}")

    living_players = []
    for p in combat.participants:
        if p.actor_id.startswith("player_"):
            try:
                _, p_context = await get_actor_context(p.actor_id)
                _, p_context = get_actor_context(p.actor_id)
                if p_context.get("current_hp", 0) > 0:
                    living_players.append(p_context)
            except HTTPException:
                continue

    if not living_players:
        return None # No one to fight

    # --- 3. AI Decision Tree ---

    # 3a. Healing Logic
    if "Minor Heal" in npc_abilities and npc_current_hp < (npc_max_hp * 0.5):
        logger.info(f"NPC {npc_actor_id} is healing itself.")
        return schemas.PlayerActionRequest(
            action="use_ability",
            ability_id="Minor Heal", # Use the simple name
            target_id=npc_actor_id # Target self
        )

    # 3b. Cowardly Logic
    if "cowardly" in behavior_tags and npc_current_hp < (npc_max_hp * 0.3):
        logger.info(f"NPC {npc_actor_id} is cowardly and waiting.")
        return None # Wait

    # 3c. Target Selection
    target_player = None
    if "targets_weakest" in behavior_tags:
        living_players.sort(key=lambda p: p.get("current_hp", 999))
        target_player = living_players[0]
    else:
        # Default: aggressive
        target_player = random.choice(living_players)

    target_id = target_player['id']
    logger.info(f"NPC {npc_actor_id} is targeting {target_id}")

    # 3d. Ability Usage Logic
    if "Nausea" in npc_abilities and random.random() < 0.5: # 50% chance
        logger.info(f"NPC {npc_actor_id} uses Nausea on {target_id}")
        return schemas.PlayerActionRequest(
            action="use_ability",
            ability_id="Nausea",
            target_id=target_id
        )

    # 3e. Default Attack
    logger.info(f"NPC {npc_actor_id} uses default attack on {target_id}")
    return schemas.PlayerActionRequest(action="attack", target_id=target_id)

async def handle_no_action(db: Session, combat: models.CombatEncounter, actor_id: str, reason: str = "waits") -> schemas.PlayerActionResponse:
    """Handles a 'wait' action or a skipped turn."""
    log = [f"{actor_id} {reason}."]
    combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
    combat_over = await check_combat_end_condition(db, combat, log)
def handle_no_action(db: Session, combat: models.CombatEncounter, actor_id: str, reason: str = "waits") -> schemas.PlayerActionResponse:
    """Handles a 'wait' action or a skipped turn."""
    log = [f"{actor_id} {reason}."]
    combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
    combat_over = check_combat_end_condition(db, combat, log)
    db.commit()
    db.refresh(combat)

    return schemas.PlayerActionResponse(
        success=True,
        message=f"{actor_id} waited.",
        log=log,
        new_turn_index=combat.current_turn_index,
        combat_over=combat_over
    )

async def _handle_basic_attack(
# --- NEW: Dice Rolling Helper ---
def _roll_dice_string(dice_str: str) -> int:
    """Rolls dice based on a string like '1d8' or '2d6'."""
    try:
        if "d" in dice_str:
            num, die = map(int, dice_str.split('d'))
            return sum(random.randint(1, die) for _ in range(num))
        else:
            return int(dice_str)
    except Exception as e:
        logger.error(f"Failed to roll dice string '{dice_str}': {e}")
        return 0

# --- NEW: Ability Effect Handlers ---
# These are the small helper functions that execute our data-driven effects.

def _handle_effect_modify_attack(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict
) -> bool:
    log: List[str]) -> bool:
    """
    Performs the core attack roll, damage, and HP update logic.
    Returns True if the target was hit, False otherwise.
    """
    target_type = "player" if target_id.startswith("player_") else "npc"

    weapon_category, weapon_type = await get_equipped_weapon(attacker_context)
    armor_category = await get_equipped_armor(defender_context)

    weapon_data = await services.get_weapon_data(weapon_category, weapon_type)
    armor_data = await services.get_armor_data(armor_category) if armor_category else {"dr": 0, "skill_stat": "Reflexes", "skill": "Natural/Unarmored"}

    attack_params = {
        "attacker_attacking_stat_score": get_stat_score(attacker_context, weapon_data["skill_stat"]),
        "attacker_skill_rank": get_skill_rank(attacker_context, weapon_data["skill"]),
        "defender_armor_stat_score": get_stat_score(defender_context, armor_data["skill_stat"]),
        "defender_armor_skill_rank": get_skill_rank(defender_context, armor_data["skill"]),
        "attacker_attack_roll_bonus": 0,
        "attacker_attack_roll_penalty": 0,
        "defender_defense_roll_bonus": 0,
        "defender_defense_roll_penalty": 0,
        "defender_weapon_penalty": weapon_data.get("penalty", 0)
    }
    attack_result = await services.roll_contested_attack(attack_params)
    log.append(f"Attack Roll: Attacker ({attack_result['attacker_final_total']}) vs Defender ({attack_result['defender_final_total']}). Margin: {attack_result['margin']}.")

    outcome = attack_result.get("outcome")
    if outcome in ["hit", "solid_hit", "critical_hit"]:
        log.append(f"Result: {actor_id} hits {target_id}!")

        # Apply status effects from hit
        if outcome == "solid_hit":
            await services.apply_status_to_target(target_id, "Staggered")
            log.append(f"{target_id} is Staggered!")
        elif outcome == "critical_hit":
            await services.apply_status_to_target(target_id, "Bleeding")
            log.append(f"{target_id} is Bleeding!")

        damage_params = {
            "base_damage_dice": weapon_data["damage"],
            "relevant_stat_score": get_stat_score(attacker_context, weapon_data["skill_stat"]),
            "attacker_damage_bonus": 0,
            "attacker_damage_penalty": 0,
            "attacker_dr_modifier": 0,
            "defender_base_dr": armor_data["dr"]
        }
        damage_result = await services.calculate_damage(damage_params)
        final_damage = damage_result.get("final_damage", 0)
        log.append(f"Damage: {final_damage}")

        if final_damage > 0:
            if target_type == "player":
                await services.apply_damage_to_character(target_id, final_damage)
            else:
                npc_instance_id = int(target_id.split("_")[1])
                new_hp = defender_context.get("current_hp", 0) - final_damage
                await services.apply_damage_to_npc(npc_instance_id, new_hp)
        return True
    else:
        log.append(f"Result: {actor_id} misses {target_id}.")
        return False

# --- Main Action Handler ---
async def handle_player_action(db: Session, combat: models.CombatEncounter, actor_id: str, action: schemas.PlayerActionRequest) -> schemas.PlayerActionResponse:
    log: List[str],
    effect: Dict) -> bool:
    """
    Handles abilities that modify a basic attack (e.g., "Concussive Strike").
    """
    return _handle_basic_attack(actor_id, target_id, attacker_context, defender_context, log, ability_mod=effect)

def _handle_effect_direct_damage(
    target_id: str,
    log: List[str],
    effect: Dict
) -> bool:
    effect: Dict) -> bool:
    """
    Handles effects that deal direct damage without an attack roll.
    """
    amount_str = effect.get("amount", "1d4")
    damage_type = effect.get("damage_type", "physical")
    damage_amount = _roll_dice_string(amount_str)

    log.append(f"A pulse of energy hits {target_id} for {damage_amount} {damage_type} damage!")

    if damage_amount > 0:
        if target_id.startswith("player_"):
            services.apply_damage_to_character(target_id, damage_amount)
        elif target_id.startswith("npc_"):
            try:
                _, defender_context = get_actor_context(target_id)
                npc_instance_id = int(target_id.split("_")[1])
                new_hp = defender_context.get("current_hp", 0) - damage_amount
                services.apply_damage_to_npc(npc_instance_id, new_hp)
            except Exception as e:
                log.append(f"Failed to apply direct damage to {target_id}: {e}")
                return False
    return True

def _handle_effect_heal(
    target_id: str,
    log: List[str],
    effect: Dict
) -> bool:
    effect: Dict) -> bool:
    """
    Handles effects that restore HP.
    """
    amount_str = effect.get("amount", "1d8")
    heal_amount = _roll_dice_string(amount_str)

    if target_id.startswith("player_"):
        services.apply_healing_to_character(target_id, heal_amount)
    elif target_id.startswith("npc_"):
        try:
            _, target_context = get_actor_context(target_id)
            npc_instance_id = int(target_id.split("_")[1])
            new_hp = min(
                target_context.get("current_hp", 0) + heal_amount,
                target_context.get("max_hp", 99)
            )
            services.apply_damage_to_npc(npc_instance_id, new_hp) # Use apply_damage to set HP
            services.world_api.update_npc_state(npc_instance_id, {"current_hp": new_hp})
        except Exception as e:
            log.append(f"Failed to apply heal to {target_id}: {e}")
            return False

    log.append(f"{target_id} is healed for {heal_amount} HP!")
    return True

def _handle_effect_apply_status(
    target_id: str,
    log: List[str],
    effect: Dict
) -> bool:
    effect: Dict) -> bool:
    """
    Handles effects that apply a status, no save.
    """
    status_id = effect.get("status_id")
    if not status_id:
        return False

    services.apply_status_to_target(target_id, status_id)
    log.append(f"{target_id} is now afflicted with {status_id}!")
    return True

def _handle_effect_apply_status_roll(
    target_id: str,
    log: List[str],
    effect: Dict
) -> bool:
    effect: Dict) -> bool:
    """
    Handles effects that apply a status, WITH a save.
    """
    status_id = effect.get("status_id")
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 12)

    if not status_id or not save_stat:
        return False

    # Get target's save modifier
    _, target_context = get_actor_context(target_id)
    stat_score = get_stat_score(target_context, save_stat)
    # --- FIXED: Called correct function from imported rules_core ---
    stat_mod = rules_core.calculate_modifier(stat_score)

    # Make the roll
    roll = random.randint(1, 20)
    total = roll + stat_mod

    if total >= dc:
        log.append(f"{target_id} rolled {total} (d20={roll} + mod={stat_mod}) and SAVED against {status_id} (DC {dc})!")
        return False
    else:
        log.append(f"{target_id} rolled {total} (d20={roll} + mod={stat_mod}) and FAILED to save against {status_id} (DC {dc})!")
        services.apply_status_to_target(target_id, status_id)
        return True

def _handle_effect_move_target(
    target_id: str,
    log: List[str],
    effect: Dict
) -> bool:
def _handle_effect_move_target_roll(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """
    Handles effects that move a target, WITH a save.
    (e.g., Force T1: Minor Shove)
    """
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 12) # Default DC if not specified
    contest = effect.get("contest") # e.g., "user"

    # This is a complex effect. For now, let's just implement the DC-based save.
    # A "contest" would require the attacker's context.

    if contest == "user":
        log.append(f"Contested roll not yet implemented. Using DC {dc} as fallback.")

    # Get target's save modifier
    _, target_context = get_actor_context(target_id)
    stat_score = get_stat_score(target_context, save_stat)
    stat_mod = rules_core.calculate_modifier(stat_score)

    # Make the roll
    roll = random.randint(1, 20)
    total = roll + stat_mod

    if total >= dc:
        log.append(f"{target_id} rolled {total} (d20={roll} + mod={stat_mod}) and resisted the push (DC {dc})!")
        return False
    else:
        log.append(f"{target_id} rolled {total} (d20={roll} + mod={stat_mod}) and FAILED to resist (DC {dc})!")
        # Save failed, call the simple move handler
        return _handle_effect_move_target(target_id, log, effect)

def _handle_effect_move_target(
    target_id: str,
    log: List[str],
    effect: Dict) -> bool:
    """
    Handles effects that move a target (e.g., "Minor Shove").
    """
    if target_id.startswith("npc_"):
        try:
            distance = effect.get("distance", 1)
            npc_instance_id = int(target_id.split('_')[1])
            _, defender_context = get_actor_context(target_id)
            current_coords = defender_context.get("coordinates", [1, 1])

            # Simple push "north" (increase Y)
            new_coords = [current_coords[0], current_coords[1] + distance]

            # TODO: Add check for map bounds and impassable tiles

            # --- FIXED: Called correct function via services.world_api ---
            services.world_api.update_npc_state(npc_instance_id, {"coordinates": new_coords})
            log.append(f"{target_id} is pushed {distance}m to {new_coords}!")
            return True
        except Exception as e:
            log.append(f"Failed to move target: {e}")
            return False
    else:
        log.append(f"Cannot move {target_id} (only NPCs can be moved).")
        return False

# This is the "router" that maps `effect["type"]` to the functions above
ABILITY_EFFECT_HANDLERS: Dict[str, Callable] = {
# --- IMPLEMENTED T2 STUB ---
def _handle_effect_move_self(
    actor_id: str,
    target_id: str, # Unused, but passed for consistency
    attacker_context: Dict,
    defender_context: Dict, # Unused
    log: List[str],
    effect: Dict) -> bool:
    """
    Handles effects that move the caster. (e.g., Force T2: Repel Step)
    """
    distance = effect.get("distance", 2)

    # Simple "repel" = move north (increase Y)
    # TODO: Add logic to let player choose direction

    try:
        if actor_id.startswith("player_"):
            loc_id = attacker_context.get("current_location_id")
            current_coords = [attacker_context.get("position_x"), attacker_context.get("position_y")]
            new_coords = [current_coords[0], current_coords[1] + distance]

            # TODO: Check map bounds/passable

            services.character_api.update_character_location(actor_id, loc_id, new_coords)
            log.append(f"{actor_id} repels themselves {distance}m to {new_coords}!")

        elif actor_id.startswith("npc_"):
            npc_instance_id = int(actor_id.split('_')[1])
            current_coords = attacker_context.get("coordinates", [1, 1])
            new_coords = [current_coords[0], current_coords[1] + distance]

            # TODO: Check map bounds/passable

            services.world_api.update_npc_state(npc_instance_id, {"coordinates": new_coords})
            log.append(f"{actor_id} repels themselves {distance}m to {new_coords}!")

        return True
    except Exception as e:
        log.append(f"Failed to move self: {e}")
        return False
# --- END IMPLEMENTED T2 STUB ---

def _handle_effect_reaction_damage(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """
    Handles effects that trigger as a reaction. (e.g., Bastion T2: Spiked Deflection)
    """
    log.append(f"Reaction ability '{effect.get('trigger')}' not yet implemented.")
    # TODO: Implement reaction system
    return True

def _handle_effect_reaction_move_ally(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """
    Handles effects that move an ally as a reaction. (e.g., Grace T2: Pull Aside)
    """
    log.append(f"Reaction ability '{effect.get('trigger')}' not yet implemented.")
    # TODO: Implement reaction system
    return True

def _handle_effect_create_trap(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """
    Handles effects that create a trap. (e.g., Cunning T2: Alarm Snare)
    """
    effect_id = effect.get("effect_id", "generic_trap")
    log.append(f"{actor_id} places a trap: {effect_id}!")
    # TODO: Implement trap creation in world_pkg
    return True

def _handle_effect_aoe_damage(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """
    Handles effects that deal AoE damage. (e.g., Evocation T2: Elemental Cascade)
    """
    damage = effect.get("damage", "1d8")
    shape = effect.get("shape", "line")
    log.append(f"{actor_id} unleashes an AoE {shape} for {damage} damage!")
    # TODO: Implement AoE targeting and apply damage to all targets
    return True

def _handle_effect_random_status(
    target_id: str,
    log: List[str],
    effect: Dict) -> bool:
    """
    Handles effects that apply a random status. (e.g., Chaos T2: Unstable Bolt)
    """
    status_list = effect.get("status_list", [])
    if not status_list:
        return False
    status_id = random.choice(status_list)
    services.apply_status_to_target(target_id, status_id)
    log.append(f"{target_id} is afflicted with a random status: {status_id}!")
    return True

def _handle_effect_special_move(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """
    Handles special, named moves. (e.g., Psionics T2: Push Object)
    """
    effect_id = effect.get("effect_id", "unknown_move")
    log.append(f"Performing special move: {effect_id}!")
    # TODO: Implement logic for specific named moves
    return True

# --- END NEW T2 STUBS ---

# This is the "router" that maps `effect["type"]` to the functions above
ABILITY_EFFECT_HANDLERS: Dict[str, Callable] = {
    # T1 Handlers
    "modify_attack": _handle_effect_modify_attack,
    "direct_damage": _handle_effect_direct_damage,
    "heal": _handle_effect_heal,
    "apply_status": _handle_effect_apply_status,
    "apply_status_roll": _handle_effect_apply_status_roll,
    "move_target": _handle_effect_move_target,
    # TODO: Add handlers for all 53 effect types
    "move_target": _handle_effect_move_target, # T1 Spirit (Bad Juju) uses this

    # --- ADDED T2 Handlers ---
    "move_self": _handle_effect_move_self,
    "reaction_damage": _handle_effect_reaction_damage,
    "reaction_move_ally": _handle_effect_reaction_move_ally,
    "create_trap": _handle_effect_create_trap,
    "aoe_damage": _handle_effect_aoe_damage,
    "move_target_roll": _handle_effect_move_target_roll, # T1 Force (Minor Shove) uses this
    "random_status": _handle_effect_random_status,
    "special_move": _handle_effect_special_move,
    # --- END ADD ---
}

# --- Main Attack Handler ---
def _handle_basic_attack(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    ability_mod: Optional[Dict] = None
) -> bool:
    ability_mod: Optional[Dict] = None) -> bool:
    """
    Performs the core attack roll, damage, and HP update logic.
    Returns True if the target was hit, False otherwise.
    """
    ability_mod = ability_mod or {}
    target_type = "player" if target_id.startswith("player_") else "npc"

    weapon_category, weapon_type = get_equipped_weapon(attacker_context)
    armor_category = get_equipped_armor(defender_context)

    weapon_data = services.get_weapon_data(weapon_category, weapon_type)
    armor_data = services.get_armor_data(armor_category) if armor_category else {"dr": 0, "skill_stat": "Reflexes", "skill": "Natural/Unarmored"}

    attack_params = {
        "attacker_attacking_stat_score": get_stat_score(attacker_context, weapon_data["skill_stat"]),
        "attacker_skill_rank": get_skill_rank(attacker_context, weapon_data["skill"]),
        "defender_armor_stat_score": get_stat_score(defender_context, armor_data["skill_stat"]),
        "defender_armor_skill_rank": get_skill_rank(defender_context, armor_data["skill"]),
        "attacker_attack_roll_bonus": 0,
        "attacker_attack_roll_penalty": 0,
        "defender_defense_roll_bonus": 0,
        "defender_defense_roll_penalty": 0,
        "defender_weapon_penalty": weapon_data.get("penalty", 0)
    }

    # Check for Nausea status
    if "Nausea" in attacker_context.get("status_effects", []):
        log.append(f"{actor_id} is Nauseous, attack is penalized!")
        attack_params["attacker_attack_roll_penalty"] += 2 # Add penalty

    attack_result = services.roll_contested_attack(attack_params)
    log.append(f"Attack Roll: Attacker ({attack_result['attacker_final_total']}) vs Defender ({attack_result['defender_final_total']}). Margin: {attack_result['margin']}.")

    outcome = attack_result.get("outcome")
    if outcome in ["hit", "solid_hit", "critical_hit"]:
        log.append(f"Result: {actor_id} hits {target_id}!")

        # Apply status effects from hit
        if outcome == "solid_hit":
            services.apply_status_to_target(target_id, "Staggered")
            log.append(f"{target_id} is Staggered!")
        elif outcome == "critical_hit":
            services.apply_status_to_target(target_id, "Bleeding")
            log.append(f"{target_id} is Bleeding!")

        # Check for damage boost from ability
        damage_bonus = 0
        if ability_mod.get("damage_boost"):
            damage_bonus = _roll_dice_string(ability_mod["damage_boost"])
            log.append(f"Ability adds +{damage_bonus} damage!")

        damage_params = {
            "base_damage_dice": weapon_data["damage"],
            "relevant_stat_score": get_stat_score(attacker_context, weapon_data["skill_stat"]),
            "attacker_damage_bonus": damage_bonus, # Pass in the bonus
            "attacker_damage_penalty": 0,
            "attacker_dr_modifier": 0,
            "defender_base_dr": armor_data["dr"]
        }
        damage_result = services.calculate_damage(damage_params)
        final_damage = damage_result.get("final_damage", 0)
        log.append(f"Damage: {final_damage}")

        if final_damage > 0:
            if target_type == "player":
                services.apply_damage_to_character(target_id, final_damage)
            else:
                npc_instance_id = int(target_id.split("_")[1])
                new_hp = defender_context.get("current_hp", 0) - final_damage
                services.apply_damage_to_npc(npc_instance_id, new_hp)
        return True
    else:
        log.append(f"Result: {actor_id} misses {target_id}.")
        return False

# --- Main Action Handler ---
def handle_player_action(db: Session, combat: models.CombatEncounter, actor_id: str, action: schemas.PlayerActionRequest) -> schemas.PlayerActionResponse:
    log = []

    # 1. Check actor's turn
    current_actor_id = combat.turn_order[combat.current_turn_index]
    if actor_id != current_actor_id:
        raise HTTPException(status_code=403, detail=f"It is not {actor_id}'s turn.")

    # 2. Get actor context and check for turn-skipping status effects
    try:
        actor_type, attacker_context = await get_actor_context(actor_id)
        actor_type, attacker_context = get_actor_context(actor_id)
        status_effects = attacker_context.get("status_effects", [])

        if "Staggered" in status_effects:
            log.append(f"{actor_id} is Staggered and loses their turn!")
            # --- FIXED: Check actor_type and call correct function ---
            if actor_type == "player":
            if actor_type == "player":
                await services.remove_status_from_character(actor_id, "Staggered")
            else:
                await services.remove_status_from_npc(int(actor_id.split('_')[1]), "Staggered")
            return await handle_no_action(db, combat, actor_id, reason="is Staggered")

    except HTTPException as he:
        return await handle_no_action(db, combat, actor_id, reason=f"could not be found ({he.detail})")
                services.remove_status_from_character(actor_id, "Staggered")
            else:
                services.remove_status_from_npc(int(actor_id.split('_')[1]), "Staggered")
            return handle_no_action(db, combat, actor_id, reason="is Staggered")

    except HTTPException as he:
        return handle_no_action(db, combat, actor_id, reason=f"could not be found ({he.detail})")

    # 3. Handle "wait" action
    if action.action == "wait":
        return handle_no_action(db, combat, actor_id)
        return await handle_no_action(db, combat, actor_id)

    # 4. Handle actions that require a target
    target_id = action.target_id
    if not target_id:
        log.append(f"Action '{action.action}' requires a target, but none provided. Waiting instead.")
        return await handle_no_action(db, combat, actor_id)

    try:
        target_type, defender_context = await get_actor_context(target_id)
        hp = defender_context.get("current_hp", 0)
        if hp <= 0:
            raise HTTPException(status_code=400, detail=f"Target {target_id} is already defeated.")
        return handle_no_action(db, combat, actor_id)

    try:
        target_type, defender_context = get_actor_context(target_id)
        hp = defender_context.get("current_hp", 0)
        # Allow targeting self/allies even if "dead" for heals
        if hp <= 0 and target_type == "npc":
            raise HTTPException(status_code=400, detail=f"Target {target_id} is already defeated.")
             raise HTTPException(status_code=400, detail=f"Target {target_id} is already defeated.")

        # --- 5. Route Action ---

        if action.action == "attack":
            log.append(f"{actor_id} targets {target_id} with an attack.")
            await _handle_basic_attack(actor_id, target_id, attacker_context, defender_context, log)

        elif action.action == "use_ability":
            ability_data = await services.get_ability_data(action.ability_id)
            if not ability_data:
                log.append(f"Ability '{action.ability_id}' not found in rules data.")
                return await handle_no_action(db, combat, actor_id, reason=f"unknown ability {action.ability_id}")

            log.append(f"{actor_id} uses ability: {ability_data.get('name')} on {target_id}!")

            for effect in ability_data.get("effects", []):
                effect_type = effect.get("type")
                if effect_type == "apply_status":
                    await services.apply_status_to_target(target_id, effect.get("status_id"))
                    log.append(f"{target_id} is now {effect.get('status_id')}!")
                elif effect_type == "apply_status_roll":
                    # For now, assume the roll passes
                    await services.apply_status_to_target(target_id, effect.get("status_id"))
                    log.append(f"{target_id} is now {effect.get('status_id')}!")
                elif effect_type == "heal":
                    amount = effect.get("amount", "1d8")
                    heal_amount = 10 if "d" in amount else int(amount)
                    if target_id.startswith("player_"):
                        await services.apply_healing_to_character(target_id, heal_amount)
                    else:
                        # TODO: Add healing for NPCs
                        pass
                    log.append(f"{actor_id} heals {target_id} for {heal_amount} HP.")
                elif effect_type == "damage":
                    amount = effect.get("amount", "1d6")
                    damage_amount = 8  # Placeholder
                    if target_id.startswith("player_"):
                        await services.apply_damage_to_character(target_id, damage_amount)
                    else:
                        npc_id = int(target_id.split("_")[1])
                        new_hp = defender_context.get("current_hp", 0) - damage_amount
                        await services.apply_damage_to_npc(npc_id, new_hp)
                    log.append(f"{actor_id} deals {damage_amount} damage to {target_id}.")
                elif effect_type == "move_target":
                    distance = effect.get("distance", 1)
                    if target_id.startswith("npc_"):
                        npc_id = int(target_id.split("_")[1])
                        current_coords = defender_context.get("coordinates", [1, 1])
                        new_coords = [current_coords[0], current_coords[1] + distance] # Simple push
                        await services.update_npc_state(npc_id, {"coordinates": new_coords})
                        log.append(f"{target_id} is pushed {distance}m to {new_coords}!")
                elif effect_type == "modify_attack":
                    log.append("This ability modifies the next attack. The effect will be applied then.")
                    # TODO: Implement a way to store and apply attack modifications
                    pass
                else:
                    log.append(f"Effect type '{effect_type}' is not yet implemented.")

        elif action.action == "use_item":
            log.append(f"{actor_id} uses item: {action.item_id} on {target_id}!")
            try:
                item_template = await services.get_item_template_params(action.item_id)
                if item_template.get("type") == "healing":
                    healing_amount = item_template.get("potency", 15)

                    if target_id.startswith("player_"):
                        await services.apply_healing_to_character(target_id, healing_amount)
                    elif target_id.startswith("npc_"):
                        # TODO: Add NPC healing logic
                        pass
                    log.append(f"{actor_id} heals {target_id} for {healing_amount} HP.")

                    # Consume item
                    await services.remove_item_from_character(actor_id, action.item_id, 1)
                else:
            _handle_basic_attack(actor_id, target_id, attacker_context, defender_context, log)

        elif action.action == "use_ability":
            ability_name = action.ability_id
            log.append(f"{actor_id} uses ability: {ability_name} on {target_id}!")

            ability_data = services.get_ability_data(ability_name)
            if not ability_data:
                log.append(f"Unknown ability: {ability_name}. Action failed.")
            else:
                # --- RESOURCE COST ---
                cost = ability_data.get("cost")
                if cost:
                    # TODO: Add resource check logic
                    log.append(f"Paid {cost['amount']} {cost['resource']}.")

                # --- PROCESS EFFECTS ---
                for effect in ability_data.get("effects", []):
                    effect_type = effect.get("type")
                    handler = ABILITY_EFFECT_HANDLERS.get(effect_type)

                    if handler:
                        try:
                            if effect_type == "modify_attack":
                                handler(actor_id, target_id, attacker_context, defender_context, log, effect)
                            else:
                            # --- Pass correct context to handlers ---
                            if effect_type in ("modify_attack", "special_move", "create_trap", "move_self", "reaction_damage", "reaction_move_ally", "aoe_damage", "move_target_roll"):
                                # Handlers that need the actor's context
                                handler(actor_id, target_id, attacker_context, defender_context, log, effect)
                            else:
                                # Handlers that only need the target's context
                                handler(target_id, log, effect)
                        except Exception as e:
                            log.append(f"Effect {effect_type} failed: {e}")
                    else:
                        log.append(f"Effect type '{effect_type}' is not implemented.")

        elif action.action == "use_item":
            log.append(f"{actor_id} uses item: {action.item_id} on {target_id}!")
            try:
                item_template = services.get_item_template_params(action.item_id)
                if item_template.get("type") == "healing":
                    healing_amount = item_template.get("potency", 15)

                    if target_id.startswith("player_"):
                        services.apply_healing_to_character(target_id, healing_amount)
                    elif target_id.startswith("npc_"):
                        _, target_context = get_actor_context(target_id)
                        npc_instance_id = int(target_id.split("_")[1])
                        new_hp = min(
                            target_context.get("current_hp", 0) + healing_amount,
                            target_context.get("max_hp", 99)
                        )
                        services.apply_damage_to_npc(npc_instance_id, new_hp)
                        services.world_api.update_npc_state(npc_instance_id, {"current_hp": new_hp})

                    log.append(f"{actor_id} heals {target_id} for {healing_amount} HP.")

                    # Consume item
                    if actor_type == "player":
                        services.remove_item_from_character(actor_id, action.item_id, 1)
                else:
                    log.append(f"Item {action.item_id} has no combat effect.")
            except Exception as e:
                log.append(f"Could not use item: {e}")

        else:
            log.append(f"Action '{action.action}' not fully implemented. Waiting instead.")
            return await handle_no_action(db, combat, actor_id)

        # --- 6. Advance Turn and Check End Condition ---
        combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
        combat_over = await check_combat_end_condition(db, combat, log) # Also sync
            return handle_no_action(db, combat, actor_id)

        # --- 6. Advance Turn and Check End Condition ---
        combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
        combat_over = check_combat_end_condition(db, combat, log) # Also sync
        db.commit()
        db.refresh(combat)

        return schemas.PlayerActionResponse(
            success=True,
            message=f"{actor_id} performed {action.action}.",
            log=log,
            new_turn_index=combat.current_turn_index,
            combat_over=combat_over
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(f"Unexpected error in handle_player_action for {actor_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")