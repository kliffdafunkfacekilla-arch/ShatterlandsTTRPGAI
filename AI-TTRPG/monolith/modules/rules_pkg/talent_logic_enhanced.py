"""
Enhanced Talent Logic with Generic Action Resolver

This module provides:
- Effect handler registry for all modifier types
- Generic action resolver for talent/ability execution  
- Helper functions for dice rolling, stat modifiers, conditions
- Integration with RuleSetContainer for data-driven talents
"""
import logging
import random
from typing import Dict, List, Any, Optional, Callable
from .data_loader_enhanced import get_rules
from .models_inventory import PassiveModifier
from ..save_schemas import CharacterSave

logger = logging.getLogger("monolith.rules.talent_logic_enhanced")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def roll_dice(dice_string: str) -> int:
    """Parse and roll dice (e.g., '3d6', '1d20+5')
    
    Args:
        dice_string: Dice notation like "3d6", "1d20+5", or "2d8-2"
        
    Returns:
        Total roll result
    """
    try:
        # Handle flat bonuses
        bonus = 0
        if '+' in dice_string:
            dice_string, bonus_str = dice_string.split('+')
            bonus = int(bonus_str.strip())
        elif '-' in dice_string and dice_string.count('-') == 1:
            dice_string, bonus_str = dice_string.split('-')
            bonus = -int(bonus_str.strip())
        
        # Parse dice (e.g., "3d6")
        if 'd' not in dice_string:
            return int(dice_string) + bonus
        
        num_dice, die_size = dice_string.lower().split('d')
        num_dice = int(num_dice.strip() or "1")
        die_size = int(die_size.strip())
        
        # Roll
        total = sum(random.randint(1, die_size) for _ in range(num_dice))
        return total + bonus
        
    except Exception as e:
        logger.error(f"Failed to parse dice string '{dice_string}': {e}")
        return 0


def get_stat_modifier(character: CharacterSave, stat_name: str) -> int:
    """Get stat modifier from character
    
    Args:
        character: Character data
        stat_name: Stat name (e.g., "Might")
        
    Returns:
        Stat modifier value (typically stat score)
    """
    return character.stats.get(stat_name, 0)


def check_condition(character: CharacterSave, condition: str, context: Dict = None) -> bool:
    """Evaluate a condition string
    
    Args:
        character: Character to check
        condition: Condition string (e.g., "is_leader", "in_combat")
        context: Additional context data
        
    Returns:
        Whether condition is met
    """
    context = context or {}
    
    # Simple condition checks
    if condition == "is_leader":
        return context.get("is_leader", False)
    elif condition == "in_combat":
        return context.get("in_combat", False)
    elif condition == "finesse_weapon":
        return context.get("weapon_type") == "finesse"
    elif condition == "non_magical":
        return not context.get("is_magical", False)
    
    # Default to True if unknown (permissive)
    logger.warning(f"Unknown condition '{condition}', defaulting to True")
    return True


def apply_resource_cost(character: CharacterSave, resource: str, amount: int) -> bool:
    """Deduct resource cost from character
    
    Args:
        character: Character to modify
        resource: Resource name (e.g., "Stamina", "Chi")
        amount: Amount to deduct
        
    Returns:
        Whether cost was successfully paid
    """
    # This would modify character state - for now just log
    logger.info(f"Resource cost: {amount} {resource} from {character.name}")
    # TODO: Implement actual resource deduction
    return True


# ============================================================================
# EFFECT HANDLERS
# ============================================================================

def _handle_damage_bonus_active(source: CharacterSave, target_id: str, params: Dict, context: Dict) -> Dict:
    """Handle active damage bonus (e.g., spend resource for extra damage)"""
    bonus = params.get("bonus", 0)
    cost_resource = params.get("cost_resource")
    
    # Apply resource cost if specified
    if cost_resource:
        if not apply_resource_cost(source, cost_resource, 1):
            return {"success": False, "error": "Insufficient resources"}
    
    return {
        "type": "damage_modifier",
        "target": target_id,
        "bonus": bonus,
        "source": "talent"
    }


def _handle_resource_restore(source: CharacterSave, trigger: str, params: Dict, context: Dict) -> Optional[Dict]:
    """Handle resource restoration on trigger"""
    required_trigger = params.get("trigger")
    
    if context.get("trigger") == required_trigger:
        return {
            "type": "resource_restore",
            "resource": params["resource"],
            "amount": params["amount"],
            "target": source.id
        }
    return None


def _handle_unlock_action(source: CharacterSave, action_id: str, params: Dict, context: Dict) -> Dict:
    """Handle unlocking a new action"""
    return {
        "type": "action_unlocked",
        "action": params.get("action", action_id),
        "cost_resource": params.get("cost_resource"),
        "cost_action": params.get("cost_action", "major")
    }


