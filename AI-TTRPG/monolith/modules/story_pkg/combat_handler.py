# AI-TTRPG/story_engine/app/combat_handler.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
import httpx
from typing import List, Dict, Any, Tuple, Optional
from . import crud, models, schemas, services
import random
import re
import logging

logger = logging.getLogger("uvicorn.error")

def _find_spawn_points(map_data: List[List[int]], num_points: int) -> List[List[int]]:
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
    return {
        "endurance": stats_dict.get("Endurance", 10),
        "reflexes": stats_dict.get("Reflexes", 10), # <-- CHANGED 'reflexes' was previously 'agility' here
        "fortitude": stats_dict.get("Fortitude", 10),
        "logic": stats_dict.get("Logic", 10),
        "intuition": stats_dict.get("Intuition", 10),
        "willpower": stats_dict.get("Willpower", 10),
    }

def start_combat(db: Session, start_request: schemas.CombatStartRequest) -> models.CombatEncounter:
    # --- REMOVED ASYNC ---
    logger.info(f"Starting combat at location {start_request.location_id}")
    participants_data: List[Tuple[str, str, int]] = []
    spawned_npc_details: List[Dict] = []

    # --- REMOVED 'async with httpx.AsyncClient() as client:' ---

    spawn_points = []
    try:
        # --- REMOVED AWAIT ---
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
            # --- ALL 'AWAIT' KEYWORDS REMOVED FROM THIS BLOCK ---
            template_lookup = services.get_npc_generation_params(template_id)
            generation_params = template_lookup.get("generation_params")
            if not generation_params: continue

            full_npc_template = services.generate_npc_template(generation_params)

            npc_max_hp = full_npc_template.get("max_hp", 10)
            spawn_data = schemas.OrchestrationSpawnNpc(
                template_id=template_id,
                location_id=start_request.location_id,
                coordinates=coords,
                current_hp=npc_max_hp,
                max_hp=npc_max_hp,
                behavior_tags=full_npc_template.get("behavior_tags", ["aggressive"])
            )
            npc_instance_data = services.spawn_npc_in_world(spawn_data)
            spawned_npc_details.append(npc_instance_data)
        except Exception as e:
            logger.exception(f"Unexpected error spawning NPC template '{template_id}': {e}")
            continue

    for player_id_str in start_request.player_ids:
        try:
            if not isinstance(player_id_str, str) or not player_id_str.startswith("player_"):
                continue
            # --- ALL 'AWAIT' KEYWORDS REMOVED FROM THIS BLOCK ---
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
            # --- ALL 'AWAIT' KEYWORDS REMOVED FROM THIS BLOCK ---
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
    # --- REMOVED ASYNC AND CLIENT ---
    logger.debug(f"Getting context for actor: {actor_id}")
    if actor_id.startswith("player_"):
        try:
            # --- REMOVED AWAIT ---
            context_data = services.get_character_context(actor_id)
            return "player", context_data
        # ... (error handling unchanged) ...
        except HTTPException as e:
            raise e
    elif actor_id.startswith("npc_"):
        try:
            npc_instance_id = int(actor_id.split("_")[1])
            # --- REMOVED AWAIT ---
            context_data = services.get_npc_context(npc_instance_id)
            return "npc", context_data
        # ... (error handling unchanged) ...
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
    # --- REMOVED ASYNC AND CLIENT ---
    actor_name = actor_context.get('name', actor_context.get('template_id', 'Unknown Actor'))
    equipment = actor_context.get("equipment")
    if equipment is not None: # Player
        weapon_item_id = equipment.get("weapon")
        if weapon_item_id:
            try:
                # --- REMOVED AWAIT ---
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

def get_equipped_armor(actor_context: Dict) -> Optional[str]:
    # --- REMOVED ASYNC AND CLIENT ---
    actor_name = actor_context.get('name', actor_context.get('template_id', 'Unknown Actor'))
    equipment = actor_context.get("equipment")
    if equipment is not None: # Player
        armor_item_id = equipment.get("armor")
        if armor_item_id:
            try:
                # --- REMOVED AWAIT ---
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

