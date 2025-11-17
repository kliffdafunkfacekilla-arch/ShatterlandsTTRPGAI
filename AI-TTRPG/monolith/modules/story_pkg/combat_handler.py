# AI-TTRPG/monolith/modules/story_pkg/combat_handler.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
import httpx
from typing import List, Dict, Any, Tuple, Optional, Callable
from . import crud, models, schemas, services
# --- MODIFIED/ADDED IMPORTS ---
from ..rules_pkg import core as rules_core
from ..story_pkg import database as story_db
# --- END MODIFIED/ADDED IMPORTS ---
import random
import re
import logging

logger = logging.getLogger("monolith.story.combat")

# ----------------------------------------------------
# --- NEW CORE MOVEMENT AND AOE HELPERS (REQUIRED) ---
# ----------------------------------------------------

def _get_map_dimensions_and_data(location_id: int) -> Tuple[int, int, List[List[int]], List[str]]:
    """Retrieves map dimensions and tile data, raising error if map is invalid."""
    location_context = services.get_world_location_context(location_id)
    map_data = location_context.get("generated_map_data", [])

    if not map_data or not isinstance(map_data, list) or not map_data[0]:
        raise RuntimeError("Map data is unavailable for boundary checks.")

    height = len(map_data)
    width = len(map_data[0])

    # Impassable tile IDs based on tile_definitions.json (1=Tree, 2=Water, 4=Stone Wall, 5=Door Closed)
    impassable_ids = [1, 2, 4, 5]

    return width, height, map_data, impassable_ids

def _is_passable_and_in_bounds(loc_id: int, x: int, y: int, log: List[str]) -> bool:
    """Checks if new coordinates are within map boundaries and on a passable tile."""
    try:
        width, height, map_data, impassable_ids = _get_map_dimensions_and_data(loc_id)
    except RuntimeError as e:
        log.append(f"Error: Map check failed ({e})")
        return False

    if not (0 <= x < width and 0 <= y < height):
        log.append(f"Movement failed: Coordinates ({x}, {y}) are out of bounds.")
        return False

    # Note: Map data is indexed [row][col], which is [y][x]
    tile_id = map_data[y][x]
    if tile_id in impassable_ids:
        log.append(f"Movement failed: Tile ({x}, {y}) is impassable (Tile ID: {tile_id}).")
        return False

    return True

def _get_targets_in_aoe(combat: models.CombatEncounter, center_id: str, shape: str, range_m: int, target_type: str = "enemy") -> List[Tuple[str, Dict]]:
    """
    Finds all targets within an AoE radius or line.
    Returns a list of (actor_id, context) tuples.
    """
    targets = []

    try:
        _, center_context = get_actor_context(center_id)
        if center_id.startswith("player_"):
            center_x, center_y = center_context.get("position_x", 0), center_context.get("position_y", 0)
        else:
            center_x, center_y = center_context.get("coordinates", [0, 0])
    except:
        logger.error(f"Could not get center context for AoE: {center_id}")
        return []

    for p in combat.participants:
        try:
            p_actor_type, p_context = get_actor_context(p.actor_id)

            # --- Targeting Filter Logic ---
            is_player = p.actor_id.startswith("player_")
            is_npc = p.actor_id.startswith("npc_")

            # Check if this target should be included based on the requested target_type
            if target_type == "enemy" and is_player: continue
            if target_type == "ally" and (is_npc or p.actor_id == center_id): continue
            if target_type in ("ally_or_self", "area_ally") and is_npc: continue
            if target_type in ("area_enemy", "area") and is_player: continue
            if target_type == "enemy_and_ally" and p.actor_id == center_id: continue # Exclude self for generalized area/enemy_and_ally checks

            # Filter out defeated characters/npcs
            if p_context.get("current_hp", 0) <= 0: continue

            # --- Range Check (Manhattan Distance) ---
            if is_player:
                p_x, p_y = p_context.get("position_x", 999), p_context.get("position_y", 999)
            else:
                p_x, p_y = p_context.get("coordinates", [999, 999])

            # Calculate distance (Manhattan distance for grid-based check)
            distance = abs(p_x - center_x) + abs(p_y - center_y)

            if distance <= range_m:
                targets.append((p.actor_id, p_context))
        except:
            continue

    return targets


# ----------------------------------------------------
# --- COMBAT REWARD & LOGIC HELPERS (Original/Core) ---
# ----------------------------------------------------

