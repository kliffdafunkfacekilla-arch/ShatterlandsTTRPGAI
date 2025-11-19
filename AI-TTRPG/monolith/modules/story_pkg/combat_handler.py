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
import heapq

logger = logging.getLogger("monolith.story.combat")

# ----------------------------------------------------
# --- NEW CORE MOVEMENT AND AOE HELPERS (REQUIRED) ---
# ----------------------------------------------------

def _find_next_step(start_coords: List[int], end_coords: List[int], location_id: int, log: List[str]) -> Optional[List[int]]:
    """
    Finds the next single step towards a target using A* pathfinding.
    Returns the coordinates of the next step, or None if no path is found.
    """
    try:
        width, height, map_data, impassable_ids = _get_map_dimensions_and_data(location_id)
    except RuntimeError as e:
        log.append(f"Pathfinding failed: {e}")
        return None

    start_node = (start_coords[1], start_coords[0]) # (y, x)
    end_node = (end_coords[1], end_coords[0]) # (y, x)

    # A* algorithm components
    open_list = []
    heapq.heappush(open_list, (0, start_node)) # (f_cost, (y, x))

    # Dictionaries to store A* data
    g_costs = {start_node: 0}
    parents = {start_node: None}

    while open_list:
        current_f_cost, current_node = heapq.heappop(open_list)

        # Stop if we are *adjacent* to the end node
        if _calculate_distance([current_node[1], current_node[0]], [end_node[1], end_node[0]]) <= 1:
            # Reconstruct path to find the *first step*
            path = []
            temp = current_node
            while temp and temp != start_node:
                path.append(temp)
                temp = parents.get(temp)

            if not path:
                return None # Already adjacent

            next_step_node = path.pop() # This is the first step from start
            return [next_step_node[1], next_step_node[0]] # Return as [x, y]

        # Explore neighbors
        (y, x) = current_node
        for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]: # 4-directional movement
            neighbor_node = (y + dy, x + dx)
            (ny, nx) = neighbor_node

            # Check bounds
            if not (0 <= ny < height and 0 <= nx < width):
                continue

            # Check passability
            if map_data[ny][nx] in impassable_ids:
                continue

            # Calculate new G cost
            new_g_cost = g_costs[current_node] + 1

            if neighbor_node not in g_costs or new_g_cost < g_costs[neighbor_node]:
                g_costs[neighbor_node] = new_g_cost
                # Heuristic: Manhattan distance
                h_cost = abs(ny - end_node[0]) + abs(nx - end_node[1])
                f_cost = new_g_cost + h_cost

                heapq.heappush(open_list, (f_cost, neighbor_node))
                parents[neighbor_node] = current_node

    log.append(f"Pathfinding: No path found from {start_coords} to {end_coords}.")
    return None # No path found

def _get_actor_coords(actor_context: Dict) -> Optional[List[int]]:
    """Helper to get coordinates for any actor context."""
    if "coordinates" in actor_context: # For NPCs
        return actor_context.get("coordinates")
    if "position_x" in actor_context: # For Players
        return [actor_context.get("position_x"), actor_context.get("position_y")]
    return None


# --- Resource Management ---

