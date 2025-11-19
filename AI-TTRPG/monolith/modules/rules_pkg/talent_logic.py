# AI-TTRPG/monolith/modules/rules_pkg/talent_logic.py
from typing import Dict, List, Any, Optional
import logging
from . import data_loader

logger = logging.getLogger("monolith.rules.talent_logic")

def calculate_talent_bonuses(
    character_context: Dict[str, Any],
    action_type: str,
    tags: Optional[List[str]] = None
) -> Dict[str, int]:
    """
    Calculates the total bonuses from a character's active talents for a specific action.

    Args:
        character_context: The full character context dictionary (including 'talents').
        action_type: The type of action being performed (e.g., 'contested_check', 'skill_check', 'damage_roll').
        tags: A list of tags associated with the action (e.g., ['Might', 'Intimidation', 'Melee']).

    Returns:
        A dictionary of bonuses to apply, e.g., {'attack_roll_bonus': 2, 'damage_bonus': 1}.
    """
    bonuses = {
        "attack_roll_bonus": 0,
        "defense_roll_bonus": 0,
        "damage_bonus": 0,
        "skill_check_bonus": 0,
        "stat_check_bonus": 0,
        "initiative_bonus": 0
    }
    
    tags = tags or []
    active_talents = character_context.get("talents", [])
    
    # If talents are just strings (names), we might need to look them up. 
    # However, character_context['talents'] usually comes from find_eligible_talents 
    # which returns TalentInfo objects (or dicts if serialized).
    # Let's assume for now we need to match names against the loaded data if the context only has names,
    # OR the context has the full talent data.
    # Given the current architecture, find_eligible_talents returns a list of objects/dicts with 'name', 'source', 'effect'.
    # It DOES NOT currently include the structured 'modifiers' because we haven't added them to the return yet.
    
    # STRATEGY: We need access to the full talent data to check modifiers.
    # Since this function is in rules_pkg, we can't easily circular import data_loader.
    # We will assume the caller passes the FULL talent data map or we rely on the character_context 
    # having enriched talent data.
    
    # BETTER STRATEGY: The caller (combat_handler) has access to rules_api.
    # But this logic belongs in rules. 
    # We will rely on `rules_pkg.data_loader` being available or passed in.
    # For simplicity, let's assume we can get the global data from data_loader if needed, 
    # but ideally we want this pure.
    
    all_talents_data = data_loader.TALENT_DATA
    if not all_talents_data:
        # Fallback if not loaded (e.g. in tests without full startup)
        logger.warning("Talent data not loaded in talent_logic.")
        return bonuses

    # Helper to flatten the talent structure for lookup
    # This might be slow if done every time. Ideally this map is pre-calculated.
    # For now, we'll do a quick lookup.
    
    # We need to find the 'modifiers' for each talent the character has.
    character_talent_names = set()
    for t in active_talents:
        if isinstance(t, dict):
            character_talent_names.add(t.get("name"))
        elif isinstance(t, str):
            character_talent_names.add(t)
            
    # Iterate through all defined talents to find matches (inefficient but robust for now)
    # TODO: Optimize this with a pre-built map in data_loader
    
    found_modifiers = []
    
    def check_talent_group(group):
        for t in group:
            if t.get("talent_name") in character_talent_names or t.get("name") in character_talent_names:
                if "modifiers" in t:
                    found_modifiers.extend(t["modifiers"])

    # 1. Single Stat
    for t in all_talents_data.get("single_stat_mastery", []):
        if t.get("talent_name") in character_talent_names:
            if "modifiers" in t:
                found_modifiers.extend(t["modifiers"])
                
    # 2. Dual Stat
    for t in all_talents_data.get("dual_stat_focus", []):
        if t.get("talent_name") in character_talent_names:
            if "modifiers" in t:
                found_modifiers.extend(t["modifiers"])
                
    # 3. Skill Mastery
    for category in all_talents_data.get("single_skill_mastery", {}).values():
        for skill_group in category:
            check_talent_group(skill_group.get("talents", []))

    # Apply Modifiers
    for mod in found_modifiers:
        mod_type = mod.get("type")
        mod_bonus = mod.get("bonus", 0)
        
        # Check conditions
        # 1. Action Type Match
        if mod_type != action_type and mod_type != "all":
             # Allow specific mapping?
             # e.g. 'skill_check' modifier applies if action is 'contested_check' AND involves that skill?
             pass

        # 2. Tag Match (if modifier specifies required tags)
        required_tags = mod.get("required_tags", [])
        if required_tags:
            if not any(tag in tags for tag in required_tags):
                continue
                
        # 3. Specific Stat/Skill Match
        target_stat = mod.get("stat")
        if target_stat and target_stat not in tags:
            continue
            
        target_skill = mod.get("skill")
        if target_skill and target_skill not in tags:
            continue

        # Apply
        if mod_type == "contested_check":
            # This could be attack or defense depending on context
            # We'll assume the caller knows what they are doing or we map it
            bonuses["attack_roll_bonus"] += mod_bonus
            # If it's a defense check, the caller should map 'attack_roll_bonus' to defense?
            # Or we add explicit keys.
            bonuses["defense_roll_bonus"] += mod_bonus
            
        elif mod_type == "attack_roll":
            bonuses["attack_roll_bonus"] += mod_bonus
            
        elif mod_type == "defense_roll":
            bonuses["defense_roll_bonus"] += mod_bonus
            
        elif mod_type == "damage":
            bonuses["damage_bonus"] += mod_bonus
            
        elif mod_type == "skill_check":
            bonuses["skill_check_bonus"] += mod_bonus
            
        elif mod_type == "initiative":
            bonuses["initiative_bonus"] += mod_bonus

    return bonuses
