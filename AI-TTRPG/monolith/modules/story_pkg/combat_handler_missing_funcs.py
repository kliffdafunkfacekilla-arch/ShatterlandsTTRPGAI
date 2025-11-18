
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
