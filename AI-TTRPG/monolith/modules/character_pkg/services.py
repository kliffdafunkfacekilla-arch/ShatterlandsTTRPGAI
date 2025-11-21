# app/services.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from copy import deepcopy
import uuid
import logging
from . import models, schemas
from ..rules_pkg.data_loader import get_item_template
from ..rules_pkg.models_inventory import PassiveModifier
from ..rules_pkg.talent_logic import get_talent_modifiers
from ..rules_pkg.inventory_logic import get_passive_modifiers
from .. import rules as rules_api

logger = logging.getLogger("monolith.character.services")

def get_character(db: Session, character_id: str) -> Optional[models.Character]:
    """Fetches a single character by its UUID."""
    return (
        db.query(models.Character).filter(models.Character.id == character_id).first()
    )

def get_characters(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Character]:
    """Fetches a list of all characters."""
    return db.query(models.Character).offset(skip).limit(limit).all()

def apply_passive_modifiers(character: models.Character) -> (Dict[str, Any], int):
    """
    Applies all passive modifiers from equipment and talents to a character's stats.
    Returns a tuple containing the new, modified stats dictionary and the total DR.
    """
    base_stats = deepcopy(character.stats)
    total_dr = 0

    # Get modifiers from equipment
    equipment_modifiers = get_passive_modifiers(character)

    # Get modifiers from talents
    talent_modifiers = get_talent_modifiers(character.talents or [])

    all_modifiers = equipment_modifiers + talent_modifiers

    for mod in all_modifiers:
        if mod.effect_type == "STAT_MODIFIER" and mod.target in base_stats:
            base_stats[mod.target] += mod.value
            logger.info(f"Applied {mod.source_id}: {mod.target} +{mod.value}")
        elif mod.effect_type == "DR_MODIFIER":
            total_dr += mod.value
            logger.info(f"Applied {mod.source_id}: DR +{mod.value}")

    return base_stats, total_dr

def toggle_technique_state(db: Session, character_id: str, technique_id: str, active: bool) -> Optional[models.Character]:
    """
    Toggles a technique on or off for a character, updating reserved resources.
    """
    character = get_character(db, character_id)
    if not character:
        logger.error(f"Toggle technique failed: Character {character_id} not found.")
        return None

    # Ensure resource pools are in the correct format (dict of dicts)
    resource_pools = deepcopy(character.resource_pools) if character.resource_pools else {}

    # Ensure active_techniques is initialized
    active_techniques = list(character.active_techniques) if character.active_techniques else []

    # Call core logic
    success = rules_api.core.toggle_technique(resource_pools, active_techniques, technique_id, active)

    if success:
        character.resource_pools = resource_pools
        character.active_techniques = active_techniques
        try:
            db.commit()
            db.refresh(character)
            logger.info(f"Technique '{technique_id}' toggled to {active}. New resources: {resource_pools}")
            return character
        except Exception as e:
            db.rollback()
            logger.error(f"Database error toggling technique: {e}")
            raise
    else:
        logger.warning(f"Failed to toggle technique '{technique_id}' (Active={active}) for {character.name}")
        return None

