# app/services.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uuid
import httpx # Import httpx
import os # Import os
from . import models, schemas
import logging # --- ADD LOGGING ---
# --- ADDED: Logger ---
logger = logging.getLogger("uvicorn.error")
# --- ADDED: Rules Engine Configuration ---
RULES_ENGINE_URL = os.getenv("RULES_ENGINE_URL", "http://127.0.0.1:8000/v1")
CLIENT_TIMEOUT = 10.0
print(f"Character Engine configured to use Rules Engine at: {RULES_ENGINE_URL}")
# --- UNCHANGED: get_character, get_characters ---
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
# --- MODIFIED: get_character_context ---
def get_character_context(
    db_character: models.Character,
) -> schemas.CharacterContextResponse:
    """
    Maps the SQLAlchemy model (with JSON fields) to the Pydantic
    response model. THIS FUNCTION IS REUSED.
    """
    if not db_character:
        return None

    # Ensure JSON fields are dictionaries, not strings
    # (FastAPI's JSON type usually handles this, but good to be safe)
    def_stats = {}
    def_skills = {}
    def_pools = {}
    def_talents = []
    def_abilities = []
    def_inv = {}
    def_equip = {}
    def_status = []
    def_injuries = []

    return schemas.CharacterContextResponse(
        id=db_character.id,
        name=db_character.name,
        kingdom=db_character.kingdom or "Unknown",
        level=db_character.level,
        stats=db_character.stats if isinstance(db_character.stats, dict) else def_stats,
        skills=(
            db_character.skills if isinstance(db_character.skills, dict) else def_skills
        ),
        max_hp=db_character.max_hp,
        current_hp=db_character.current_hp,
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
        # --- ADD THIS LINE ---
        current_location_id=db_character.current_location_id,
        # --- END ADD ---
        position_x=db_character.position_x,
        position_y=db_character.position_y,

        # --- ADD THIS LINE ---
        portrait_id=db_character.portrait_id # Map the new field
        # --- END ADD ---
    )
# --- MODIFIED: Helper functions for new creation logic ---
def _get_rules_engine_data() -> Dict[str, Any]:
    """
    Fetches all necessary data from the rules_engine module SYNCHRONOUSLY.
    This replaces the old async/httpx version.
    """
    if not rules_api:
        raise Exception("Rules module is not loaded.")

    logger.info("Fetching all creation data from Rules Module (sync)...")

    try:
        # All data is already loaded into memory by rules_api,
        # we just call the helper getters.
        rules_data = {
            "kingdom_features": rules_api._get_data("kingdom_features_data"),
            "ability_schools": list(rules_api._get_data("ability_data").keys()),
            "stats_list": rules_api._get_data("stats_list"),
            "all_skills": rules_api._get_data("all_skills"),
            "origin_choices": rules_api._get_data("origin_choices"),
            "childhood_choices": rules_api._get_data("childhood_choices"),
            "coming_of_age_choices": rules_api._get_data("coming_of_age_choices"),
            "training_choices": rules_api._get_data("training_choices"),
            "devotion_choices": rules_api._get_data("devotion_choices"),
            "all_talents_structured": rules_api._get_data("talent_data"),
        }

        # --- (This talent-flattening logic is the same as before) ---
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

        # --- Get Ability School Details (Sync) ---
        school_details = {}
        all_abilities_map = rules_api._get_data("ability_data")
        for school_name in rules_data["ability_schools"]:
            school_data = all_abilities_map.get(school_name, {})
            school_details[school_name] = {
                "school": school_name,
                "resource_pool": school_data.get("resource_pool", school_data.get("resource")),
                "associated_stat": school_data.get("associated_stat", "Unknown"),
                "tiers": school_data.get("branches", [])
            }
        rules_data["all_abilities_map"] = school_details

        logger.info("Successfully fetched all creation data (sync).")
        return rules_data

    except Exception as e:
        logger.exception(f"FATAL: Error in _get_rules_engine_data (sync): {e}")
        raise e