def check_combat_end_condition(db: Session, combat: models.CombatEncounter) -> bool:
    # --- REMOVED ASYNC ---
    players_alive, npcs_alive = False, False
    # --- REMOVED 'async with httpx.AsyncClient() as client:' ---
    for p in combat.participants:
        try:
            # --- REMOVED AWAIT ---
            actor_type, context = get_actor_context(p.actor_id)
            hp = context.get("current_hp", 0)
            if hp > 0:
                if actor_type == "player": players_alive = True
                elif actor_type == "npc": npcs_alive = True
        except HTTPException as e:
            logger.warning(f"Could not get context for {p.actor_id} during end check: {e.detail}.")

    if not players_alive or not npcs_alive:
        end_status = "npcs_win" if not players_alive else "players_win"
        combat.status = end_status
        db.commit()
        logger.info(f"Combat {combat.id} ended: {end_status}")
        return True
    return False

def determine_npc_action(db: Session, combat: models.CombatEncounter, npc_actor_id: str) -> Optional[schemas.PlayerActionRequest]:
    # --- REMOVED ASYNC ---
    log = [] # Create a log list
    try:
        # --- REMOVED AWAIT ---
        _, npc_context = get_actor_context(npc_actor_id)
    except HTTPException:
        logger.error(f"Could not get context for NPC {npc_actor_id} to determine action.")
        return None

    behavior_tags = npc_context.get("behavior_tags", [])
    npc_current_hp = npc_context.get("current_hp", 1)
    npc_max_hp = npc_context.get("max_hp", 1)

    # --- NEW: Cowardly Check ---
    if "cowardly" in behavior_tags and npc_current_hp < (npc_max_hp * 0.3):
        logger.info(f"NPC {npc_actor_id} is cowardly and waiting.")
        # Return None, which is handled as a "wait" action
        return None

    living_players = []
    for p in combat.participants:
        if p.actor_id.startswith("player_"):
            try:
                # --- REMOVED AWAIT ---
                _, p_context = get_actor_context(p.actor_id)
                if p_context.get("current_hp", 0) > 0:
                    living_players.append(p_context)
            except HTTPException:
                continue

    if not living_players:
        return None

    target_id, action_type = None, "attack"

    # --- MODIFIED: Targeting Logic ---
    if "targets_weakest" in behavior_tags:
        living_players.sort(key=lambda p: p.get("current_hp", 999))
        target_id = living_players[0]['id']
        logger.info(f"NPC {npc_actor_id} targets weakest player: {target_id}")
    else:
        # Default aggressive behavior
        target_id = random.choice(living_players)['id']
        logger.info(f"NPC {npc_actor_id} randomly targets: {target_id}")

    if action_type == "attack" and target_id:
        return schemas.PlayerActionRequest(action="attack", target_id=target_id)
    else:
        return None # Will be handled as a "wait" action

def handle_no_action(db: Session, combat: models.CombatEncounter, actor_id: str) -> schemas.PlayerActionResponse:
    # ... (same as before) ...
    pass