def get_character_context(
    db_character: models.Character,
) -> schemas.CharacterContextResponse:
    """
    Maps the SQLAlchemy model (with JSON fields) to the Pydantic
    response model. THIS FUNCTION IS REUSED.
    """
    if not db_character:
        return None

    def_skills = {}
    def_pools = {}
    def_talents = []
    def_abilities = []
    def_inv = {}
    def_equip = {}
    def_status = []
    def_injuries = []
    def_unlocks = []
    def_techniques = []

    # Apply passive modifiers from talents and equipment
    final_stats, total_dr = apply_passive_modifiers(db_character)

    # --- IMPLEMENT: DYNAMIC STAT OVERRIDE LOGIC ---
    current_statuses = db_character.status_effects or []
    for status_id in current_statuses:
        if status_id.startswith("TempDebuff_"):
            try:
                # Expected format: TempDebuff_STATNAME_AMOUNT_DURATION (e.g., TempDebuff_Might_-2_1)
                # Note: amount is typically negative for debuffs
                parts = status_id.split("_")
                if len(parts) == 4:
                    _, stat_name, amount_str, _ = parts
                    amount = int(amount_str)

                    if stat_name in final_stats:
                        final_stats[stat_name] += amount
                        logger.info(f"Applying temporary modifier: {stat_name} adjusted by {amount}")
            except Exception as e:
                logger.warning(f"Failed to parse dynamic stat status {status_id}: {e}")
    # --- END IMPLEMENTATION ---

    return schemas.CharacterContextResponse(
        id=getattr(db_character, "id", None),
        name=getattr(db_character, "name", "Unknown"),
        kingdom=getattr(db_character, "kingdom", "Unknown"),
        level=getattr(db_character, "level", 1),
        stats=final_stats,
        skills=(
            db_character.skills if isinstance(db_character.skills, dict) else def_skills
        ),
        max_hp=getattr(db_character, "max_hp", 1),
        current_hp=getattr(db_character, "current_hp", 1),

        # --- ADD THIS LINE ---
        temp_hp=getattr(db_character, "temp_hp", 0),
        xp=getattr(db_character, "xp", 0),
        is_dead=bool(getattr(db_character, "is_dead", 0)),
        dr=total_dr,
        # --- END ADD ---

        # --- NEW FIELDS ---
        available_ap=getattr(db_character, "available_ap", 0),
        unlocked_abilities=(
            db_character.unlocked_abilities
            if isinstance(db_character.unlocked_abilities, list)
            else def_unlocks
        ),
        active_techniques=(
            db_character.active_techniques
            if isinstance(db_character.active_techniques, list)
            else def_techniques
        ),
        # ------------------

        max_composure=getattr(db_character, "max_composure", 10),
        current_composure=getattr(db_character, "current_composure", 10),
        resource_pools=(
            db_character.resource_pools
            if isinstance(db_character.resource_pools, dict)
            else def_pools
        ),
        talents=(
            db_character.talents
            if isinstance(db_character.talents, list)
            else def_talents
        ),
        abilities=(
            db_character.abilities
            if isinstance(db_character.abilities, list)
            else def_abilities
        ),
        inventory=(
            db_character.inventory
            if isinstance(db_character.inventory, dict)
            else def_inv
        ),
        equipment=(
            db_character.equipment
            if isinstance(db_character.equipment, dict)
            else def_equip
        ),
        status_effects=(
            db_character.status_effects
            if isinstance(db_character.status_effects, list)
            else def_status
        ),
        injuries=(
            db_character.injuries
            if isinstance(db_character.injuries, list)
            else def_injuries
        ),
        current_location_id=getattr(db_character, "current_location_id", 1),
        position_x=getattr(db_character, "position_x", 1),
        position_y=getattr(db_character, "position_y", 1),
        portrait_id=getattr(db_character, "portrait_id", None),
    )

def _get_rules_engine_data() -> Dict[str, Any]:
    """
    Fetches all necessary data from the rules_engine module SYNCHRONOUSLY.
    This replaces the old async/httpx version.
    """
    if not rules_api:
        raise Exception("Rules module is not loaded.")

    logger.info("Fetching all creation data from Rules Module (sync)...")

    try:
        rules_data = {
            "kingdom_features_data": rules_api._get_data("kingdom_features_data"),
            "ability_schools": rules_api.get_all_ability_schools(),
            "stats_list": rules_api.get_all_stats(),
            "all_skills": rules_api.get_all_skills(),
            "origin_choices": rules_api.get_origin_choices(),
            "childhood_choices": rules_api.get_childhood_choices(),
            "coming_of_age_choices": rules_api.get_coming_of_age_choices(),
            "training_choices": rules_api.get_training_choices(),
            "devotion_choices": rules_api.get_devotion_choices(),
            "all_talents_structured": rules_api.get_all_talents_data(),
            "item_templates": rules_api._get_data("item_templates"),
        }

        all_talents_map = {}
        structured_talents = rules_data.get("all_talents_structured", {})
        if not structured_talents:
            logger.warning("Received empty talent data from rules module.")
        else:
            for talent in structured_talents.get("single_stat_mastery", []):
                if isinstance(talent, dict) and "talent_name" in talent:
                    all_talents_map[talent["talent_name"]] = talent
            for talent in structured_talents.get("dual_stat_focus", []):
                if isinstance(talent, dict) and "talent_name" in talent:
                    all_talents_map[talent["talent_name"]] = talent
            for category_list in structured_talents.get("single_skill_mastery", {}).values():
                if isinstance(category_list, list):
                    for skill_group in category_list:
                        if isinstance(skill_group, dict):
                            for talent in skill_group.get("talents", []):
                                if isinstance(talent, dict):
                                    talent_name = talent.get("talent_name") or talent.get("name")
                                    if talent_name:
                                        all_talents_map[talent_name] = talent
        rules_data["all_talents_map"] = all_talents_map
        logger.info(f"Loaded {len(all_talents_map)} talents into map.")

        school_details = {}
        all_abilities_map = rules_api._get_data("ability_data")
        for school_name in rules_data["ability_schools"]:
            school_data = rules_api.get_ability_school(school_name)
            school_details[school_name] = school_data

        rules_data["all_abilities_map"] = school_details

        logger.info("Successfully fetched all creation data (sync).")
        return rules_data

    except Exception as e:
        logger.exception(f"FATAL: Error in _get_rules_engine_data (sync): {e}")
        raise e