def _handle_force_reroll(source: CharacterSave, target_id: str, params: Dict, context: Dict) -> Optional[Dict]:
    """Handle forcing a reroll"""
    trigger = params.get("trigger")
    
    if context.get("trigger") == trigger:
        cost_resource = params.get("cost_resource")
        if cost_resource:
            apply_resource_cost(source, cost_resource, 1)
        
        return {
            "type": "force_reroll",
            "target": target_id,
            "frequency": params.get("frequency", "unlimited")
        }
    return None


def _handle_immunity(source: CharacterSave, effect_type: str, params: Dict, context: Dict) -> Dict:
    """Handle immunity to effects"""
    return {
        "type": "immunity",
        "effect": params.get("effect", effect_type),
        "condition": params.get("condition"),
        "source_types": params.get("source", [])
    }


def _handle_action_enhancement(source: CharacterSave, action: str, params: Dict, context: Dict) -> Dict:
    """Handle action enhancements"""
    return {
        "type": "action_enhancement",
        "action": params.get("action", action),
        "effect": params.get("effect"),
        "frequency": params.get("frequency", "unlimited")
    }


def _handle_ignore_penalty(source: CharacterSave, penalty_type: str, params: Dict, context: Dict) -> Dict:
    """Handle ignoring penalties"""
    return {
        "type": "ignore_penalty",
        "skills": params.get("skills", []),
        "source": params.get("source"),
        "penalty_type": penalty_type
    }


def _handle_reaction_damage(source: CharacterSave, trigger: str, params: Dict, context: Dict) -> Optional[Dict]:
    """Handle reactive damage on trigger"""
    if context.get("trigger") == params.get("trigger"):
        return {
            "type": "reaction_damage",
            "amount": params["amount"],
            "trigger": trigger
        }
    return None


# Effect handler registry - maps modifier types to handler functions
EFFECT_HANDLERS: Dict[str, Callable] = {
    "damage_bonus_active": _handle_damage_bonus_active,
    "resource_restore_on_trigger": _handle_resource_restore,
    "unlock_action": _handle_unlock_action,
    "force_reroll_reactive": _handle_force_reroll,
    "immunity": _handle_immunity,
    "action_enhancement": _handle_action_enhancement,
    "ignore_penalty": _handle_ignore_penalty,
    "reaction_damage": _handle_reaction_damage,
    
    # Passive handlers (return None, handled by calculate_talent_bonuses)
    "skill_check": lambda *args: None,
    "contested_check": lambda *args: None,
    "defense_bonus": lambda *args: None,
    "initiative": lambda *args: None,
    "resource_max": lambda *args: None,
}


# ============================================================================
# GENERIC ACTION RESOLVER
# ============================================================================