def _grant_combat_rewards(db: Session, combat: models.CombatEncounter, log: List[str]):
    """Calculates and grants rewards (items, XP, etc.) upon combat victory."""
    logger.info(f"Granting rewards for combat {combat.id}")

    player_ids = [p.actor_id for p in combat.participants if p.actor_type == "player" and p.actor_id]
    if not player_ids:
        log.append("No surviving players to grant rewards to.")
        return

    primary_player_id = player_ids[0]

    for p in combat.participants:
        if p.actor_type == "npc":
            try:
                _, npc_context = get_actor_context(p.actor_id)
                if npc_context.get("current_hp", 0) > 0:
                    continue

                template_id = npc_context.get("template_id")
                if not template_id:
                    continue

                template_data = services.get_npc_generation_params(template_id)
                loot_table_ref = template_data.get("loot_table_ref")

                if not loot_table_ref:
                    continue

                loot_table = services.get_loot_table(loot_table_ref)
                for item_id, loot_info in loot_table.items():
                    if random.random() < loot_info.get("chance", 0):
                        quantity = loot_info.get("quantity", 1)
                        services.add_item_to_character(primary_player_id, item_id, quantity)
                        log.append(f"The {template_id} dropped {item_id} (x{quantity})!")
            except Exception as e:
                logger.exception(f"Failed to grant loot for {p.actor_id}: {e}")

def _find_spawn_points(map_data: List[List[int]], num_points: int) -> List[List[int]]:
    if not map_data:
        logger.warning("Map data is empty, cannot find spawn points.")
        return [[5, 5]] * num_points
    valid_spawns = []
    height = len(map_data)
    width = len(map_data[0]) if height > 0 else 0
    for y in range(height):
        for x in range(width):
            if map_data[y][x] in [0, 3]:
                valid_spawns.append([x, y])
    if not valid_spawns:
        logger.warning("No valid spawn tiles found on map. Falling back to default.")
        return [[5, 5]] * num_points
    random.shuffle(valid_spawns)
    return [valid_spawns[i % len(valid_spawns)] for i in range(num_points)]

def _extract_initiative_stats(stats_dict: Dict) -> Dict:
    return {
        "endurance": stats_dict.get("Endurance", 10),
        "reflexes": stats_dict.get("Reflexes", 10),
        "fortitude": stats_dict.get("Fortitude", 10),
        "logic": stats_dict.get("Logic", 10),
        "intuition": stats_dict.get("Intuition", 10),
        "willpower": stats_dict.get("Willpower", 10),
    }

def start_combat(db: Session, start_request: schemas.CombatStartRequest) -> models.CombatEncounter:
    logger.info(f"Starting combat at location {start_request.location_id}")
    participants_data: List[Tuple[str, str, int]] = []
    spawned_npc_details: List[Dict] = []

    spawn_points = []
    try:
        location_context = services.get_world_location_context(start_request.location_id)
        map_data = location_context.get("generated_map_data")
        num_npcs = len(start_request.npc_template_ids)

        map_spawn_points = location_context.get("spawn_points", {}).get("enemy")
        if map_spawn_points and len(map_spawn_points) >= num_npcs:
            random.shuffle(map_spawn_points)
            spawn_points = map_spawn_points[:num_npcs]
        else:
            spawn_points = _find_spawn_points(map_data, num_npcs)

    except Exception as e:
        logger.exception(f"Error finding spawn points: {e}.")
        spawn_points = [[5, 5]] * len(start_request.npc_template_ids)

    for i, template_id in enumerate(start_request.npc_template_ids):
        try:
            coords = spawn_points[i]
            template_lookup = services.get_npc_generation_params(template_id)
            generation_params = template_lookup.get("generation_params")
            if not generation_params:
                logger.error(f"No generation_params found for template_id: {template_id}")
                continue

            full_npc_template = services.generate_npc_template(generation_params)

            npc_max_hp = full_npc_template.get("max_hp", 10)
            npc_abilities = full_npc_template.get("abilities", [])

            spawn_data = schemas.OrchestrationSpawnNpc(
                template_id=template_id,
                location_id=start_request.location_id,
                coordinates=coords,
                current_hp=npc_max_hp,
                max_hp=npc_max_hp,
                behavior_tags=full_npc_template.get("behavior_tags", ["aggressive"]),
            )
            npc_instance_data = services.spawn_npc_in_world(spawn_data)

            try:
                services.world_api.update_npc_state(npc_instance_data['id'], {"abilities": npc_abilities})
            except Exception as e_abil:
                logger.error(f"Failed to manually add abilities to NPC: {e_abil}")

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
            initiative_total = init_result.get("total_initiative", 0)
            participants_data.append((player_id_str, "player", initiative_total))
        except Exception as e:
            logger.exception(f"Unexpected error processing Player {player_id_str}: {e}")
            participants_data.append((player_id_str, "player", 0))

    for npc_data in spawned_npc_details:
        actor_id_str = f"npc_{npc_data.get('id')}"
        try:
            npc_context = services.get_npc_context(npc_data.get('id'))
            template_id = npc_context.get("template_id", "")
            if not template_id:
                npc_stats = {}
            else:
                template_lookup = services.get_npc_generation_params(template_id)
                generation_params = template_lookup.get("generation_params")
                if not generation_params:
                    npc_stats = {}
                else:
                    full_npc_template = services.generate_npc_template(generation_params)
                    npc_stats = full_npc_template.get("stats", {})

            stats_for_init = _extract_initiative_stats(npc_stats)
            init_result = services.roll_initiative(**stats_for_init)
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
            context_data = services.get_npc_context(npc_instance_id)
            return "npc", context_data
        except (IndexError, ValueError):
            raise HTTPException(status_code=400, detail=f"Invalid NPC actor ID format: {actor_id}")
        except HTTPException as e:
            raise e
    else:
        raise HTTPException(status_code=400, detail=f"Unknown actor ID format: {actor_id}")