def apply_injury_to_character(
    db: Session, character_id: str, injury: Dict[str, Any]
) -> Optional[models.Character]:
    """Applies an injury to a character and saves it."""
    character = get_character(db, character_id)
    if not character:
        logger.warning(f"Apply injury failed: Character {character_id} not found.")
        return None

    # Make sure injuries is a list
    if not isinstance(character.injuries, list):
        character.injuries = []

    # SQLAlchemy's change detection for mutable types like JSON can be tricky.
    # Re-assigning the list ensures the change is tracked.
    new_injuries = character.injuries + [injury]
    character.injuries = new_injuries

    try:
        db.commit()
        db.refresh(character)
        logger.info(f"Successfully applied injury to {character_id}.")
        return character
    except Exception as e:
        db.rollback()
        logger.error(f"Database error applying injury to {character_id}: {e}")
        raise Exception(f"Database error: {e}")


def remove_injury_from_character(
    db: Session, character_id: str, severity: str
) -> Optional[models.Character]:
    """Removes the first injury of a given severity from a character."""
    character = get_character(db, character_id)
    if not character:
        logger.warning(f"Remove injury failed: Character {character_id} not found.")
        return None

    if not isinstance(character.injuries, list) or not character.injuries:
        logger.info(f"Character {character_id} has no injuries to remove.")
        return character

    found_injury = None
    new_injuries_list = character.injuries[:]  # Create a copy
    for inj in new_injuries_list:
        if inj.get("severity") == severity:
            found_injury = inj
            break

    if found_injury:
        new_injuries_list.remove(found_injury)
        character.injuries = new_injuries_list
        logger.info(f"Removed '{severity}' injury from {character_id}.")
        try:
            db.commit()
            db.refresh(character)
            logger.info(f"Successfully removed injury from {character_id}.")
            return character
        except Exception as e:
            db.rollback()
            logger.error(f"Database error removing injury from {character_id}: {e}")
            raise Exception(f"Database error: {e}")
    else:
        logger.info(f"No '{severity}' injury found on {character_id}.")
        return character

def _apply_mods(stats: Dict[str, int], mods: Dict[str, List[str]]):
    """
    Helper to apply a standard 'mods' block to a stats dictionary.
    Modifies the stats dictionary in-place.
    """
    if not isinstance(mods, dict):
        logger.warning(f"Invalid mods format, expected dict, got {type(mods)}")
        return

    for key, stat_list in mods.items():
        if not isinstance(stat_list, list):
            continue

        value = 0
        if key == "+3":
            value = 3
        elif key == "+2":
            value = 2
        elif key == "+1":
            value = 1
        elif key == "-1":
            value = -1

        if value == 0:
            continue

        for stat_name in stat_list:
            if stat_name in stats:
                stats[stat_name] += value
                logger.info(f"Applied {key} to {stat_name}. New value: {stats[stat_name]}")
            else:
                logger.warning(f"Stat '{stat_name}' in mods not found in base stats.")