def _apply_mods(stats: Dict[str, int], mods: Dict[str, List[str]]):
    """
    Helper to apply a standard 'mods' block to a stats dictionary.
    Modifies the stats dictionary in-place.
    """
    if not isinstance(mods, dict):
        print(f"Warning: Invalid mods format, expected dict, got {type(mods)}")
        return

    for key, stat_list in mods.items():
        if not isinstance(stat_list, list):
            continue

        value = 0
        if key == "+2":
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
                print(f"Applied {key} to {stat_name}. New value: {stats[stat_name]}")
            else:
                print(f"Warning: Stat '{stat_name}' in mods not found in base stats.")
async def create_character(
    db: Session, character: schemas.CharacterCreate, rules_data: Optional[Dict[str, Any]] = None
) -> schemas.CharacterContextResponse:
    """
    Creates a new character in the database after calculating all
    stats and vitals based on user choices.
    """
    logger.info(f"--- Starting character creation for: {character.name} ---")
    logger.debug(f"Received character creation payload: {character.model_dump_json(indent=2)}")

    # 1. Get all rules data (either pass it in or fetch it)
    rules = rules_data
    if rules is None:
        try:
            logger.info("No rules data passed, fetching from rules_engine...")
            rules = await _get_rules_engine_data()
        except Exception as e:
            print(f"Failed to fetch rules data from rules_engine: {e}")
            raise e # Re-raise the HTTPException from the helper
    else:
        logger.info("Using pre-fetched rules data.")

    # 2. Initialize base stats and skills
    base_stats = {stat: 8 for stat in rules.get("stats_list", [])}
    base_skills = {}
    for skill_name in rules.get("all_skills", {}):
        base_skills[skill_name] = {"rank": 0, "sre": 0}

    if not base_stats or not base_skills:
        logger.error("Failed to initialize stats/skills. Rules data for 'stats_list' or 'all_skills' was empty.")
        raise HTTPException(status_code=500, detail="Character creation failed: Missing core rules data.")

    print(f"Initialized stats (all 8s) and skills (all 0s).")

    # 3. Apply Feature mods
    print("Applying feature mods...")
    all_features_data = rules.get("kingdom_features", {})
    for choice in character.feature_choices:
        kingdom_key = "All" if choice.feature_id == "F9" else character.kingdom
        try:
            # Check if feature_id exists
            if choice.feature_id not in all_features_data:
                logger.warning(f"Feature ID '{choice.feature_id}' not found in kingdom_features. Skipping.")
                print(f"Warning: Feature ID '{choice.feature_id}' not found. Skipping.")
                continue

            feature_id_data = all_features_data.get(choice.feature_id, {})

            # Check if kingdom exists for this feature
            if kingdom_key not in feature_id_data:
                logger.warning(f"Kingdom '{kingdom_key}' not found for feature '{choice.feature_id}'. Available: {list(feature_id_data.keys())}")
                print(f"Warning: Kingdom '{kingdom_key}' not found for feature {choice.feature_id}. Skipping.")
                continue

            feature_set = feature_id_data.get(kingdom_key, [])

            # Check if feature_set is valid
            if not isinstance(feature_set, list):
                logger.error(f"Feature set for {choice.feature_id}/{kingdom_key} is not a list: {type(feature_set)}")
                print(f"Error: Feature set for {choice.feature_id}/{kingdom_key} is malformed. Skipping.")
                continue

            # Find the specific choice
            mod_data = next(
                (item for item in feature_set if item.get("name") == choice.choice_name),
                None,
            )

            if mod_data and "mods" in mod_data:
                print(f"Applying mods for: {choice.choice_name}")
                _apply_mods(base_stats, mod_data["mods"])
            else:
                if not mod_data:
                    available_choices = [item.get("name", "Unknown") for item in feature_set if isinstance(item, dict)]
                    logger.warning(f"Could not find choice '{choice.choice_name}' for {choice.feature_id}. Available: {available_choices}")
                    print(f"Warning: Could not find choice '{choice.choice_name}' for feature {choice.feature_id}. Skipping.")
                else:
                    logger.warning(f"Choice '{choice.choice_name}' for {choice.feature_id} has no 'mods' field. Skipping.")
                    print(f"Warning: Choice '{choice.choice_name}' has no 'mods' field. Skipping.")
        except Exception as e:
            logger.exception(f"Error applying feature {choice.feature_id} ({choice.choice_name}): {e}")
            print(f"Error applying feature {choice.feature_id} ({choice.choice_name}): {e}")

    # 4. Apply Background Skills
    print("Applying background skills...")
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
            print(f"Granted Rank 1 in skill: {skill_name}")
        else:
            print(f"Warning: Background choice granted unknown skill '{skill_name}'")

    # 5. Apply Ability Talent mods
    print(f"Applying Ability Talent mods for: {character.ability_talent}")
    all_talents_map = rules.get("all_talents_map", {})

    if not all_talents_map:
        logger.error("Talent map is empty. No ability talents will be applied.")
        print("ERROR: Talent map is empty. No ability talents available.")
    else:
        ab_talent_data = all_talents_map.get(character.ability_talent)

        if not ab_talent_data:
            available_talents = list(all_talents_map.keys())[:10]  # Show first 10
            logger.warning(f"Ability talent '{character.ability_talent}' not found in talent map. Available (showing first 10): {available_talents}")
            print(f"Warning: Ability talent '{character.ability_talent}' not found. Available talents: {available_talents}...")
        elif "mods" not in ab_talent_data:
            logger.warning(f"Ability talent '{character.ability_talent}' has no 'mods' field. Talent will be added but no stat mods applied.")
            print(f"Warning: Ability talent '{character.ability_talent}' has no 'mods' field. Skipping stat modifications.")
        else:
            # Apply the mods
            try:
                _apply_mods(base_stats, ab_talent_data["mods"])
                print(f"Successfully applied mods for talent: {character.ability_talent}")
            except Exception as e:
                logger.exception(f"Error applying mods for talent '{character.ability_talent}': {e}")
                print(f"Error: Failed to apply mods for talent '{character.ability_talent}': {e}")

    print(f"Final calculated stats: {base_stats}")

    # 6. Get Vitals from Rules Engine
    print("Calculating vitals...")
    try:
        vitals_data = await _call_rules_engine(
            "POST",
            "/calculate/base_vitals",
            json_data={"stats": base_stats}
        )
        max_hp = vitals_data.get("max_hp", 1)
        resource_pools = vitals_data.get("resources", {})
        print(f"Vitals calculated: MaxHP={max_hp}")
    except Exception as e:
        print(f"FATAL: Failed to calculate vitals from rules_engine: {e}")
        raise e # Re-raise the HTTPException from the helper

    # 7. Get base abilities
    base_abilities = []
    school_data = rules.get("all_abilities_map", {}).get(character.ability_school)

    # --- FIX: Check if school_data and tiers exist before trying to access (with comprehensive error handling) ---
    if not school_data:
        logger.warning(f"No ability school data found for '{character.ability_school}'. No base ability added.")
        print(f"Warning: Could not find school data for {character.ability_school}. No base ability added.")
    elif "tiers" not in school_data:
        logger.warning(f"Ability school '{character.ability_school}' has no 'tiers' field. No base ability added.")
        print(f"Warning: Ability school '{character.ability_school}' has no 'tiers' field. No base ability added.")
    elif not isinstance(school_data["tiers"], list):
        logger.error(f"Tiers for '{character.ability_school}' is not a list: {type(school_data['tiers'])}")
        print(f"Error: Tiers field is not a list for {character.ability_school}. No base ability added.")
    elif len(school_data["tiers"]) == 0:
        logger.warning(f"Ability school '{character.ability_school}' has empty tiers list. No base ability added.")
        print(f"Warning: Ability school '{character.ability_school}' has empty tiers list. No base ability added.")
    else:
        # Tiers exist and have content, proceed with logic
        tiers_list = school_data["tiers"]

        # Try to find T1 ability
        t1_ability = None
        for tier in tiers_list:
            if isinstance(tier, dict) and tier.get("tier") == "T1":
                t1_ability = tier
                break

        if t1_ability:
            # Use 'description' as it's the ability text
            description = t1_ability.get("description", "Unknown T1 Ability")
            base_abilities.append(description)
            print(f"Added T1 ability: {description}")
        else:
            # No T1 found, use first tier as fallback
            first_tier = tiers_list[0]
            if isinstance(first_tier, dict):
                description = first_tier.get("description", "Unknown Ability")
                base_abilities.append(description)
                logger.warning(f"No T1 ability found for {character.ability_school}. Using first available: {description}")
                print(f"Warning: School {character.ability_school} has no 'T1' ability defined. Using first available: {description}")
            else:
                logger.error(f"First tier in {character.ability_school} is not a dict: {first_tier}")
                print(f"Error: Could not extract ability from {character.ability_school}. First tier is malformed.")
    # --- END FIX ---

    # 8. Create DB model (saving to separate columns)
    print("Creating database entry...")
    db_character = models.Character(
        id=str(uuid.uuid4()),
        name=character.name,
        kingdom=character.kingdom,
        level=1,
        stats=base_stats,
        skills=base_skills,
        max_hp=max_hp,
        current_hp=max_hp,
        resource_pools=resource_pools,
        talents=[character.ability_talent],
        abilities=base_abilities,
        inventory={"item_iron_sword": 1, "item_leather_jerkin": 1},
        equipment={"weapon": "item_iron_sword", "armor": "item_leather_jerkin"},
        status_effects=[],
        injuries=[],
        # --- ADD THIS LINE ---
        current_location_id=1, # Default to STARTING_ZONE
        position_x=1, # Default start position (matches placeholder spawn)
        position_y=1, # Default start position (matches placeholder spawn)

        # --- ADD THIS LINE ---
        portrait_id=character.portrait_id # Save the portrait ID
        # --- END ADD ---
    )

    logger.debug(f"Constructed DB character model: {db_character.__dict__}")

    # 9. Save and return
    try:
        logger.info("Adding character to DB session...")
        db.add(db_character)
        logger.info("Committing transaction...")
        db.commit()
        logger.info("Transaction committed.")
        db.refresh(db_character)
        logger.info(f"Successfully refreshed character from DB: {db_character.id}")

        # This function will now work, as db_character has the separate fields
        response = get_character_context(db_character)
        logger.debug(f"Returning character context response: {response.model_dump_json(indent=2)}")
        logger.info("--- Character creation successful ---")
        return response
    except Exception as e:
        db.rollback()
        logger.error(f"Database error on character save: {e}", exc_info=True)
        raise Exception(f"Database error: {e}")