def get_stat_score(actor_context: Dict, stat_name: str) -> int:
    stats = actor_context.get("stats", {})
    return stats.get(stat_name, 10)

def get_skill_rank(actor_context: Dict, skill_name: str) -> int:
    skills = actor_context.get("skills", {})
    skill_data = skills.get(skill_name)
    if isinstance(skill_data, dict):
        return skill_data.get("rank", 0)
    elif isinstance(skill_data, int):
        return skill_data
    return 0

def get_equipped_weapon(actor_context: Dict) -> Tuple[Optional[str], Optional[str]]:
    actor_name = actor_context.get('name', actor_context.get('template_id', 'Unknown Actor'))
    equipment = actor_context.get("equipment")
    if equipment is not None:
        weapon_item_id = equipment.get("weapon")
        if weapon_item_id:
            try:
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
    else:
        npc_skills = actor_context.get("skills", {})
        if npc_skills.get("Great Weapons", 0) > 0: return "Great Weapons", "melee"
        if npc_skills.get("Bows and Firearms", 0) > 0: return "Bows and Firearms", "ranged"
        return "Unarmed/Fist Weapons", "melee"

def get_equipped_armor(actor_context: Dict) -> Optional[str]:
    actor_name = actor_context.get('name', actor_context.get('template_id', 'Unknown Actor'))
    equipment = actor_context.get("equipment")
    if equipment is not None:
        armor_item_id = equipment.get("armor")
        if armor_item_id:
            try:
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
    else:
        npc_skills = actor_context.get("skills", {})
        if npc_skills.get("Plate Armor", 0) > 0: return "Plate Armor"
        elif npc_skills.get("Clothing/Utility", 0) > 0: return "Clothing/Utility"
        return "Natural/Unarmored"

def check_combat_end_condition(db: Session, combat: models.CombatEncounter, log: List[str]) -> bool:
    """Checks if all NPCs or all Players are defeated."""
    players_alive, npcs_alive = False, False

    for p in combat.participants:
        try:
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
            _grant_combat_rewards(db, combat, log)

        combat.status = end_status
        db.commit()
        logger.info(f"Combat {combat.id} ended: {end_status}")
        return True
    return False

def determine_npc_action(db: Session, combat: models.CombatEncounter, npc_actor_id: str) -> Optional[schemas.PlayerActionRequest]:
    """
    Determines an NPC's action based on health, behavior tags, and abilities.
    """
    try:
        _, npc_context = get_actor_context(npc_actor_id)
    except HTTPException:
        logger.error(f"Could not get context for NPC {npc_actor_id} to determine action.")
        return None

    status_effects = npc_context.get("status_effects", [])
    if "Staggered" in status_effects:
        logger.info(f"NPC {npc_actor_id} is Staggered and skips its turn.")
        services.remove_status_from_npc(int(npc_actor_id.split('_')[1]), "Staggered")
        return None

    behavior_tags = npc_context.get("behavior_tags", [])
    npc_current_hp = npc_context.get("current_hp", 1)
    npc_max_hp = npc_context.get("max_hp", 1)
    npc_abilities = npc_context.get("abilities", [])

    living_players = []
    for p in combat.participants:
        if p.actor_id.startswith("player_"):
            try:
                _, p_context = get_actor_context(p.actor_id)
                if p_context.get("current_hp", 0) > 0:
                    living_players.append(p_context)
            except HTTPException:
                continue

    if not living_players:
        return None

    # --- AI Decision Tree ---
    if "Minor Heal" in npc_abilities and npc_current_hp < (npc_max_hp * 0.5):
        return schemas.PlayerActionRequest(action="use_ability", ability_id="Minor Heal", target_id=npc_actor_id)

    if "cowardly" in behavior_tags and npc_current_hp < (npc_max_hp * 0.3):
        return None

    target_player = None
    if "targets_weakest" in behavior_tags:
        living_players.sort(key=lambda p: p.get("current_hp", 999))
        target_player = living_players[0]
    else:
        target_player = random.choice(living_players)

    target_id = target_player['id']

    if "Nausea" in npc_abilities and random.random() < 0.5:
        return schemas.PlayerActionRequest(action="use_ability", ability_id="Nausea", target_id=target_id)

    if "Repel Step" in npc_abilities and random.random() < 0.3:
        return schemas.PlayerActionRequest(action="use_ability", ability_id="Repel Step", target_id=npc_actor_id)

    return schemas.PlayerActionRequest(action="attack", target_id=target_id)

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