def create_character(
    db: Session, character: schemas.CharacterCreate, rules_data: Optional[Dict[str, Any]] = None
) -> schemas.CharacterContextResponse:
    """
    Creates a new character in the database after calculating all
    stats and vitals based on user choices.

    This is now a SYNCHRONOUS function.
    """
    logger.info(f"--- Starting character creation for: {character.name} ---")
    logger.debug(f"Received character creation payload: {character.model_dump_json(indent=2)}")

    rules = rules_data
    if rules is None:
        try:
            logger.info("No rules data passed, fetching from rules_engine...")
            rules = _get_rules_engine_data()
        except Exception as e:
            logger.error(f"Failed to fetch rules data from rules_engine: {e}")
            raise e
    else:
        logger.info("Using pre-fetched rules data.")

    base_stats = {stat: 8 for stat in rules.get("stats_list", [])}
    base_skills = {}
    for skill_name in rules.get("all_skills", {}):
        base_skills[skill_name] = {"rank": 0, "sre": 0}

    if not base_stats or not base_skills:
        logger.error("Failed to initialize stats/skills. Rules data for 'stats_list' or 'all_skills' was empty.")
        raise Exception("Character creation failed: Missing core rules data.")

    logger.info("Initialized stats (all 8s) and skills (all 0s).")
    logger.info("Applying feature mods...")
    all_features_data = rules.get("kingdom_features_data", {})
    for choice in character.feature_choices:
        kingdom_key = "All" if choice.feature_id == "F9" else character.kingdom
        try:
            if choice.feature_id not in all_features_data:
                logger.warning(f"Feature ID '{choice.feature_id}' not found in kingdom_features. Skipping.")
                continue

            feature_id_data = all_features_data.get(choice.feature_id, {})

            if kingdom_key not in feature_id_data:
                logger.warning(f"Kingdom '{kingdom_key}' not found for feature '{choice.feature_id}'. Available: {list(feature_id_data.keys())}")
                continue

            feature_set = feature_id_data.get(kingdom_key, [])

            if not isinstance(feature_set, list):
                logger.error(f"Feature set for {choice.feature_id}/{kingdom_key} is not a list: {type(feature_set)}")
                continue

            mod_data = next(
                (item for item in feature_set if item.get("name") == choice.choice_name),
                None,
            )

            if mod_data and "mods" in mod_data:
                logger.info(f"Applying mods for: {choice.choice_name}")
                _apply_mods(base_stats, mod_data["mods"])
            else:
                if not mod_data:
                    available_choices = [item.get("name", "Unknown") for item in feature_set if isinstance(item, dict)]
                    logger.warning(f"Could not find choice '{choice.choice_name}' for {choice.feature_id}. Available: {available_choices}")
                else:
                    logger.warning(f"Choice '{choice.choice_name}' for {choice.feature_id} has no 'mods' field. Skipping.")
        except Exception as e:
            logger.exception(f"Error applying feature {choice.feature_id} ({choice.choice_name}): {e}")

    logger.info("Applying background skills...")
    background_choices_map = {
        "origin": {item["name"]: item for item in rules.get("origin_choices", [])},
        "childhood": {
            item["name"]: item for item in rules.get("childhood_choices", [])
        },
        "coming_of_age": {
            item["name"]: item for item in rules.get("coming_of_age_choices", [])
        },
        "training": {item["name"]: item for item in rules.get("training_choices", [])},
        "devotion": {item["name"]: item for item in rules.get("devotion_choices", [])},
    }
    origin_skills = (
        background_choices_map["origin"]
        .get(character.origin_choice, {})
        .get("skills", [])
    )
    childhood_skills = (
        background_choices_map["childhood"]
        .get(character.childhood_choice, {})
        .get("skills", [])
    )
    coming_of_age_skills = (
        background_choices_map["coming_of_age"]
        .get(character.coming_of_age_choice, {})
        .get("skills", [])
    )
    training_skills = (
        background_choices_map["training"]
        .get(character.training_choice, {})
        .get("skills", [])
    )
    devotion_skills = (
        background_choices_map["devotion"]
        .get(character.devotion_choice, {})
        .get("skills", [])
    )
    all_background_skills = (
        origin_skills
        + childhood_skills
        + coming_of_age_skills
        + training_skills
        + devotion_skills
    )
    for skill_name in all_background_skills:
        if skill_name in base_skills:
            base_skills[skill_name]["rank"] = 1
            logger.info(f"Granted Rank 1 in skill: {skill_name}")
        else:
            logger.warning(f"Background choice granted unknown skill '{skill_name}'")

    logger.info(f"Applying Ability Talent mods for: {character.ability_talent}")
    all_talents_map = rules.get("all_talents_map", {})

    if not all_talents_map:
        logger.error("Talent map is empty. No ability talents will be applied.")
    else:
        ab_talent_data = all_talents_map.get(character.ability_talent)

        if not ab_talent_data:
            available_talents = list(all_talents_map.keys())[:10]
            logger.warning(f"Ability talent '{character.ability_talent}' not found in talent map. Available (showing first 10): {available_talents}")
        elif "mods" not in ab_talent_data:
            logger.info(f"Ability talent '{character.ability_talent}' has no 'mods' field. Talent will be added but no stat mods applied.")
        else:
            try:
                _apply_mods(base_stats, ab_talent_data["mods"])
                logger.info(f"Successfully applied mods for talent: {character.ability_talent}")
            except Exception as e:
                logger.exception(f"Error applying mods for talent '{character.ability_talent}': {e}")

    logger.info(f"Final calculated stats: {base_stats}")
    logger.info("Calculating vitals...")

    # --- UPDATE: Use New Vitals Logic ---
    try:
        # We use the internal rules function directly for safety in service layer
        vitals_req = rules_api.models.BaseVitalsRequest(stats=base_stats, level=1)
        vitals = rules_api.core.calculate_base_vitals(vitals_req)

        max_hp = vitals.max_hp
        max_composure = vitals.max_composure
        resource_pools = vitals.resources
        logger.info(f"Vitals calculated: MaxHP={max_hp}, MaxComposure={max_composure}")
    except Exception as e:
        logger.error(f"FATAL: Failed to calculate vitals from rules_engine: {e}")
        raise e
    # --- END UPDATE ---

    base_abilities = []
    school_data = rules.get("all_abilities_map", {}).get(character.ability_school)

    # --- NEW: Initial Unlocks ---
    # "One Ability school unlocked and can use the first tier abilities"
    initial_unlocks = []
    school = character.ability_school # e.g., "Force"

    # Assuming standard branches: Offense, Defense, Utility
    initial_unlocks.append(f"{school}_Offense_T1")
    initial_unlocks.append(f"{school}_Defense_T1")
    initial_unlocks.append(f"{school}_Utility_T1")
    # --- END NEW ---

    if not school_data:
        logger.warning(f"No ability school data found for '{character.ability_school}'. No base ability added.")
    else:
        branches = school_data.get("tiers", [])
        if not branches or not isinstance(branches, list) or len(branches) == 0:
             logger.warning(f"Ability school '{character.ability_school}' has no 'branches' or 'tiers'. No base ability added.")
        else:
            try:
                first_branch = branches[0]
                first_tier = first_branch.get("tiers", [])[0]
                ability_name = first_tier.get("name", "Unknown Ability")
                base_abilities.append(ability_name)
                logger.info(f"Added T1 ability: {ability_name}")
            except Exception as e:
                logger.exception(f"Could not parse T1 ability from school '{character.ability_school}': {e}")

    logger.info("Creating database entry...")
    db_character = models.Character(
        id=str(uuid.uuid4()),
        name=character.name,
        kingdom=character.kingdom,
        level=1,
        stats=base_stats,
        skills=base_skills,
        max_hp=max_hp,
        current_hp=max_hp,

        # --- ADD THIS LINE ---
        temp_hp=0,
        xp=0,
        available_ap=3, # Starting Grant
        is_dead=0,
        # --- END ADD ---

        max_composure=max_composure,
        current_composure=max_composure,
        resource_pools=resource_pools,

        unlocked_abilities=initial_unlocks, # New Field

        talents=[character.ability_talent],
        abilities=base_abilities,
        inventory={"item_iron_sword": 1, "item_leather_jerkin": 1},

        equipment={
            "combat": {
                "main_hand": rules.get("item_templates", {}).get("item_iron_sword"),
                "chest": rules.get("item_templates", {}).get("item_leather_jerkin"),
            },
            "accessories": {},
            "equipped_gear": None
        },
        status_effects=[],
        injuries=[],
        current_location_id=1,
        position_x=1,
        position_y=1,
        portrait_id=character.portrait_id
    )

    logger.debug(f"Constructed DB character model: {db_character.__dict__}")

    try:
        logger.info("Adding character to DB session...")
        db.add(db_character)
        logger.info("Committing transaction...")
        db.commit()
        logger.info("Transaction committed.")
        db.refresh(db_character)
        logger.info(f"Successfully refreshed character from DB: {db_character.id}")

        response = get_character_context(db_character)
        logger.debug(f"Returning character context response: {response.model_dump_json(indent=2)}")
        logger.info("--- Character creation successful ---")
        return response
    except Exception as e:
        db.rollback()
        logger.error(f"Database error on character save: {e}", exc_info=True)
        raise Exception(f"Database error: {e}")