# --- MODIFIED: update_character_context ---
def update_character_context(
    db: Session, character_id: str, updates: schemas.CharacterContextResponse
) -> Optional[models.Character]:
    """
    Updates a character in the database from a full context object.
    """
    db_character = get_character(db, character_id)
    if db_character:
        print(f"Updating character: {character_id}")
        # Update all fields from the 'updates' Pydantic model
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
        # --- ADD THIS LINE ---
        db_character.current_location_id = updates.current_location_id
        # --- END ADD ---
        db_character.position_x = updates.position_x
        db_character.position_y = updates.position_y

        # --- ADD THIS LINE ---
        db_character.portrait_id = updates.portrait_id
        # --- END ADD ---

        try:
            db.commit()
            db.refresh(db_character)
            print(f"Successfully updated character {character_id}.")
            return db_character
        except Exception as e:
            db.rollback()
            print(f"Database error on character update: {e}")
            raise Exception(f"Database error: {e}")
    else:
        print(f"Update failed: Character {character_id} not found.")
        return None


async def create_default_test_character(db: Session, rules_data: dict):
    """Creates a hardcoded default character for testing by calling the main creation service."""
    logger.info("--- Creating Default Test Character ---")

    # --- MODIFICATION: Use VALID data from the JSON files ---
    creation_request = schemas.CharacterCreate(
        name="Tester",
        kingdom="Mammal", # Was "kingdom_automata"
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
        ability_talent="Overpowering Presence", # Was "Mind over Matter" which doesn't exist

        # --- ADD THIS LINE ---
        portrait_id="character_1" # Give it a default portrait
        # --- END ADD ---
    )
    # --- END MODIFICATION ---

    logger.info(f"Default character payload created for '{creation_request.name}'. Passing to main creation service.")

    try:
        # We pass rules_data from the dependency to avoid fetching it twice
        new_character = await create_character(db=db, character=creation_request, rules_data=rules_data)
        logger.info("--- Default test character creation successful ---")
        return new_character
    except Exception as e:
        logger.exception("An error occurred in the main creation service while creating the default character.")
        # Re-raise the exception to be handled by the endpoint.
        raise e