# --- NEW: Dice Rolling Helper ---
def _roll_dice_string(dice_str: str) -> int:
    """Rolls dice based on a string like '1d8' or '2d6'."""
    try:
        if "d" in dice_str:
            num, die = map(int, dice_str.split('d'))
            # Roll details is a list of individual roll results
            return sum(random.randint(1, die) for _ in range(num))
        else:
            return int(dice_str)
    except Exception as e:
        logger.error(f"Failed to roll dice string '{dice_str}': {e}")
        return 0

# ----------------------------------------------------
# --- ABILITY EFFECT HANDLERS (COMPLETED/UPDATED) ---
# ----------------------------------------------------

# --- Resource Management ---

def _handle_effect_composure_damage(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles effects that deal damage directly to the Composure pool (e.g., Spirit T1)."""
    amount_str = effect.get("amount", "1d6")
    damage_amount = _roll_dice_string(amount_str)

    if damage_amount > 0:
        log.append(f"{target_id} suffers {damage_amount} Composure damage! [STUB]")
        # TODO: Implement actual Composure deduction via character_api/world_api
    return True

def _handle_effect_composure_damage_roll(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles effects that deal Composure damage with a save for half damage (e.g., Psionics T4)."""
    amount_str = effect.get("amount", "3d6")
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 14)

    if not save_stat:
        log.append(f"Cannot execute Composure damage roll: missing save_stat.")
        return False

    _, target_context = get_actor_context(target_id)
    stat_score = get_stat_score(target_context, save_stat)
    stat_mod = rules_core.calculate_modifier(stat_score)

    roll = random.randint(1, 20)
    total = roll + stat_mod
    damage_amount = _roll_dice_string(amount_str)

    final_damage = damage_amount
    if total >= dc:
        final_damage = damage_amount // 2
        log.append(f"{target_id} SAVED ({total} vs DC {dc}) and takes half Composure damage: {final_damage}.")
    else:
        log.append(f"{target_id} FAILED to save ({total} vs DC {dc}) and takes {final_damage} Composure damage.")

    if final_damage > 0:
        log.append(f"[STUB] {final_damage} Composure damage applied to {target_id}.")
    return True

def _handle_effect_composure_heal(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles effects that restore Composure to a target (e.g., Spirit T1)."""
    amount_str = effect.get("amount", "1d6")
    heal_amount = _roll_dice_string(amount_str)

    log.append(f"{target_id} is healed for {heal_amount} Composure! [STUB]")
    # TODO: Implement actual Composure restoration via character_api/world_api
    return True

def _handle_effect_resource_damage(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles effects that drain a character's resource pool (e.g., Cosmos T5, Spirit T3)."""
    resource_id = effect.get("resource")
    amount_str = effect.get("amount", "1d4")
    damage_amount = _roll_dice_string(amount_str)

    # Handle roll if included in effect
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 15)

    if save_stat:
        _, target_context = get_actor_context(target_id)
        stat_score = get_stat_score(target_context, save_stat)
        stat_mod = rules_core.calculate_modifier(stat_score)
        roll = random.randint(1, 20)
        total = roll + stat_mod

        if total >= dc:
             log.append(f"{target_id} SAVED ({total} vs DC {dc}) and resisted resource drain.")
             return False

    if not resource_id:
        log.append(f"Resource damage failed: missing resource ID.")
        return False

    log.append(f"{target_id} loses {damage_amount} {resource_id} points. [STUB]")
    # TODO: Implement actual resource pool deduction.
    return True

# --- Status and Move ---