def add_item_to_character(db: Session, character_id: str, item_id: str, quantity: int = 1) -> Optional[models.Character]:
    """Adds an item to the character's inventory."""
    character = get_character(db, character_id)
    if not character:
        return None

    inventory = dict(character.inventory) if character.inventory else {}
    if item_id in inventory:
        inventory[item_id] += quantity
    else:
        inventory[item_id] = quantity

    character.inventory = inventory
    try:
        db.commit()
        db.refresh(character)
        logger.info(f"Added {quantity}x {item_id} to {character_id}")
        return character
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add item: {e}")
        raise

def remove_item_from_character(db: Session, character_id: str, item_id: str, quantity: int = 1) -> Optional[models.Character]:
    """Removes an item from the character's inventory."""
    character = get_character(db, character_id)
    if not character:
        return None

    inventory = dict(character.inventory) if character.inventory else {}
    if item_id not in inventory:
        logger.warning(f"Item {item_id} not in inventory for {character_id}")
        return character

    if inventory[item_id] <= quantity:
        del inventory[item_id]
    else:
        inventory[item_id] -= quantity

    character.inventory = inventory
    try:
        db.commit()
        db.refresh(character)
        logger.info(f"Removed {quantity}x {item_id} from {character_id}")
        return character
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to remove item: {e}")
        raise

def _get_slot_category(slot_name: str) -> Optional[str]:
    """Helper to determine if a slot is 'combat' or 'accessories'."""
    if slot_name in schemas.CombatSlots.model_fields:
        return "combat"
    if slot_name in schemas.AccessorySlots.model_fields:
        return "accessories"
    if slot_name == "equipped_gear":
        return "equipped_gear"
    return None