def handle_player_action(db: Session, combat: models.CombatEncounter, actor_id: str, action: schemas.PlayerActionRequest) -> schemas.PlayerActionResponse:
    # --- REMOVED ASYNC ---
    log = []
    current_actor_id = combat.turn_order[combat.current_turn_index]
    if actor_id != current_actor_id:
        raise HTTPException(status_code=403, detail=f"It is not {actor_id}'s turn.")

    if action.action == "wait":
        return handle_no_action(db, combat, actor_id)

    # --- NEW: Handle actions that require a target ---
    target_id = action.target_id
    if not target_id:
        log.append(f"Action '{action.action}' requires a target, but none provided. Waiting instead.")
        return handle_no_action(db, combat, actor_id)

    if action.action == "attack":
        log.append(f"{actor_id} targets {target_id} with an attack.")

    elif action.action == "use_ability":
        log.append(f"{actor_id} uses ability: {action.ability_id} on {target_id}!")

        # --- NEW: Ability Logic ---
        if "Minor Shove" in action.ability_id:
            try:
                log.append(f"{actor_id} attempts to shove {target_id}!")
                npc_instance_id = int(target_id.split('_')[1])
                _, defender_context = get_actor_context(target_id)
                current_coords = defender_context.get("coordinates", [1, 1])

                # Simple push "north" (increase Y)
                new_coords = [current_coords[0], current_coords[1] + 1]

                # TODO: Add check for map bounds and impassable tiles

                services.update_npc_state(npc_instance_id, {"coordinates": new_coords})
                log.append(f"{target_id} is pushed to {new_coords}!")

            except Exception as e:
                log.append(f"Ability failed: {e}")

        else:
            log.append("That ability's effect is not yet implemented.")

        # --- CRITICAL: Add turn advancement logic copied from use_item ---
        combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
        combat_over = check_combat_end_condition(db, combat)
        db.commit()
        db.refresh(combat)

        return schemas.PlayerActionResponse(
            success=True,
            message=f"{actor_id} used {action.ability_id}.",
            log=log,
            new_turn_index=combat.current_turn_index,
            combat_over=combat_over
        )
        # --- End ability logic ---

    elif action.action == "use_item":
        log.append(f"{actor_id} uses item: {action.item_id} on {target_id}!")

        # --- NEW: Item Logic ---
        try:
            item_template = services.get_item_template_params(action.item_id)
            if item_template.get("type") == "healing": # Check type
                healing_amount = item_template.get("potency", 15) # Use potency

                if target_id.startswith("player_"):
                    services.apply_healing_to_character(target_id, healing_amount)
                elif target_id.startswith("npc_"):
                    # TODO: Add NPC healing logic
                    pass
                log.append(f"{actor_id} heals {target_id} for {healing_amount} HP.")

            else:
                log.append(f"Item {action.item_id} has no combat effect.")

        except Exception as e:
            log.append(f"Could not use item: {e}")
        # --- End item logic ---

        # This part (turn advancement) is correct and remains
        combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
        combat_over = check_combat_end_condition(db, combat)
        db.commit()
        db.refresh(combat)

        return schemas.PlayerActionResponse(
            success=True,
            message=f"{actor_id} used {action.item_id}.",
            log=log,
            new_turn_index=combat.current_turn_index,
            combat_over=combat_over
        )
        # --- End self-contained action ---

    else:
        log.append(f"Action '{action.action}' not fully implemented. Waiting instead.")
        return handle_no_action(db, combat, actor_id)

    # --- (The rest of the function is now shared) ---
    try:
        _, attacker_context = get_actor_context(actor_id)
        target_type, defender_context = get_actor_context(target_id)

        hp = defender_context.get("current_hp", 0)
        if hp <= 0:
            raise HTTPException(status_code=400, detail=f"Target {target_id} is already defeated.")

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
        attack_result = services.roll_contested_attack(attack_params)
        log.append(f"Attack Roll: Attacker ({attack_result['attacker_final_total']}) vs Defender ({attack_result['defender_final_total']}). Margin: {attack_result['margin']}.")

        outcome = attack_result.get("outcome")
        if outcome in ["hit", "solid_hit", "critical_hit"]:
            log.append(f"Result: {actor_id} hits {target_id}!")
            damage_params = {
                "base_damage_dice": weapon_data["damage"],
                "relevant_stat_score": get_stat_score(attacker_context, weapon_data["skill_stat"]),
                "attacker_damage_bonus": 0,
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
        else:
            log.append(f"Result: {actor_id} misses {target_id}.")

        combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
        combat_over = check_combat_end_condition(db, combat) # Also sync
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