def _handle_effect_modify_attack(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """Handles abilities that modify a basic attack (e.g., "Concussive Strike")."""
    return _handle_basic_attack(actor_id, target_id, attacker_context, defender_context, log, ability_mod=effect)

def _handle_effect_direct_damage(
    target_id: str,
    log: List[str],
    effect: Dict) -> bool:
    """Handles effects that deal direct damage without an attack roll (e.g., Biomancy T2)."""
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

def _handle_effect_heal(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles effects that restore HP (e.g., Biomancy T2)."""
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
            services.world_api.update_npc_state(npc_instance_id, {"current_hp": new_hp})
        except Exception as e:
            log.append(f"Failed to apply heal to {target_id}: {e}")
            return False

    log.append(f"{target_id} is healed for {heal_amount} HP!")
    return True

def _handle_effect_apply_status(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles effects that apply a status, no save (e.g., Force T1)."""
    status_id = effect.get("status_id")
    if not status_id: return False
    services.apply_status_to_target(target_id, status_id)
    log.append(f"{target_id} is now afflicted with {status_id}!")
    return True

def _handle_effect_apply_status_roll(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles effects that apply a status, WITH a save (e.g., Biomancy T1)."""
    status_id = effect.get("status_id")
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 12)

    if not status_id or not save_stat: return False

    _, target_context = get_actor_context(target_id)
    stat_score = get_stat_score(target_context, save_stat)
    stat_mod = rules_core.calculate_modifier(stat_score)

    roll = random.randint(1, 20)
    total = roll + stat_mod

    if total >= dc:
        log.append(f"{target_id} rolled {total} and SAVED against {status_id} (DC {dc})!")
        return False
    else:
        log.append(f"{target_id} FAILED to save ({total}) and is {status_id} (DC {dc})!")
        services.apply_status_to_target(target_id, status_id)
        return True

def _handle_effect_remove_status(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles removing a specific status (e.g., Biomancy T1)."""
    status_id = effect.get("status_id")

    if not status_id:
        log.append(f"Cannot remove status: missing status_id.")
        return False

    if target_id.startswith("player_"):
        services.remove_status_from_character(target_id, status_id)
    elif target_id.startswith("npc_"):
        npc_instance_id = int(target_id.split("_")[1])
        services.remove_status_from_npc(npc_instance_id, status_id)

    log.append(f"Status '{status_id}' removed from {target_id}.")
    return True

def _handle_effect_move_target_roll(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """Handles effects that move a target, WITH a save (e.g., Force T1)."""
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 12)

    if not save_stat:
        log.append(f"Cannot execute move effect: missing save_stat.")
        return False

    stat_score = get_stat_score(defender_context, save_stat)
    stat_mod = rules_core.calculate_modifier(stat_score)

    roll = random.randint(1, 20)
    total = roll + stat_mod

    if total >= dc:
        log.append(f"{target_id} rolled {total} and RESISTS the forced movement (DC {dc})!")
        return False
    else:
        log.append(f"{target_id} FAILED to resist ({total} vs DC {dc})!")
        return _handle_effect_move_target(target_id, log, effect)

def _handle_effect_move_target(
    target_id: str,
    log: List[str],
    effect: Dict) -> bool:
    """Handles effects that move a target (used by _handle_effect_move_target_roll when save fails)."""
    if target_id.startswith("npc_"):
        try:
            distance = effect.get("distance", 1)
            npc_instance_id = int(target_id.split('_')[1])
            _, defender_context = get_actor_context(target_id)
            current_coords = defender_context.get("coordinates", [1, 1])
            loc_id = defender_context.get("location_id")

            new_x, new_y = current_coords[0], current_coords[1] + distance

            if not _is_passable_and_in_bounds(loc_id, new_x, new_y, log):
                log.append(f"Target move stopped by obstacle or boundary.")
                return False

            services.world_api.update_npc_state(npc_instance_id, {"coordinates": [new_x, new_y]})
            log.append(f"{target_id} is pushed {distance}m to ({new_x}, {new_y})!")
            return True
        except Exception as e:
            log.append(f"Failed to move target: {e}")
            return False
    else:
        log.append(f"Cannot move {target_id} (only NPCs can be forcibly moved in combat).")
        return False

def _handle_effect_move_self(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """Handles effects that move the caster (e.g., Force T2: Repel Step)."""
    distance = effect.get("distance", 2)
    direction = "up"

    try:
        loc_id = attacker_context.get("current_location_id")

        if actor_id.startswith("player_"):
            current_coords = [attacker_context.get("position_x"), attacker_context.get("position_y")]
        elif actor_id.startswith("npc_"):
            current_coords = attacker_context.get("coordinates", [1, 1])
        else:
            log.append(f"Cannot move self: Unknown actor type for {actor_id}.")
            return False

        new_x, new_y = current_coords[0], current_coords[1]

        if direction == "up": new_y += distance
        elif direction == "down": new_y -= distance
        elif direction == "right": new_x += distance
        elif direction == "left": new_x -= distance

        if not _is_passable_and_in_bounds(loc_id, new_x, new_y, log):
            return False

        if actor_id.startswith("player_"):
            services.character_api.update_character_location(actor_id, loc_id, [new_x, new_y])
        elif actor_id.startswith("npc_"):
            npc_instance_id = int(actor_id.split('_')[1])
            services.world_api.update_npc_state(npc_instance_id, {"coordinates": [new_x, new_y]})

        log.append(f"{actor_id} repels themselves {distance}m to ({new_x}, {new_y})!")
        return True

    except Exception as e:
        log.append(f"Failed to move self: {e}")
        return False

# --- AoE Handlers ---

def _handle_effect_aoe_status_apply(actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Handles AoE application of a status (no roll) (e.g., Cunning T4)."""
    status_id = effect.get("status_id")
    shape = effect.get("shape", "radius")
    range_m = effect.get("range", 5)

    if not status_id: return False

    try:
        db = story_db.SessionLocal()
        combat = crud.get_combat_encounter(db, combat_id=attacker_context.get("combat_id"))
    finally:
        if db: db.close()

    # Assuming AoE buffs target friends by default
    aoe_targets = _get_targets_in_aoe(combat, target_id, shape, range_m, target_type="ally_or_self")

    for p_actor_id, p_context in aoe_targets:
        services.apply_status_to_target(p_actor_id, status_id)
        log.append(f"  -> {p_actor_id} gains {status_id}.")

    log.append(f"AoE status '{status_id}' applied to {len(aoe_targets)} targets in the {shape}.")
    return True

def _handle_effect_aoe_status_roll(actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Handles AoE application of a status with an individual save roll (e.g., Evocation T2)."""
    status_id = effect.get("status_id")
    shape = effect.get("shape", "radius")
    range_m = effect.get("range", 5)
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 14)

    if not status_id or not save_stat: return False

    try:
        db = story_db.SessionLocal()
        combat = crud.get_combat_encounter(db, combat_id=attacker_context.get("combat_id"))
    finally:
        if db: db.close()

    aoe_targets = _get_targets_in_aoe(combat, target_id, shape, range_m, target_type="enemy")
    targets_hit = 0

    for p_actor_id, p_context in aoe_targets:
        if not p_context: continue
        stat_score = get_stat_score(p_context, save_stat)
        stat_mod = rules_core.calculate_modifier(stat_score)
        roll = random.randint(1, 20)
        total = roll + stat_mod

        if total < dc:
            services.apply_status_to_target(p_actor_id, status_id)
            targets_hit += 1
            log.append(f"  -> {p_actor_id} FAILED save ({total}) and is {status_id}!")
        else:
             log.append(f"  -> {p_actor_id} SAVED ({total}) against {status_id}.")

    log.append(f"AoE status '{status_id}' attempted on {len(aoe_targets)} targets. {targets_hit} hit.")
    return True

def _handle_effect_aoe_composure_damage_roll(actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Handles AoE Composure damage with individual saves for half damage (e.g., Spirit T4)."""
    amount_str = effect.get("amount", "1d6")
    shape = effect.get("shape", "radius")
    range_m = effect.get("range", 5)
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 14)

    if not save_stat: return False

    try:
        db = story_db.SessionLocal()
        combat = crud.get_combat_encounter(db, combat_id=attacker_context.get("combat_id"))
    finally:
        if db: db.close()

    aoe_targets = _get_targets_in_aoe(combat, target_id, shape, range_m, target_type="enemy")
    total_damage = 0

    for p_actor_id, p_context in aoe_targets:
        stat_score = get_stat_score(p_context, save_stat)
        stat_mod = rules_core.calculate_modifier(stat_score)
        roll = random.randint(1, 20)
        total = roll + stat_mod
        damage_amount = _roll_dice_string(amount_str)
        final_damage = damage_amount

        if total >= dc:
            final_damage = damage_amount // 2

        total_damage += final_damage
        if final_damage > 0:
            log.append(f"[STUB] Applied {final_damage} Composure damage to {p_actor_id}.")

    log.append(f"AoE Composure damage applied to {len(aoe_targets)} targets, total damage: {total_damage}.")
    return True

def _handle_effect_aoe_heal(actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Handles AoE healing for HP (e.g., Biomancy T8)."""
    amount_str = effect.get("amount", "1d6")
    shape = effect.get("shape", "radius")
    range_m = effect.get("range", 5)

    try:
        db = story_db.SessionLocal()
        combat = crud.get_combat_encounter(db, combat_id=attacker_context.get("combat_id"))
    finally:
        if db: db.close()

    aoe_targets = _get_targets_in_aoe(combat, target_id, shape, range_m, target_type="ally_or_self")
    total_healed = 0

    for p_actor_id, p_context in aoe_targets:
        heal_amount = _roll_dice_string(amount_str)
        total_healed += heal_amount

        if p_actor_id.startswith("player_"):
            services.apply_healing_to_character(p_actor_id, heal_amount)
        elif p_actor_id.startswith("npc_"):
            log.append(f"[STUB] NPC healing applied to {p_actor_id}.")

        log.append(f"  -> {p_actor_id} healed for {heal_amount} HP.")

    log.append(f"AoE heal applied to {len(aoe_targets)} targets, total healed: {total_healed} HP.")
    return True

def _handle_effect_aoe_damage(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """Handles AoE HP damage (e.g., Evocation T2)."""
    damage_str = effect.get("damage", "1d6")
    shape = effect.get("shape", "radius")
    range_m = effect.get("range", 3)
    damage_type = effect.get("damage_type", "elemental")

    try:
        db = story_db.SessionLocal()
        combat = crud.get_combat_encounter(db, combat_id=attacker_context.get("combat_id"))
    finally:
        if db: db.close()

    if not combat:
        log.append("AoE damage failed: No active combat found.")
        return False

    aoe_targets = _get_targets_in_aoe(combat, target_id, shape, range_m, target_type="enemy")

    if not aoe_targets:
        log.append(f"AoE damage failed: No enemies found in {range_m}m {shape}.")
        return False

    log.append(f"AoE {damage_type} damage hits {len(aoe_targets)} targets.")

    for p_actor_id, p_context in aoe_targets:
        damage_amount = _roll_dice_string(damage_str)

        log.append(f"  -> {p_actor_id} suffers {damage_amount} {damage_type} damage.")

        if p_actor_id.startswith("player_"):
            services.apply_damage_to_character(p_actor_id, damage_amount)
        elif p_actor_id.startswith("npc_"):
            try:
                npc_instance_id = int(p_actor_id.split("_")[1])
                new_hp = p_context.get("current_hp", 0) - damage_amount
                services.apply_damage_to_npc(npc_instance_id, new_hp)
            except Exception as e:
                log.append(f"Failed to apply AoE damage to {p_actor_id}: {e}")

    return True

# --- Utility / Special Handlers ---

def _handle_effect_temp_hp(actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Grants Temporary HP to a target (e.g., Psionics T2)."""
    amount_str = effect.get("amount", "1d8")
    amount = _roll_dice_string(amount_str)

    if effect.get("amount_formula"):
        formula = effect["amount_formula"]
        might_score = attacker_context.get("stats", {}).get("Might", 0)
        level = attacker_context.get("level", 1)
        try:
            amount = eval(formula.replace("Might", str(might_score)).replace("Level", str(level)))
        except:
            pass # Use rolled amount if formula fails

    log.append(f"Temporary HP granted to {target_id}: {amount} HP. [STUB]")
    return True

def _handle_effect_random_stat_debuff(target_id: str, log: List[str], effect: Dict) -> bool:
    """Applies a random penalty to one of the target's stats (e.g., Chaos T2)."""
    # A list of Core Stats (A-L)
    stats_to_debuff = ["Might", "Endurance", "Finesse", "Reflexes", "Vitality", "Fortitude", "Knowledge", "Logic", "Awareness", "Intuition", "Charm", "Willpower"]
    stat = random.choice(stats_to_debuff)
    amount = effect.get("amount", -1)
    duration = effect.get("duration", 1)

    log.append(f"Random Debuff: {target_id} suffers {amount} penalty to {stat} for {duration} round(s). [STUB]")
    # TODO: Implement temporary stat modification via status effect logic
    return True

def _handle_effect_reaction_damage(
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Stub for Reaction Damage (e.g., Bastion T2)."""
    log.append(f"[STUB] Reaction '{effect.get('trigger')}' triggered. Needs full implementation.")
    return True

def _handle_effect_reaction_move_ally(
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Stub for Reaction Move Ally (e.g., Grace T2)."""
    log.append(f"[STUB] Reaction '{effect.get('trigger')}' triggered. Needs full implementation.")
    return True

def _handle_effect_reaction_contest(
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Stub for Complex Reaction Contest (e.g., Force T7)."""
    trigger = effect.get("trigger")
    user_stat = effect.get("user_stat")
    effect_on_win = effect.get("effect_on_win")

    log.append(f"[STUB] Reaction '{trigger}' triggered. Needs implementation of contested {user_stat} check.")
    return True

def _handle_effect_create_trap(
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Stub for Trap Creation (e.g., Cunning T2)."""
    trap_id = effect.get("effect_id", "generic_trap")

    # Get coordinates near the target (or caster if target_id is self/area)
    _, target_context = get_actor_context(target_id)
    if target_id.startswith("player_"):
        coords = [target_context.get("position_x", 0) + 1, target_context.get("position_y", 0)]
    else:
        coords = [target_context.get("coordinates", [0, 0])[0] + 1, target_context.get("coordinates", [0, 0])[1]]

    log.append(f"{actor_id} successfully places a trap: {trap_id} at {coords}. [STUB: Requires World Module 'Trap' entity logic].")
    return True

def _handle_effect_special_move(
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Stub for Special Move/Action (e.g., Psionics T2)."""
    effect_id = effect.get("effect_id", "unknown_move")
    log.append(f"Performing special action: {effect_id}! [STUB: Custom logic required].")
    return True


# This is the "router" that maps `effect["type"]` to the functions above
ABILITY_EFFECT_HANDLERS: Dict[str, Callable] = {
    # Core Attack/Damage/Heal
    "modify_attack": _handle_effect_modify_attack,
    "direct_damage": _handle_effect_direct_damage,
    "heal": _handle_effect_heal,

    # Core Status/Move
    "apply_status": _handle_effect_apply_status,
    "apply_status_roll": _handle_effect_apply_status_roll,
    "remove_status": _handle_effect_remove_status,
    "move_target": _handle_effect_move_target,
    "move_target_roll": _handle_effect_move_target_roll,
    "move_self": _handle_effect_move_self,

    # Resources (Composure/Pools)
    "composure_damage": _handle_effect_composure_damage,
    "composure_damage_roll": _handle_effect_composure_damage_roll,
    "composure_heal": _handle_effect_composure_heal,
    "resource_damage_roll": _handle_effect_resource_damage,
    "resource_damage": _handle_effect_resource_damage,

    # AoE
    "aoe_damage": _handle_effect_aoe_damage,
    "aoe_status": _handle_effect_aoe_status_apply,
    "aoe_status_roll": _handle_effect_aoe_status_roll,
    "aoe_composure_damage_roll": _handle_effect_aoe_composure_damage_roll,
    "aoe_heal": _handle_effect_aoe_heal,

    # Utility / Special
    "create_trap": _handle_effect_create_trap,
    "temp_hp": _handle_effect_temp_hp,
    "random_status": _handle_effect_random_status,
    "random_stat_debuff": _handle_effect_random_stat_debuff,

    # Complex Stubs (Re-used for special_action/roll)
    "reaction_damage": _handle_effect_reaction_damage,
    "reaction_move_ally": _handle_effect_reaction_move_ally,
    "reaction_contest": _handle_effect_reaction_contest,
    "special_move": _handle_effect_special_move,
    "special_action": _handle_effect_special_move,
    "special_action_roll": _handle_effect_special_move,
}

# --- Main Attack Handler (Original/Core) ---
def _handle_basic_attack(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
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
        dr_pierce = 0

        if ability_mod.get("damage_boost"):
            damage_bonus = _roll_dice_string(ability_mod["damage_boost"])
            log.append(f"Ability adds +{damage_bonus} damage!")

        if ability_mod.get("armor_pierce"):
             dr_pierce = ability_mod.get("armor_pierce")
             log.append(f"Ability grants {dr_pierce} Armor Pierce.")


        damage_params = {
            "base_damage_dice": weapon_data["damage"],
            "relevant_stat_score": get_stat_score(attacker_context, weapon_data["skill_stat"]),
            "attacker_damage_bonus": damage_bonus, # Pass in the bonus
            "attacker_damage_penalty": 0,
            "attacker_dr_modifier": dr_pierce, # Pass in the pierce
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

# --- Main Action Handler (Original/Core) ---
def handle_player_action(db: Session, combat: models.CombatEncounter, actor_id: str, action: schemas.PlayerActionRequest) -> schemas.PlayerActionResponse:
    log = []

    current_actor_id = combat.turn_order[combat.current_turn_index]
    if actor_id != current_actor_id:
        raise HTTPException(status_code=403, detail=f"It is not {actor_id}'s turn.")

    try:
        actor_type, attacker_context = get_actor_context(actor_id)
        status_effects = attacker_context.get("status_effects", [])

        # Pass combat ID to context so effect handlers can re-access the combat state
        attacker_context["combat_id"] = combat.id

        if "Staggered" in status_effects:
            log.append(f"{actor_id} is Staggered and loses their turn!")
            if actor_type == "player":
                services.remove_status_from_character(actor_id, "Staggered")
            else:
                services.remove_status_from_npc(int(actor_id.split('_')[1]), "Staggered")
            return handle_no_action(db, combat, actor_id, reason="is Staggered")

    except HTTPException as he:
        return handle_no_action(db, combat, actor_id, reason=f"could not be found ({he.detail})")

    if action.action == "wait":
        return handle_no_action(db, combat, actor_id)

    target_id = action.target_id
    if (action.action in ["attack", "use_ability", "use_item"]) and (not target_id):
        log.append(f"Action '{action.action}' requires a target, but none provided. Waiting instead.")
        return handle_no_action(db, combat, actor_id)

    try:
        defender_context = attacker_context # Default for self/area spells
        if target_id:
            target_type, defender_context = get_actor_context(target_id)
            hp = defender_context.get("current_hp", 0)
            if hp <= 0 and target_type == "npc":
                 raise HTTPException(status_code=400, detail=f"Target {target_id} is already defeated.")

        if action.action == "attack":
            log.append(f"{actor_id} targets {target_id} with an attack.")
            _handle_basic_attack(actor_id, target_id, attacker_context, defender_context, log)

        elif action.action == "use_ability":
            ability_name = action.ability_id
            log.append(f"{actor_id} uses ability: {ability_name} on {target_id}!")

            ability_data = services.get_ability_data(ability_name)
            if not ability_data:
                log.append(f"Unknown ability: {ability_name}. Action failed.")
            else:
                cost = ability_data.get("cost")
                if cost:
                    log.append(f"Paid {cost['amount']} {cost['resource']}.")

                for effect in ability_data.get("effects", []):
                    effect_type = effect.get("type")
                    handler = ABILITY_EFFECT_HANDLERS.get(effect_type)

                    if handler:
                        try:
                            handler(actor_id, target_id, attacker_context, defender_context, log, effect)
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
                        services.world_api.update_npc_state(npc_instance_id, {"current_hp": new_hp})

                    log.append(f"{actor_id} heals {target_id} for {healing_amount} HP.")

                    if actor_type == "player":
                        services.remove_item_from_character(actor_id, action.item_id, 1)
                else:
                    log.append(f"Item {action.item_id} has no combat effect.")
            except Exception as e:
                log.append(f"Could not use item: {e}")

        else:
            log.append(f"Action '{action.action}' not fully implemented. Waiting instead.")
            return handle_no_action(db, combat, actor_id)

        combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
        combat_over = check_combat_end_condition(db, combat, log)
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