def equip_item(db: Session, character_id: str, item_id: str, target_slot: str) -> Optional[models.Character]:
    """
    Equips an item from a character's inventory to a specified slot.
    Handles validation, swapping, and database persistence.
    """
    character = get_character(db, character_id)
    if not character:
        logger.error(f"Equip failed: Character '{character_id}' not found.")
        return None

    item_template = get_item_template(item_id)
    if not item_template:
        logger.error(f"Equip failed: Item template '{item_id}' not found.")
        return None

    if target_slot not in item_template.slots:
        logger.error(f"Equip failed: Item '{item_id}' cannot be equipped in slot '{target_slot}'.")
        return None

    inventory = deepcopy(dict(character.inventory)) if character.inventory else {}
    if inventory.get(item_id, 0) < 1:
        logger.error(f"Equip failed: Item '{item_id}' not in character's inventory.")
        return None

    equipment = deepcopy(dict(character.equipment)) if character.equipment else {}
    slot_category = _get_slot_category(target_slot)

    if not slot_category:
        logger.error(f"Equip failed: Invalid target slot '{target_slot}'.")
        return None

    # Ensure equipment structure is initialized
    if slot_category not in equipment:
        equipment[slot_category] = {}

    # Unequip any existing item in the target slot
    if slot_category == "equipped_gear":
        currently_equipped = equipment.get("equipped_gear")
        if currently_equipped:
            # We need to find the item_id of the equipped item. Assume it was stored.
            equipped_item_id = currently_equipped.get("id", "unknown_item")
            inventory[equipped_item_id] = inventory.get(equipped_item_id, 0) + 1
            logger.info(f"Unequipped '{equipped_item_id}' to inventory.")
    else:
        currently_equipped = equipment.get(slot_category, {}).get(target_slot)
        if currently_equipped:
            equipped_item_id = currently_equipped.get("id", "unknown_item")
            inventory[equipped_item_id] = inventory.get(equipped_item_id, 0) + 1
            logger.info(f"Unequipped '{equipped_item_id}' from '{target_slot}' to inventory.")

    # Decrement inventory and equip the new item
    inventory[item_id] -= 1
    if inventory[item_id] == 0:
        del inventory[item_id]

    item_data_to_store = item_template.model_dump()
    item_data_to_store['id'] = item_id # Store the id for future reference

    if slot_category == "equipped_gear":
        equipment["equipped_gear"] = item_data_to_store
    else:
        equipment[slot_category][target_slot] = item_data_to_store

    logger.info(f"Equipped '{item_id}' to '{target_slot}'.")

    # Persist changes to the database
    character.inventory = inventory
    character.equipment = equipment
    try:
        db.commit()
        db.refresh(character)
        return character
    except Exception as e:
        db.rollback()
        logger.exception(f"Database error while equipping item: {e}")
        raise

def get_passive_modifiers(character: models.Character) -> List[PassiveModifier]:
    """
    Aggregates all passive modifiers from a character's equipped items.
    """
    modifiers: List[PassiveModifier] = []
    if not isinstance(character.equipment, dict):
        return modifiers

    equipment = character.equipment

    # Iterate through combat and accessory slots
    for category in ["combat", "accessories"]:
        for slot_name, item in equipment.get(category, {}).items():
            if not item:
                continue

            item_id = item.get("id", "unknown_item")

            # Handle direct DR stat
            if "dr" in item and isinstance(item["dr"], int):
                modifiers.append(PassiveModifier(
                    effect_type="DR_MODIFIER",
                    target=slot_name,
                    value=item["dr"],
                    source_id=item_id
                ))

            # Handle effects list
            for effect in item.get("effects", []):
                if effect.get("type") == "buff" and "target_stat" in effect:
                    modifiers.append(PassiveModifier(
                        effect_type="STAT_MODIFIER",
                        target=effect["target_stat"],
                        value=effect.get("value", 0),
                        source_id=item_id
                    ))

    return modifiers