def resolve_talent_action(
    source_character: CharacterSave,
    talent_id: str,
    target_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Execute a talent's active effects based on JSON data.
    
    This is the main entry point for talent execution. It:
    1. Looks up talent data from RuleSetContainer
    2. Checks resource costs and conditions
    3. Executes effect handlers for active modifiers
    4. Returns structured result with effects applied
    
    Args:
        source_character: Character using the talent
        talent_id: ID/name of talent to execute
        target_id: Optional target entity ID
        context: Additional context (trigger events, combat state, etc.)
        
    Returns:
        {
            "success": bool,
            "talent_name": str,
            "effects_applied": List[Dict],  # List of effect dictionaries
            "narrative": str,  # Human-readable description
            "state_changes": Dict,  # Specific state mutations needed
            "error": str  # If success=False
        }
    """
    context = context or {}
    
    try:
        # Load talent data
        rules = get_rules()
        talent_data = rules.get_talent(talent_id)
        
        if not talent_data:
            return {
                "success": False,
                "error": f"Talent '{talent_id}' not found"
            }
        
        logger.info(f"Resolving talent: {talent_id} for {source_character.name}")
        
        effects_applied = []
        
        # Get modifiers from talent
        modifiers = talent_data.get("modifiers", [])
        
        for modifier in modifiers:
            mod_type = modifier.get("type")
            
            # Get handler for this modifier type
            handler = EFFECT_HANDLERS.get(mod_type)
            
            if not handler:
                logger.warning(f"No handler for modifier type: {mod_type}")
                continue
            
            # Execute handler
            try:
                effect = handler(
                    source=source_character,
                    target_id=target_id or "",
                    params=modifier,
                    context=context
                )
                
                if effect:  # Handler returned an effect
                    effects_applied.append(effect)
                    
            except Exception as e:
                logger.error(f"Handler failed for {mod_type}: {e}")
                continue
        
        # Build narrative
        talent_name = talent_data.get("talent_name", talent_id)
        effect_desc = talent_data.get("effect", "Unknown effect")
        narrative = f"{source_character.name} uses {talent_name}: {effect_desc}"
        
        return {
            "success": True,
            "talent_name": talent_name,
            "talent_id": talent_id,
            "effects_applied": effects_applied,
            "narrative": narrative,
            "state_changes": {
                "source_id": source_character.id,
                "target_id": target_id
            }
        }
        
    except Exception as e:
        logger.exception(f"Failed to resolve talent '{talent_id}'")
        return {
            "success": False,
            "error": str(e)
        }


def resolve_ability_action(
    source_character: CharacterSave,
    ability_id: str,
    target_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Execute an ability's effects (similar to talents but for abilities)
    
    Args:
        source_character: Character using the ability
        ability_id: ID/name of ability
        target_id: Optional target
        context: Additional context
        
    Returns:
        Same structure as resolve_talent_action
    """
    context = context or {}
    
    try:
        rules = get_rules()
        ability_data = rules.get_ability(ability_id)
        
        if not ability_data:
            return {
                "success": False,
                "error": f"Ability '{ability_id}' not found"
            }
        
        logger.info(f"Resolving ability: {ability_id} for {source_character.name}")
        
        # Abilities can have similar modifier structure
        # For now, return success with basic info
        return {
            "success": True,
            "ability_name": ability_data.get("name", ability_id),
            "ability_id": ability_id,
            "effects_applied": [],
            "narrative": f"{source_character.name} uses {ability_id}",
            "state_changes": {}
        }
        
    except Exception as e:
        logger.exception(f"Failed to resolve ability '{ability_id}'")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# BACKWARD COMPATIBILITY - Keep existing functions
# ============================================================================

# Import existing functions from old talent_logic.py
# These remain unchanged for backward compatibility
from . import data_loader

def calculate_talent_bonuses(
    character_context: Dict[str, Any],
    action_type: str,
    tags: Optional[List[str]] = None
) -> Dict[str, int]:
    """Calculate passive bonuses from talents (existing function)"""
    # Keep existing implementation...
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
    
    all_talents_data = data_loader.TALENT_DATA
    if not all_talents_data:
        return bonuses
    
    character_talent_names = set()
    for t in active_talents:
        if isinstance(t, dict):
            character_talent_names.add(t.get("name"))
        elif isinstance(t, str):
            character_talent_names.add(t)
    
    found_modifiers = []
    
    def extract_mods_if_active(talent_def):
        t_name = talent_def.get("talent_name") or talent_def.get("name")
        if t_name in character_talent_names:
            if "modifiers" in talent_def:
                found_modifiers.extend(talent_def["modifiers"])
    
    for t in all_talents_data.get("single_stat_mastery", []):
        extract_mods_if_active(t)
    
    for t in all_talents_data.get("dual_stat_focus", []):
        extract_mods_if_active(t)
    
    for category_list in all_talents_data.get("single_skill_mastery", {}).values():
        for skill_group in category_list:
            for talent_def in skill_group.get("talents", []):
                extract_mods_if_active(talent_def)
    
    for mod in found_modifiers:
        mod_type = mod.get("type")
        mod_bonus = mod.get("bonus", 0)
        
        is_applicable = False
        
        if action_type == "attack_roll":
            if mod_type in ["attack_roll", "contested_check", "attack_bonus"]:
                is_applicable = True
        elif action_type == "defense_roll":
            if mod_type in ["defense_roll", "defense_bonus", "ac_bonus"]:
                is_applicable = True
        elif action_type == "damage":
            if mod_type in ["damage", "damage_bonus"]:
                is_applicable = True
        elif action_type == "initiative":
            if mod_type in ["initiative", "initiative_bonus"]:
                is_applicable = True
        
        if not is_applicable:
            continue
        
        required_tags = mod.get("required_tags", [])
        if required_tags:
            if not all(req in tags for req in required_tags):
                continue
        
        target_stat = mod.get("stat")
        if target_stat and target_stat not in tags:
            continue
        
        target_skill = mod.get("skill")
        if target_skill and target_skill not in tags:
            continue
        
        if action_type == "attack_roll":
            bonuses["attack_roll_bonus"] += mod_bonus
        elif action_type == "defense_roll":
            bonuses["defense_roll_bonus"] += mod_bonus
        elif action_type == "damage":
            bonuses["damage_bonus"] += mod_bonus
        elif action_type == "initiative":
            bonuses["initiative_bonus"] += mod_bonus
    
    return bonuses