def _handle_effect_composure_damage(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles effects that deal damage directly to the Composure pool (e.g., Spirit T1)."""
    amount_str = effect.get("amount", "1d6")
    damage_amount = _roll_dice_string(amount_str)

    if damage_amount > 0:
        if target_id.startswith("player_"):
            services.apply_composure_damage_to_character(target_id, damage_amount)
        elif target_id.startswith("npc_"):
            services.apply_composure_damage_to_npc(int(target_id.split("_")[1]), damage_amount)

        log.append(f"{target_id} suffers {damage_amount} Composure damage!")
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
        if target_id.startswith("player_"):
            services.apply_composure_damage_to_character(target_id, final_damage)
        elif target_id.startswith("npc_"):
            services.apply_composure_damage_to_npc(int(target_id.split("_")[1]), final_damage)

    return True

def _handle_effect_composure_heal(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles effects that restore Composure to a target (e.g., Spirit T1)."""
    amount_str = effect.get("amount", "1d6")
    heal_amount = _roll_dice_string(amount_str)

    if target_id.startswith("player_"):
        services.apply_composure_healing_to_character(target_id, heal_amount)
    elif target_id.startswith("npc_"):
        services.apply_composure_healing_to_npc(int(target_id.split("_")[1]), heal_amount)

    log.append(f"{target_id} is healed for {heal_amount} Composure!")
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

    _, target_context = get_actor_context(target_id)
    current_pools = target_context.get("resource_pools", {})
    pool_data = current_pools.get(resource_id, {"current": 0, "max": 10})

    new_value = max(0, pool_data.get("current", 0) - damage_amount)

    if target_id.startswith("player_"):
        # This updates the pool using the dedicated character service function.
        services.update_character_resource_pool(target_id, resource_id, new_value)
        log.append(f"{target_id} loses {damage_amount} {resource_id}, dropping to {new_value}.")
    elif target_id.startswith("npc_"):
        services.update_npc_resource_pool(int(target_id.split("_")[1]), resource_id, new_value)
        log.append(f"{target_id} loses {damage_amount} {resource_id}, dropping to {new_value}.")

    return True

# --- Status and Move ---

def _handle_effect_modify_attack(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict) -> bool:
    """Handles abilities that modify a basic attack (e.g., "Concussive Strike")."""
    return _handle_basic_attack(db, combat, actor_id, target_id, attacker_context, defender_context, log, ability_mod=effect)

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

def _handle_effect_create_area(target_id: str, log: List[str], effect: Dict) -> bool:
    """
    Handles creating a persistent area effect (e.g., Wall of Stalwartness).
    For now, this is a placeholder that logs the creation.
    """
    area_id = effect.get("effect_id", "Unknown Area")
    shape = effect.get("shape", "radius")
    range_val = effect.get("range", 0)
    duration = effect.get("duration", 1)
    
    log.append(f"{target_id} creates a {shape} area '{area_id}' (Range: {range_val}m) for {duration} rounds.")
    # TODO: Implement actual area persistence in World Engine or Combat State
    return True

def _handle_effect_reaction_contest(target_id: str, log: List[str], effect: Dict) -> bool:
    """
    Handles a reaction that triggers a contested roll (e.g., Counterspell-like effects).
    """
    contest_stat = effect.get("contest_stat", "Willpower")
    dc = effect.get("dc", 15)
    
    log.append(f"{target_id} triggers a reaction contest using {contest_stat} vs DC {dc}!")
    
    _, target_context = get_actor_context(target_id)
    stat_score = get_stat_score(target_context, contest_stat)
    stat_mod = rules_core.calculate_modifier(stat_score)
    
    roll = random.randint(1, 20)
    total = roll + stat_mod
    
    if total >= dc:
        log.append(f"Success! ({total} vs {dc})")
        return True
    else:
        log.append(f"Failure! ({total} vs {dc})")
        return False

# --- AoE Handlers ---

def _get_targets_in_aoe(
    combat: models.CombatEncounter,
    center_target_id: str,
    shape: str,
    radius: int,
    target_type: str = "all" # "all", "enemy", "ally", "ally_or_self"
) -> List[Tuple[str, Dict]]:
    """
    Helper to find all actors within a certain radius of a target actor.
    Returns a list of (actor_id, actor_context).
    """
    targets = []
    try:
        _, center_context = get_actor_context(center_target_id)
        center_coords = _get_actor_coords(center_context)
        if not center_coords:
            return []

        center_faction = "player" if center_target_id.startswith("player_") else "npc"

        for participant in combat.participants:
            p_id = participant.actor_id
            try:
                _, p_context = get_actor_context(p_id)
                p_coords = _get_actor_coords(p_context)
                if not p_coords: continue

                distance = _calculate_distance(center_coords, p_coords)

                if distance <= radius:
                    # Filter by faction
                    p_faction = "player" if p_id.startswith("player_") else "npc"
                    is_enemy = (center_faction != p_faction)

                    if target_type == "enemy" and not is_enemy:
                        continue
                    if target_type == "ally" and is_enemy:
                        continue
                    if target_type == "ally_or_self" and is_enemy:
                        continue # (Self is included in ally check usually, or explicitly handled)

                    targets.append((p_id, p_context))

            except HTTPException:
                continue
    except Exception as e:
        logger.error(f"Error calculating AoE targets: {e}")
        return []

    return targets

def _calculate_distance(coords1: List[int], coords2: List[int]) -> float:
    """Chebyshev distance (chessboard distance) for grid movement."""
    return max(abs(coords1[0] - coords2[0]), abs(coords1[1] - coords2[1]))

def check_combat_end_condition(db: Session, combat: models.CombatEncounter, log: List[str]) -> bool:
    """Checks if all NPCs or all Players are defeated."""
    players_alive, npcs_alive = False, False

    for p in combat.participants:
        try:
            actor_type, context = get_actor_context(p.actor_id)
            hp = context.get("current_hp", 0)
            # --- CHANGED: Check for Downed status ---
            is_downed = "Downed" in context.get("status_effects", [])
            
            if hp > 0 and not is_downed:
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
                        services.add_item_to_character(db, primary_player_id, item_id, quantity)
                        log.append(f"The {template_id} dropped {item_id} (x{quantity})!")
            except Exception as e:
                logger.exception(f"Failed to grant loot for {p.actor_id}: {e}")

    # --- NEW: Grant XP ---
    xp_reward = 50 # Placeholder fixed amount per combat
    for pid in player_ids:
        try:
            services.award_xp(db, pid, xp_reward)
            log.append(f"Player {pid} gained {xp_reward} XP.")
        except Exception as e:
            logger.error(f"Failed to award XP to {pid}: {e}")

def _handle_effect_aoe_status_apply(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Handles AoE application of a status (no roll) (e.g., Cunning T4)."""
    status_id = effect.get("status_id")
    shape = effect.get("shape", "radius")
    range_m = effect.get("range", 5)

    if not status_id: return False

    # Assuming AoE buffs target friends by default
    aoe_targets = _get_targets_in_aoe(combat, target_id, shape, range_m, target_type="ally_or_self")

    for p_actor_id, p_context in aoe_targets:
        services.apply_status_to_target(p_actor_id, status_id)
        log.append(f"  -> {p_actor_id} gains {status_id}.")

    log.append(f"AoE status '{status_id}' applied to {len(aoe_targets)} targets in the {shape}.")
    return True

def _handle_effect_aoe_composure_damage_roll(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Handles AoE Composure damage with individual saves for half damage (e.g., Spirit T4)."""
    amount_str = effect.get("amount", "1d6")
    shape = effect.get("shape", "radius")
    range_m = effect.get("range", 5)
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 14)

    if not save_stat: return False

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
            if p_actor_id.startswith("player_"):
                services.apply_composure_damage_to_character(p_actor_id, final_damage)
            elif p_actor_id.startswith("npc_"):
                services.apply_composure_damage_to_npc(int(p_actor_id.split("_")[1]), final_damage)

            log.append(f" -> Applied {final_damage} Composure damage to {p_actor_id}.")

    log.append(f"AoE Composure damage applied to {len(aoe_targets)} targets, total damage: {total_damage}.")
    return True

def _handle_effect_aoe_heal(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Handles AoE healing for HP (e.g., Biomancy T8)."""
    amount_str = effect.get("amount", "1d6")
    shape = effect.get("shape", "radius")
    range_m = effect.get("range", 5)

    aoe_targets = _get_targets_in_aoe(combat, target_id, shape, range_m, target_type="ally_or_self")
    total_healed = 0

    for p_actor_id, p_context in aoe_targets:
        heal_amount = _roll_dice_string(amount_str)
        total_healed += heal_amount

        if p_actor_id.startswith("player_"):
            services.apply_healing_to_character(p_actor_id, heal_amount)
        elif p_actor_id.startswith("npc_"):
            try:
                npc_instance_id = int(p_actor_id.split("_")[1])
                new_hp = min(
                    p_context.get("current_hp", 0) + heal_amount,
                    p_context.get("max_hp", 99)
                )
                services.world_api.update_npc_state(npc_instance_id, {"current_hp": new_hp})
            except Exception as e:
                log.append(f"Failed to apply AoE heal to {p_actor_id}: {e}")

        log.append(f"  -> {p_actor_id} healed for {heal_amount} HP.")

    log.append(f"AoE heal applied to {len(aoe_targets)} targets, total healed: {total_healed} HP.")
    return True

def _handle_effect_aoe_damage(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str,
    target_id: str, # This is the epicenter of the AoE
    attacker_context: Dict,
    defender_context: Dict, # Context of the epicenter target
    log: List[str],
    effect: Dict
) -> bool:
    """
    Handles effects that deal AoE damage.
    """
    damage_str = effect.get("damage", "1d8")
    damage_type = effect.get("damage_type", "elemental")
    shape = effect.get("shape", "radius")
    aoe_range = effect.get("range", 2) # e.g., 2m radius
    target_faction = effect.get("target_faction", "enemy") # "enemy" or "ally"

    log.append(f"{actor_id} unleashes an AoE {shape} for {damage_str} {damage_type} damage around {target_id}!")

    # 1. Get epicenter coordinates
    epicenter_coords = _get_actor_coords(defender_context)
    if not epicenter_coords:
        log.append(f"Could not find epicenter coordinates for target {target_id}. Effect fails.")
        return False

    # 2. Roll damage ONCE
    damage_amount = _roll_dice_string(damage_str)
    if damage_amount <= 0:
        log.append("The effect fizzles and deals no damage.")
        return True # The ability was used, it just did no damage

    # 3. Find all targets in combat
    all_targets = []
    actor_type_prefix = "player_" if target_faction == "ally" else "npc_"
    if target_faction == "ally":
        actor_type_prefix = "player_"
    else:
        # Default to targeting enemies of the caster
        actor_type_prefix = "npc_" if actor_id.startswith("player_") else "player_"

    for p in combat.participants:
        if p.actor_id.startswith(actor_type_prefix):
            try:
                _, p_context = get_actor_context(p.actor_id)
                if p_context.get("current_hp", 0) > 0:
                    all_targets.append(p_context)
            except HTTPException:
                continue

    # 4. Apply damage to targets in range
    targets_hit = 0
    for target_ctx in all_targets:
        target_coords = _get_actor_coords(target_ctx)
        distance = _calculate_distance(epicenter_coords, target_coords)

        if distance <= aoe_range:
            # Target is in range
            targets_hit += 1
            target_hit_id = target_ctx.get("id")
            log.append(f"The blast hits {target_hit_id} for {damage_amount} damage!")

            # Apply damage (simplified, ignores armor for AoE)
            if target_hit_id.startswith("player_"):
                services.apply_damage_to_character(target_hit_id, damage_amount)
            elif target_hit_id.startswith("npc_"):
                try:
                    npc_instance_id = int(target_hit_id.split("_")[1])
                    new_hp = target_ctx.get("current_hp", 0) - damage_amount
                    services.apply_damage_to_npc(npc_instance_id, new_hp)
                except Exception as e:
                    log.append(f"Failed to apply AoE damage to {target_hit_id}: {e}")

    if targets_hit == 0:
        log.append("...but nothing was in range!")

    return True

def _handle_effect_aoe_status_roll(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict
) -> bool:
    """
    Handles AoE status application with a save (e.g., Flashbang).
    """
    status_id = effect.get("status_id")
    shape = effect.get("shape", "radius")
    aoe_range = effect.get("range", 2)
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 12)

    if not status_id or not save_stat:
        return False

    log.append(f"{actor_id} unleashes an AoE {shape} to apply {status_id} around {target_id}!")

    # 1. Get epicenter coordinates
    epicenter_coords = _get_actor_coords(defender_context)
    if not epicenter_coords:
        return False

    # 2. Find targets
    all_targets = []
    # Default to hitting everyone (or filter by faction if needed)
    for p in combat.participants:
         try:
            _, p_context = get_actor_context(p.actor_id)
            if p_context.get("current_hp", 0) > 0:
                all_targets.append(p_context)
         except:
            continue

    # 3. Apply to targets in range
    targets_hit = 0
    for target_ctx in all_targets:
        target_coords = _get_actor_coords(target_ctx)
        distance = _calculate_distance(epicenter_coords, target_coords)

        if distance <= aoe_range:
            targets_hit += 1
            target_hit_id = target_ctx.get("id")
            
            # Roll Save
            stat_score = get_stat_score(target_ctx, save_stat)
            stat_mod = rules_core.calculate_modifier(stat_score)
            roll = random.randint(1, 20)
            total = roll + stat_mod

            if total >= dc:
                log.append(f"{target_hit_id} SAVED ({total} vs DC {dc}) against {status_id}.")
            else:
                log.append(f"{target_hit_id} FAILED to save ({total}) and is {status_id}!")
                services.apply_status_to_target(target_hit_id, status_id)

    if targets_hit == 0:
        log.append("...but nothing was in range!")

    return True

# --- Utility / Special Handlers ---

def _handle_effect_summon_creature(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str,
    target_id: str, # The target acts as the spawn point
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict
) -> bool:
    """
    Handles abilities that spawn a new NPC into the combat encounter.
    The summoned creature is immediately added to the turn order.
    """
    npc_template_id = effect.get("npc_template_id")
    if not npc_template_id:
        log.append("Summon failed: No NPC template specified.")
        return False

    # 1. Determine spawn coordinates and location ID
    spawn_coords = _get_actor_coords(defender_context)
    if not spawn_coords:
        log.append(f"Summon failed: Could not determine spawn point for {target_id}.")
        return False

    location_id = combat.location_id

    try:
        # 2. Get generation parameters and generate full NPC template
        template_lookup = services.get_npc_generation_params(npc_template_id)
        generation_params = template_lookup.get("generation_params")

        if not generation_params:
            raise ValueError(f"No generation parameters found for {npc_template_id}")

        full_npc_template = services.generate_npc_template(generation_params)

        npc_max_hp = full_npc_template.get("max_hp", 10)

        # 3. Spawn NPC into World Module
        spawn_data = schemas.OrchestrationSpawnNpc(
            template_id=npc_template_id,
            location_id=location_id,
            coordinates=spawn_coords,
            current_hp=npc_max_hp,
            max_hp=npc_max_hp,
            behavior_tags=full_npc_template.get("behavior_tags", ["aggressive"]),
        )
        npc_instance_data = services.spawn_npc_in_world(spawn_data)

        # 4. Roll Initiative
        actor_id_str = f"npc_{npc_instance_data.get('id')}"
        stats_for_init = _extract_initiative_stats(full_npc_template.get("stats", {}))
        init_result = services.roll_initiative(**stats_for_init)
        initiative_total = init_result.get("total_initiative", 0)

        # 5. Add to Combat State (Database)
        crud.create_combat_participant(
            db,
            combat_id=combat.id,
            actor_id=actor_id_str,
            actor_type="npc",
            initiative=initiative_total
        )

        # 6. Update Turn Order (in-memory list)
        combat.turn_order.append(actor_id_str)

        # NOTE: It's technically more correct to insert the new actor into the
        # turn order based on initiative, but for simplicity, appending
        # ensures they get a turn in the next full round.

        # Save the updated turn order back to the database
        crud.update_combat_encounter(db, combat.id, {"turn_order": combat.turn_order})


        log.append(f"A {full_npc_template.get('name')} is summoned at {spawn_coords}!")
        return True

    except Exception as e:
        logger.exception(f"Failed to handle summon effect: {e}")
        log.append(f"Summon failed due to an engine error: {e}")
        return False

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

    # --- THIS IS NO LONGER A STUB ---
    if target_id.startswith("player_"):
        # This calls the service layer to update the character's temp_hp via CRUD.
        services.apply_temp_hp_to_character(target_id, amount)
        log.append(f"{target_id} gains {amount} Temporary HP.")
    elif target_id.startswith("npc_"):
        services.apply_temp_hp_to_npc(int(target_id.split("_")[1]), amount)
        log.append(f"{target_id} gains {amount} Temporary HP.")

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
    """Replaced Stub: Logs reaction damage without full implementation."""
    log.append(f"REACTION: Triggered '{effect.get('trigger', 'Damage Reaction')}', but full implementation is pending. (Action proceeds)")
    return False
def _handle_effect_reaction_move_ally(
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Replaced Stub: Logs reaction move without full implementation."""
    log.append(f"REACTION: Triggered '{effect.get('trigger', 'Move Ally Reaction')}', but full implementation is pending. (Action proceeds)")
    return False
def _handle_effect_reaction_contest(
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Replaced Stub: Logs reaction contest without full implementation."""
    log.append(f"REACTION: Triggered '{effect.get('trigger', 'Contest Reaction')}', but full implementation is pending. (Action proceeds)")
    return False

def _handle_effect_create_trap(
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict, # This is the context of the targeted position
    log: List[str],
    effect: Dict) -> bool:

    trap_template_id = effect.get("trap_template_id")
    if not trap_template_id:
        log.append(f"Cannot create trap: missing trap_template_id.")
        return False

    # 1. Determine spawn coordinates and location ID
    location_id = defender_context.get("current_location_id") or defender_context.get("location_id")
    coords = _get_actor_coords(defender_context) # Get position from the targeted context

    if not location_id or not coords:
        log.append(f"Could not determine location or coordinates to place trap. Effect fails.")
        return False

    try:
        trap_request = schemas.TrapInstanceCreate(
            template_id=trap_template_id,
            location_id=location_id,
            coordinates=coords,
        )
        # Call the world service to instantiate the trap
        services.spawn_trap_in_world(trap_request)
        log.append(f"{actor_id} successfully places a trap: {trap_template_id} at {coords[0]},{coords[1]}.")
        return True
    except Exception as e:
        log.append(f"Failed to create trap: {e}")
        return False

def _handle_effect_special_move(
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    """Replaced Stub: Logs special move without full implementation."""
    effect_id = effect.get("effect_id", "unknown_move")
    log.append(f"SPECIAL ACTION: {effect_id} executed. Custom logic handling is needed for narrative effects.")
    return True

# --- ADD THESE NEW HANDLERS ---
def _handle_effect_apply_injury(target_id: str, log: List[str], effect: Dict) -> bool:
    """
    Handles effects that directly apply an injury.
    e.g., Chaos T9 "Full Entropy"
    """
    injury_location = effect.get("location", "Torso")
    injury_severity = effect.get("severity", "Minor")

    log.append(f"[STUB] {target_id} suffers a {injury_severity} Injury to their {injury_location}!")
    return True

def _handle_effect_repair_injury(target_id: str, log: List[str], effect: Dict) -> bool:
    """
    Handles effects that repair or downgrade an injury.
    e.g., Biomancy T5 "Repair Minor Injury"
    """
    severity_to_remove = effect.get("severity", "Minor")
    log.append(f"[STUB] A {severity_to_remove} Injury on {target_id} is repaired!")
    return True
# --- END ADD ---


def _handle_effect_apply_injury(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict,
) -> bool:
    """
    Handles effects that directly apply an injury.
    e.g., Chaos T9 "Full Entropy"
    """
    injury_location = effect.get("location", "Torso")
    injury_severity = effect.get("severity", "Minor")

    log.append(f"{target_id} suffers a {injury_severity} Injury to their {injury_location}!")

    try:
        # 1. Get injury details from the rules engine
        injury_data = rules_api.get_injury_effects(injury_location, injury_severity)
        if not injury_data:
            log.append(f" -> No injury data found for {injury_severity} {injury_location}.")
            return False

        # 2. Apply the status effects associated with the injury
        for status in injury_data.get("apply_status", []):
            services.apply_status_to_target(target_id, status)
            log.append(f" -> {target_id} is now {status}!")

        # 3. Save the injury to the character's record
        injury_to_save = {
            "location": injury_location,
            "severity": injury_severity,
            "effects": injury_data, # Save the full data for reference
        }
        services.apply_injury_to_target(target_id, injury_to_save)
        return True

    except Exception as e:
        log.append(f" -> Error applying injury: {e}")
        return False

def _handle_effect_repair_injury(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str,
    target_id: str,
    attacker_context: Dict,
    defender_context: Dict,
    log: List[str],
    effect: Dict,
) -> bool:
    """
    Handles effects that repair or downgrade an injury.
    e.g., Biomancy T5 "Repair Minor Injury"
    """
    severity_to_remove = effect.get("severity", "Minor")
    log.append(f"{actor_id} attempts to repair a {severity_to_remove} injury on {target_id}.")

    try:
        # The service function handles finding and removing the injury
        services.remove_injury_from_target(target_id, severity_to_remove)
        log.append(f" -> A {severity_to_remove} Injury on {target_id} is repaired!")

        # Note: This simple version doesn't remove the status effects.
        # A full implementation would require tracking which status came from where.

        return True
    except Exception as e:
        log.append(f" -> Error repairing injury: {e}")
        return False


def _handle_effect_resource_heal(target_id: str, log: List[str], effect: Dict) -> bool:
    """Handles effects that restore a character's resource pool (e.g., Stamina, Chi)."""
    resource_id = effect.get("resource")
    amount_str = effect.get("amount", "1d4")
    heal_amount = _roll_dice_string(amount_str)

    if not resource_id:
        log.append(f"Resource heal failed: missing resource ID.")
        return False

    _, target_context = get_actor_context(target_id)
    current_pools = target_context.get("resource_pools", {})
    pool_data = current_pools.get(resource_id, {"current": 0, "max": 10})

    max_value = pool_data.get("max", 10)
    # Clamp the new value between current + amount and the max
    new_value = min(max_value, pool_data.get("current", 0) + heal_amount)

    if target_id.startswith("player_"):
        services.update_character_resource_pool(target_id, resource_id, new_value)
    elif target_id.startswith("npc_"):
        # NPCs are handled by world_api via their ID
        services.update_npc_resource_pool(int(target_id.split("_")[1]), resource_id, new_value)

    log.append(f"{target_id} gains {heal_amount} {resource_id}, reaching {new_value}/{max_value}.")
    return True

def _handle_effect_apply_status_roll_with_stat(target_id: str, log: List[str], effect: Dict) -> bool:
    """
    Applies a status if a target fails a save based on a specified STAT
    (e.g., Willpower save vs DC 14 to resist Taunt).
    """
    status_id = effect.get("status_id")
    save_stat = effect.get("save_stat")
    dc = effect.get("dc", 14)

    if not status_id or not save_stat:
        log.append(f"Status roll failed: missing status_id or save_stat in effect.")
        return False

    _, target_context = get_actor_context(target_id)
    stat_score = get_stat_score(target_context, save_stat)
    stat_mod = rules_core.calculate_modifier(stat_score)

    roll = random.randint(1, 20)
    total = roll + stat_mod

    if total >= dc:
        log.append(f"{target_id} SAVED ({total} vs DC {dc} {save_stat} check) against {status_id}.")
        return False
    else:
        log.append(f"{target_id} FAILED to save ({total}) and is now {status_id}!")
        services.apply_status_to_target(target_id, status_id)
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
    "create_area": _handle_effect_create_area, # Added
    "reaction_contest": _handle_effect_reaction_contest, # Added
    "temp_hp": _handle_effect_temp_hp,
    # "random_status": _handle_effect_random_status,
    "random_stat_debuff": _handle_effect_random_stat_debuff,
    "summon": _handle_effect_summon_creature,

    # Complex Stubs (Re-used for special_action/roll)
    "reaction_damage": _handle_effect_reaction_damage,
    "reaction_move_ally": _handle_effect_reaction_move_ally,
    "reaction_contest": _handle_effect_reaction_contest,

    # --- UPDATE THIS SECTION ---
    "special_move": _handle_effect_special_move, # Default "special_move"
    "special_action": _handle_effect_special_move, # Default "special_action"
    "special_action_roll": _handle_effect_special_move,

    # --- ADD THESE NEW KEYS ---
    "apply_injury": _handle_effect_apply_injury,
    "repair_injury": _handle_effect_repair_injury,
    "resource_heal": _handle_effect_resource_heal,
    "apply_status_roll_with_stat": _handle_effect_apply_status_roll_with_stat,
}

# --- ADD THE NEW REACTION CHECKER FUNCTION ---
def _check_and_trigger_reactions(
    db: Session,
    combat: models.CombatEncounter,
    trigger_event: str,
    trigger_actor_id: str, # The actor who *caused* the event (e.g., the mover)
    log: List[str],
    event_data: Optional[Dict[str, Any]] = None) -> bool:
    """
    Checks all participants for readied or innate reactions to an event.
    Returns True if a reaction was triggered, False otherwise.
    """
    logger.info(f"Checking reactions for event: {trigger_event} (Actor: {trigger_actor_id})")
    event_data = event_data or {}
    reaction_triggered = False

    try:
        _, trigger_actor_context = get_actor_context(trigger_actor_id)
    except HTTPException:
        return False # Mover not found

    # Iterate over ALL participants to see if any of them want to react
    for participant in combat.participants:
        # Actors can't react to their own actions
        if participant.actor_id == trigger_actor_id:
            continue

        try:
            _, reactor_context = get_actor_context(participant.actor_id)
            if reactor_context.get("current_hp", 0) <= 0:
                continue # Defeated actors can't react
        except HTTPException:
            continue # Reactor not found

        # 1. Check for Innate Reactions (from Status Effects)
        reactor_statuses = reactor_context.get("status_effects", [])
        for status in reactor_statuses:
            if status == "Threat Zone":
                # Effect format: "reaction_trigger:actor_move_exit:3:attack"
                effect_str = "reaction_trigger:actor_move_exit:3:attack" # Hardcoded from status_effects.json
                parts = effect_str.split(':')
                if len(parts) == 4 and parts[1] == "actor_move_exit" and trigger_event == "actor_move":

                    threat_range = int(parts[2])
                    old_coords = event_data.get("old_coords")
                    new_coords = _get_actor_coords(trigger_actor_context) # Mover's new position
                    reactor_coords = _get_actor_coords(reactor_context)

                    if not old_coords or not new_coords or not reactor_coords:
                        continue

                    # Check if the mover left the zone
                    old_dist = _calculate_distance(old_coords, reactor_coords)
                    new_dist = _calculate_distance(new_coords, reactor_coords)

                    if old_dist <= threat_range and new_dist > threat_range:
                        log.append(f"REACTION: {participant.actor_id}'s 'Threat Zone' triggers against {trigger_actor_id}!")
                        _handle_basic_attack(db, combat, participant.actor_id, trigger_actor_id, reactor_context, trigger_actor_context, log)
                        reaction_triggered = True

        # 2. Check for Player-Readied Actions
        if participant.readied_action:
            readied = participant.readied_action

            if trigger_event == "actor_move" and readied.get("trigger") == "enemy_moves_in_range":
                # (This logic also needs old/new coord check, but we'll implement that next)
                log.append(f"REACTION: {participant.actor_id}'s readied action triggers!")

                crud.set_readied_action(db, combat.id, participant.actor_id, None)

                # Execute the readied action (attack)
                try:
                    _handle_basic_attack(db, combat, participant.actor_id, trigger_actor_id, reactor_context, trigger_actor_context, log)
                    reaction_triggered = True
                except Exception as e:
                    log.append(f"  -> Readied action failed: {e}")

    return reaction_triggered

# --- UPDATE FUNCTION SIGNATURE ---
def _check_for_interrupt_reactions(db: Session, combat: models.CombatEncounter, attacker_id: str, target_id: str, attack_result: Dict, log: List[str]) -> bool:
    """
    Checks if a successful attack triggers any defensive reactions that could interrupt
    the flow. Placeholder implementation relies on simple ability list check.
    """
    target_type, defender_context = get_actor_context(target_id)

    if "Bastion_Reaction_T2" in defender_context.get("abilities", []):
        if attack_result.get("outcome") in ["hit", "solid_hit", "critical_hit"]:
            log.append("REACTION TRIGGERED: Bastion T2: Spiked Deflection (Placeholder)")

            # Execute the reaction's generic effect (self-damage to attacker)
            effect = {"type": "direct_damage", "amount": "1d4", "damage_type": "physical"}
            _handle_effect_direct_damage(attacker_id, log, effect)

            return False # Does NOT interrupt the original attack damage flow (Structural decision)

    return False # No interruption

def _handle_basic_attack(
    db: Session,
    combat: models.CombatEncounter,
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
    # --- TALENT BONUSES ---
    # Calculate bonuses from talents for both attacker and defender
    attacker_talent_bonuses = services.rules_api.calculate_talent_bonuses(
        attacker_context,
        "attack_roll",
        tags=[weapon_category, weapon_type, "Melee" if weapon_type == "melee" else "Ranged"]
    )
    defender_talent_bonuses = services.rules_api.calculate_talent_bonuses(
        defender_context,
        "defense_roll",
        tags=[armor_category]
    )

    # Add talent bonuses to the base modifiers
    # Note: We are adding to the 'misc' bonus fields in the request
    # Attacker
    attack_bonus_val = attacker_talent_bonuses.get("attack_roll_bonus", 0)

    # Defender
    defense_bonus_val = defender_talent_bonuses.get("defense_roll_bonus", 0)

    # Pre-calculate scores for clarity and reuse
    attacker_stat_score = get_stat_score(attacker_context, weapon_data["skill_stat"])
    attacker_skill_rank = get_skill_rank(attacker_context, weapon_data["skill"])
    defender_stat_score = get_stat_score(defender_context, armor_data["skill_stat"])
    defender_skill_rank = get_skill_rank(defender_context, armor_data["skill"])

    # 4. Roll Attack
    attack_params = {
        "attacker_attacking_stat_score": attacker_stat_score,
        "attacker_skill_rank": attacker_skill_rank,
        "attacker_attack_roll_bonus": ability_mod.get("attack_bonus", 0) + attack_bonus_val, # Add talent bonus here
        "attacker_attack_roll_penalty": 0,
        "attacker_weapon_penalty": weapon_data.get("penalty", 0), # New field
        "defender_defending_stat_score": defender_stat_score,
        "defender_skill_rank": defender_skill_rank,
        "defender_defense_roll_bonus": defense_bonus_val, # Add talent bonus here
        "defender_defense_roll_penalty": 0,
        "defender_weapon_penalty": 0 # This is usually 0 unless specific mechanics apply
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

        # --- NEW: INTERRUPT REACTION CHECK (Mid-action) ---
        is_interrupted = _check_for_interrupt_reactions(db, combat, actor_id, target_id, attack_result, log)

        if is_interrupted:
            return True # Action was interrupted, stop damage calculation
        # --- END INTERRUPT CHECK ---

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

        # --- REACTION CALL (2) ---
        # Check for reactions to the *miss* (target_id is the one missed)
        _check_and_trigger_reactions(db, combat, "attack_miss", actor_id, log, event_data={"target_id": target_id})
        # --- END REACTION CALL ---

        return False

def _process_status_effects_on_turn_start(db: Session, combat: models.CombatEncounter, actor_id: str, log: List[str]) -> bool:
    """Applies continuous effects (like DOT) and handles turn-based duration."""
    actor_type, actor_context = get_actor_context(actor_id)
    current_statuses = actor_context.get("status_effects", [])
    statuses_to_remove = []

    all_status_defs = services.get_all_status_effects()

    for status_name in current_statuses:
        status_data = all_status_defs.get(status_name)
        if not status_data: continue

        # 1. Apply Damage Over Time (DOT)
        for effect_str in status_data.get("effects", []):
            if effect_str.startswith("damage_over_time:start_turn"):
                try:
                    amount = int(effect_str.split(":")[2])

                    if actor_type == "player":
                        services.apply_damage_to_character(actor_id, amount)
                    elif actor_type == "npc":
                        npc_id = int(actor_id.split("_")[1])
                        services.apply_damage_to_npc(npc_id, amount)

                    log.append(f"DOT: {actor_context.get('name')} suffers {amount} damage from {status_name}!")
                except Exception as e:
                    logger.error(f"Failed to process DOT effect for {status_name}: {e}")

        # 2. Handle Turn-Based Duration (for TempDebuff statuses)
        if status_name.startswith("TempDebuff_"):
            try:
                # Note: The status name is the tracker (TempDebuff_STATNAME_AMOUNT_DURATION)
                _, _, _, duration_str = status_name.split("_")
                remaining_duration = int(duration_str) - 1

                if remaining_duration <= 0:
                    statuses_to_remove.append(status_name)
                    log.append(f"Status {status_name} has expired.")
                else:
                    # Save a NEW status ID to track the decremented duration
                    new_status_id = status_name.rsplit('_', 1)[0] + f"_{remaining_duration}"
                    services.apply_status_to_target(actor_id, new_status_id)
                    statuses_to_remove.append(status_name)
            except Exception as e:
                logger.error(f"Failed to process duration for {status_name}: {e}")

    # Remove all expired statuses atomically
    for expired_status in statuses_to_remove:
        if actor_type == "player":
            services.remove_status_from_character(actor_id, expired_status)
        else:
            services.remove_status_from_npc(int(actor_id.split("_")[1]), expired_status)

    return len(statuses_to_remove) > 0

# --- Main Action Handler (Original/Core) ---
def handle_player_action(db: Session, combat: models.CombatEncounter, actor_id: str, action: schemas.PlayerActionRequest) -> schemas.PlayerActionResponse:
    log = []

    current_actor_id = combat.turn_order[combat.current_turn_index]
    if actor_id != current_actor_id:
        raise HTTPException(status_code=403, detail=f"It is not {actor_id}'s turn.")

    # --- CRITICAL: PROCESS CONTINUOUS STATUS EFFECTS ---
    _process_status_effects_on_turn_start(db, combat, actor_id, log)
    # ---------------------------------------------------

    # Refresh context *after* status processing, before checking Staggered/HP
    actor_type, attacker_context = get_actor_context(actor_id)

    if attacker_context.get('current_hp', 0) <= 0:
        log.append(f"{actor_id} was defeated by continuous effects!")
        combat_over = check_combat_end_condition(db, combat, log)
        db.commit()
        return schemas.PlayerActionResponse(success=True, message="Defeated.", log=log, new_turn_index=combat.current_turn_index, combat_over=combat_over)


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

    # --- ADD THIS NEW ACTION HANDLER ---
    if action.action == "ready":
        # This is a simple version. We'll expand it to let the user
        # choose the trigger and the specific action.
        ready_action_data = {
            "trigger": "enemy_moves_in_range",
            "action": "attack"
        }
        # Use details from client if provided
        if action.ready_action_details:
            ready_action_data = action.ready_action_details

        crud.set_readied_action(db, combat.id, actor_id, ready_action_data)
        log.append(f"{actor_id} readies an action ({ready_action_data['trigger']}).")

        # Advancing the turn is the same as 'wait'
        return handle_no_action(db, combat, actor_id, reason="readies an action")
    # --- END ADD ---

    target_id = action.target_id
    if (action.action in ["attack", "use_ability", "use_item"]) and (not target_id):
        log.append(f"Action '{action.action}' requires a target, but none provided. Waiting instead.")
        return handle_no_action(db, combat, actor_id)

    # --- ADD MOVE ACTION ---
    if action.action == "move":
        coords = action.coordinates
        if not coords or len(coords) != 2:
            log.append("Invalid move coordinates. Waiting instead.")
            return handle_no_action(db, combat, actor_id)

        if not _is_passable_and_in_bounds(combat.location_id, coords[0], coords[1], log):
            log.append(f"Move failed. Waiting instead.")
            return handle_no_action(db, combat, actor_id)

        try:
            # --- REACTION CALL (3) ---
            # Get old coordinates *before* updating the actor's position
            old_coords = _get_actor_coords(attacker_context)

            # Update the actor's position in the DB
            if actor_id.startswith("player_"):
                services.character_api.update_character_location(actor_id, combat.location_id, coords)
            elif actor_id.startswith("npc_"):
                services.world_api.update_npc_state(int(actor_id.split('_')[1]), {"coordinates": coords})

            log.append(f"{actor_id} moves to ({coords[0]}, {coords[1]}).")

            # Check if this move triggered anyone's reaction
            _check_and_trigger_reactions(
                db, combat, "actor_move", actor_id, log,
                event_data={"old_coords": old_coords}
            )

        except Exception as e:
            log.append(f"Error during move: {e}")

        # Move action completes the turn
        combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
        combat_over = check_combat_end_condition(db, combat, log)
        db.commit()
        db.refresh(combat)

        return schemas.PlayerActionResponse(
            success=True,
            message=f"{actor_id} moved.",
            log=log,
            new_turn_index=combat.current_turn_index,
            combat_over=combat_over
        )
    # --- END ADD ---

    try:
        defender_context = attacker_context # Default for self/area spells
        if target_id:
            target_type, defender_context = get_actor_context(target_id)
            hp = defender_context.get("current_hp", 0)
            if hp <= 0 and target_type == "npc":
                 raise HTTPException(status_code=400, detail=f"Target {target_id} is already defeated.")

        if action.action == "attack":
            log.append(f"{actor_id} targets {target_id} with an attack.")
            _handle_basic_attack(db, combat, actor_id, target_id, attacker_context, defender_context, log)

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
                            # --- REFACTORED: Pass db and combat to all handlers that need it ---
                            if effect_type in (
                                "modify_attack",
                                "aoe_damage",
                                "summon",
                                "special_move",
                                "create_trap",
                                "move_self",
                                "reaction_damage",
                                "reaction_move_ally",
                                "move_target_roll",
                                "reaction_contest",
                                "apply_injury",
                                "repair_injury"
                            ):
                                handler(db, combat, actor_id, target_id, attacker_context, defender_context, log, effect)
                            else:
                                # Handlers that only need the target's ID and the effect
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

def determine_npc_action(
    db: Session,
    combat: models.CombatEncounter,
    npc_id: str,
    npc_context: Dict
) -> Dict:
    """
    Determines the best action for an NPC based on its AI tag and current state.
    Returns a dictionary representing the action (similar to PlayerActionRequest).
    """
    ai_tag = npc_context.get("ai_tag", "basic_melee")
    # Default fallback
    action = {"action": "pass_turn", "target_id": None}

    # Identify potential targets (players)
    enemies = []
    for p in combat.participants:
        if p.actor_id.startswith("player_"):
            try:
                _, p_context = get_actor_context(p.actor_id)
                if p_context.get("current_hp", 0) > 0:
                    enemies.append(p.actor_id)
            except:
                continue

    if not enemies:
        return action

    # Simple targeting logic: closest or random
    target_id = random.choice(enemies)
    
    # AI Logic
    if ai_tag == "aggressive":
        # Try to attack
        # Check if has melee attack
        action = {"action": "attack", "target_id": target_id, "ability_id": "Basic Melee"}
    elif ai_tag == "caster":
        # Try to cast a spell if available, else attack
        action = {"action": "attack", "target_id": target_id, "ability_id": "Basic Ranged"}
    else:
        # Basic behavior
        action = {"action": "attack", "target_id": target_id, "ability_id": "Basic Melee"}

    return action

def handle_npc_turn(
    db: Session,
    combat: models.CombatEncounter,
    npc_id: str
) -> List[str]:
    """
    Executes the turn for an NPC.
    1. Process start-of-turn status effects.
    2. Determine action.
    3. Execute action.
    4. Check end of combat.
    5. Advance turn.
    """
    log = []
    log.append(f"--- {npc_id}'s Turn ---")

    try:
        _, npc_context = get_actor_context(npc_id)
        
        # 1. Status Effects
        _process_status_effects_on_turn_start(db, combat, npc_id, log)
        
        # Check if dead after status effects
        if npc_context.get("current_hp", 0) <= 0:
             log.append(f"{npc_id} succumbed to status effects.")
             combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
             return log

        # 2. Determine Action
        action_data = determine_npc_action(db, combat, npc_id, npc_context)
        action_type = action_data.get("action")
        target_id = action_data.get("target_id")
        ability_id = action_data.get("ability_id")

        # 3. Execute Action
        if action_type == "pass_turn":
            log.append(f"{npc_id} passes their turn.")
        elif action_type == "attack":
            # Reuse logic from handle_player_action or call specific helpers
            if target_id:
                _, target_context = get_actor_context(target_id)
                # Assuming basic attack for now
                _handle_basic_attack(db, combat, npc_id, target_id, npc_context, target_context, log)
            else:
                log.append(f"{npc_id} could not find a target.")
        
        elif action_type == "move":
             # NPC movement logic (simplified)
             log.append(f"{npc_id} moves.")
             # Implement movement logic here using _handle_effect_move_self or similar
             pass

        # 4. End Turn
        combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
        check_combat_end_condition(db, combat, log)
        db.commit()
        db.refresh(combat)

    except Exception as e:
        log.append(f"Error during {npc_id}'s turn: {e}")
        logger.exception(f"NPC Turn Error: {e}")
        # Ensure turn advances even on error to prevent infinite loops
        combat.current_turn_index = (combat.current_turn_index + 1) % len(combat.turn_order)
        db.commit()

    return log