def _recalculate_character_vitals(db: Session, character: models.Character):
    """Internal helper to update Max HP/Composure after stats/level change."""
    try:
        req = rules_api.models.BaseVitalsRequest(stats=character.stats, level=character.level)
        vitals = rules_api.core.calculate_base_vitals(req)
        character.max_hp = vitals.max_hp
        character.max_composure = vitals.max_composure

        # Preserve existing reserved amounts if possible, or reset if not
        current_pools = character.resource_pools or {}
        new_pools = vitals.resources

        for pool_name, pool_data in new_pools.items():
            if pool_name in current_pools and "reserved" in current_pools[pool_name]:
                 pool_data["reserved"] = current_pools[pool_name]["reserved"]
            else:
                 pool_data["reserved"] = 0

        character.resource_pools = new_pools

        # Apply passive modifiers to max resources (e.g. Grappled effect)
        _, _ = apply_passive_modifiers(character)
        # Wait, apply_passive_modifiers only calculates stats and returns them.
        # It does not update the character model directly for resources.
        # I need to handle resource max modifiers here.

        # Get modifiers again to apply resource max changes
        equipment_modifiers = get_passive_modifiers(character)
        talent_modifiers = get_talent_modifiers(character.talents or [])
        all_modifiers = equipment_modifiers + talent_modifiers

        # Status effects also need to be checked for resource max penalties (Grappled)

        if rules_api.data_loader.STATUS_EFFECTS:
             for status_id in (character.status_effects or []):
                  # Handle both simple ID "Grappled" and complex "TempDebuff_..."
                  # Status effects in JSON are keys like "Grappled"
                  status_def = rules_api.core.get_status_effect(status_id, rules_api.data_loader.STATUS_EFFECTS)
                  # StatusEffectResponse has 'effects' list
                  for effect_str in status_def.effects:
                       # "resource_max_penalty:Stamina:5"
                       parts = effect_str.split(":")
                       if parts[0] == "resource_max_penalty" and len(parts) == 3:
                            res_target = parts[1]
                            val = int(parts[2])
                            if res_target in character.resource_pools:
                                 character.resource_pools[res_target]["max"] = max(1, character.resource_pools[res_target]["max"] - val)
                                 logger.info(f"Applied resource max penalty from status {status_id}: {res_target} -{val}")

        # CHECK FOR OVER-RESERVATION
        # If Reserved > Max, we must disable techniques until we are under budget.
        if character.active_techniques:
            if not rules_api.data_loader.TECHNIQUES:
                rules_api.data_loader.load_data()

            techniques_to_remove = []

            # Iterate pools to check for violation
            for pool_name, pool_data in character.resource_pools.items():
                if pool_data["reserved"] > pool_data["max"]:
                    logger.info(f"Resource Overdraft in {pool_name}: Reserved {pool_data['reserved']} > Max {pool_data['max']}. Disabling techniques...")

                    # Iterate active techniques to find ones using this resource
                    # We iterate in reverse or just repeatedly until solved?
                    # Simple approach: find techniques using this resource and turn them off one by one.

                    # Make a copy to iterate safely
                    active_copy = list(character.active_techniques)
                    for tech_id in active_copy:
                        if pool_data["reserved"] <= pool_data["max"]:
                            break # Solved

                        tech_data = rules_api.data_loader.TECHNIQUES.get(tech_id)
                        if not tech_data: continue

                        cost = tech_data.get("maintenance_cost", {}).get(pool_name)
                        if cost:
                            # Found a culprit
                            logger.info(f"Force disabling technique '{tech_id}' to free {cost} {pool_name}")
                            pool_data["reserved"] -= cost
                            techniques_to_remove.append(tech_id)

                            # Remove from our local copy so we don't double count if using multiple resources?
                            # Actually just flagging for removal is safer.
                            # But we need to update 'reserved' locally to know if we are done.

            # Apply removals
            if techniques_to_remove:
                new_active = [t for t in character.active_techniques if t not in techniques_to_remove]
                character.active_techniques = new_active
                logger.info(f"Updated active techniques after overdraft check: {character.active_techniques}")

        # Note: We generally don't auto-fill current HP here unless it's a full rest or level up event
    except Exception as e:
        logger.error(f"Failed to recalculate vitals: {e}")

def level_up_character(db: Session, character: models.Character):
    """Internal logic applied when XP threshold is met."""
    if character.level >= 20:
        return

    character.level += 1
    character.available_ap += 2 # Drip rate

    # Recalculate Vitals with new level scaling
    _recalculate_character_vitals(db, character)

    # Full Heal
    character.current_hp = character.max_hp
    character.current_composure = character.max_composure

    logger.info(f"{character.name} leveled up to {character.level}!")

def award_xp(db: Session, character_id: str, amount: int) -> Optional[models.Character]:
    """Awards XP and handles leveling up."""
    character = get_character(db, character_id)
    if not character:
        return None

    character.xp = (character.xp or 0) + amount
    logger.info(f"Awarded {amount} XP to {character.name}. Total: {character.xp}")

    # Simple Level Up Logic: Level * 1000
    # e.g. Lv 1 -> 2 needs 1000 XP total. Lv 2 -> 3 needs 2000 XP total.
    # This is a placeholder for the real curve.
    next_level_threshold = character.level * 1000
    if character.xp >= next_level_threshold:
        level_up_character(db, character)

    try:
        db.commit()
        db.refresh(character)
        return character
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to award XP: {e}")
        raise

