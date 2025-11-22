import os

file_path = r"c:\Users\krazy\Documents\GitHub\ShatterlandsTTRPGAI\AI-TTRPG\monolith\modules\story_pkg\combat_handler.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the split point at the corrupted if statement
split_index = -1
for i, line in enumerate(lines):
    if "if not _is_passable_and_in_bounds(loc_id, new_x, new_y, log):" in line:
        # Check if the next line is the corrupted jump
        if i + 2 < len(lines) and "if not status_id or not save_stat: return False" in lines[i+2]:
            split_index = i + 1
            break
        # Or if it's just the next line (empty line in between)
        if i + 2 < len(lines) and "if not status_id or not save_stat: return False" in lines[i+2]:
             split_index = i + 1
             break

if split_index == -1:
    # Fallback search for the context
    for i, line in enumerate(lines):
         if "if not _is_passable_and_in_bounds(loc_id, new_x, new_y, log):" in line:
             split_index = i + 1
             break

if split_index == -1:
    print("Could not find split point!")
    exit(1)

part1 = lines[:split_index]
# We need to skip the corrupted lines that followed.
# The corrupted lines were:
# 400: 
# 401:     if not status_id or not save_stat: return False
# ...
# We need to find where the next valid function starts, which seems to be `_handle_effect_aoe_status_roll` body.
# Actually, looking at the view_file output, line 401 IS the body of `_handle_effect_aoe_status_roll`.
# So we need to insert the missing block and then keep the rest of the file starting from line 401.

part2 = lines[split_index:]

missing_block = """            return False

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

def _get_targets_in_aoe(
    combat: models.CombatEncounter,
    center_target_id: str,
    shape: str,
    radius: int,
    target_type: str = "all" # "all", "enemy", "ally", "ally_or_self"
) -> List[Tuple[str, Dict]]:
    \"\"\"
    Helper to find all actors within a certain radius of a target actor.
    Returns a list of (actor_id, actor_context).
    \"\"\"
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
    \"\"\"Chebyshev distance (chessboard distance) for grid movement.\"\"\"
    return max(abs(coords1[0] - coords2[0]), abs(coords1[1] - coords2[1]))

def _handle_effect_aoe_status_apply(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    \"\"\"Handles AoE application of a status (no roll) (e.g., Cunning T4).\"\"\"
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

def _handle_effect_aoe_status_roll(
    db: Session,
    combat: models.CombatEncounter,
    actor_id: str, target_id: str, attacker_context: Dict, defender_context: Dict, log: List[str], effect: Dict) -> bool:
    \"\"\"Handles AoE application of a status with an individual save roll (e.g., Evocation T2).\"\"\"
    """

# Ensure the missing block ends with a newline if needed
if not missing_block.endswith("\n"):
    missing_block += "\n"

new_content = "".join(part1) + missing_block + "".join(part2)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("File fixed successfully!")