def purchase_ability(db: Session, character_id: str, school: str, branch: str, tier: int):
    """
    Attempts to buy an ability node.
    """
    char = get_character(db, character_id)
    if not char: raise Exception("Character not found")

    # 1. Construct Request
    target_node = rules_api.models.AbilityNode(school=school, branch=branch, tier=tier)

    req = rules_api.models.AbilityPurchaseRequest(
        target_ability=target_node,
        current_unlocks=char.unlocked_abilities or [],
        available_ap=char.available_ap
    )

    # 2. Validate via Rules Engine
    result = rules_api.core.validate_ability_unlock(req)

    if not result.success:
        return {"success": False, "message": result.message}

    # 3. Commit Transaction
    # Update AP
    char.available_ap = result.remaining_ap

    # Append new node ID safely
    current_list = list(char.unlocked_abilities) if char.unlocked_abilities else []
    current_list.append(result.new_unlock)
    char.unlocked_abilities = current_list

    try:
        db.commit()
        db.refresh(char)
        return {"success": True, "message": result.message, "character": char}
    except Exception as e:
        db.rollback()
        raise e

def handle_death(db: Session, character_id: str) -> Optional[models.Character]:
    """Sets the character status to dead/downed."""
    character = get_character(db, character_id)
    if not character:
        return None

    character.is_dead = 1 # True
    character.current_hp = 0
    
    # Add "Downed" status effect if not present
    status_effects = list(character.status_effects) if character.status_effects else []
    if "Downed" not in status_effects:
        status_effects.append("Downed")
        character.status_effects = status_effects

    logger.info(f"Character {character.name} ({character_id}) has fallen!")

    try:
        db.commit()
        db.refresh(character)
        return character
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to handle death: {e}")
        raise

def update_character_context(
    db: Session, character_id: str, updates: schemas.CharacterContextResponse
) -> Optional[models.Character]:
    """
    Updates a character in the database from a full context object.
    """
    db_character = get_character(db, character_id)
    if db_character:
        logger.info(f"Updating character: {character_id}")
        db_character.name = updates.name
        db_character.kingdom = updates.kingdom
        db_character.level = updates.level
        db_character.stats = updates.stats
        db_character.skills = updates.skills
        db_character.max_hp = updates.max_hp
        db_character.current_hp = updates.current_hp
        db_character.resource_pools = updates.resource_pools
        db_character.talents = updates.talents
        db_character.abilities = updates.abilities
        db_character.inventory = updates.inventory
        db_character.equipment = updates.equipment
        db_character.status_effects = updates.status_effects
        db_character.injuries = updates.injuries
        db_character.current_location_id = updates.current_location_id
        db_character.position_x = updates.position_x
        db_character.position_y = updates.position_y
        db_character.portrait_id = updates.portrait_id

        try:
            db.commit()
            db.refresh(db_character)
            logger.info(f"Successfully updated character {character_id}.")
            return db_character
        except Exception as e:
            db.rollback()
            logger.error(f"Database error on character update: {e}")
            raise Exception(f"Database error: {e}")
    else:
        logger.warning(f"Update failed: Character {character_id} not found.")
        return None

def create_default_test_character(db: Session, rules_data: dict):
    """
    Creates a hardcoded default character for testing purposes.

    This function constructs a fixed `CharacterCreate` payload and invokes the
    main `create_character` service to generate a complete character record.

    Args:
        db (Session): The database session.
        rules_data (dict): The pre-loaded rules data required for creation.

    Returns:
        models.Character: The created character object.
    """
    logger.info("--- Creating Default Test Character ---")

    creation_request = schemas.CharacterCreate(
        name="Tester",
        kingdom="Mammal",
        feature_choices=[
            schemas.FeatureChoice(feature_id="F1", choice_name="The Predator (Jaws/Horns)"),
            schemas.FeatureChoice(feature_id="F2", choice_name="The Juggernaut (Pure Armor)"),
            schemas.FeatureChoice(feature_id="F3", choice_name="The Brute (Raw Power)"),
            schemas.FeatureChoice(feature_id="F4", choice_name="The Artisan (Delicate)"),
            schemas.FeatureChoice(feature_id="F5", choice_name="The Acrobat (Speed/Evasion)"),
            schemas.FeatureChoice(feature_id="F6", choice_name="The Toxin Filter (Resilience)"),
            schemas.FeatureChoice(feature_id="F7", choice_name="The Tracker (Keen Senses)"),
            schemas.FeatureChoice(feature_id="F8", choice_name="The Logician (Pure Intellect)"),
            schemas.FeatureChoice(feature_id="F9", choice_name="Capstone: +3 Might"),
        ],
        origin_choice="Forested Highlands",
        childhood_choice="Street Urchin",
        coming_of_age_choice="The Grand Tournament",
        training_choice="Soldier's Discipline",
        devotion_choice="Devotion to the State",
        ability_school="Force",
        ability_talent="Overpowering Presence",
        portrait_id="character_1"
    )

    logger.info(f"Default character payload created for '{creation_request.name}'. Passing to main creation service.")

    try:
        new_character = create_character(db=db, character=creation_request, rules_data=rules_data)
        logger.info("--- Default test character creation successful ---")
        return new_character
    except Exception as e:
        logger.exception("An error occurred in the main creation service while creating the default character.")
        raise e
