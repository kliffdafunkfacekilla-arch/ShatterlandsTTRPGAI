import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'AI-TTRPG')))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reproduce_issue")

try:
    from monolith.modules import rules as rules_api
    from monolith.modules.character_pkg import schemas as char_schemas
    from monolith.modules.character_pkg import services as char_services
    from monolith.modules.character_pkg.database import SessionLocal as CharSession
except ImportError as e:
    logger.error(f"Import failed: {e}")
    sys.exit(1)

def reproduce():
    logger.info("Starting reproduction script...")

    # 1. Simulate Frontend Loading Rules
    logger.info("Simulating frontend rules loading...")
    rules_data = {
        "kingdoms": rules_api.get_all_kingdoms(),
        "schools": rules_api.get_all_ability_schools(),
        "origins": rules_api.get_origin_choices(),
        "childhoods": rules_api.get_childhood_choices(),
        "coming_of_ages": rules_api.get_coming_of_age_choices(),
        "trainings": rules_api.get_training_choices(),
        "devotions": rules_api.get_devotion_choices(),
        "talents": ["Basic Strike"], # Simplified
        "kingdom_features_data": rules_api.get_data("kingdom_features_data"),
        "stats_list": rules_api.get_all_stats(),
        "all_skills": rules_api.get_all_skills()
    }
    
    logger.info(f"Rules Data Keys: {list(rules_data.keys())}")
    logger.info(f"Stats List: {rules_data.get('stats_list')}")
    logger.info(f"All Skills Length: {len(rules_data.get('all_skills', []))}")
    
    if not rules_data.get('stats_list'):
        logger.error("Stats list is empty in reproduction script!")
        return

    # 2. Construct Character Payload
    new_char = char_schemas.CharacterCreate(
        name="TestChar",
        kingdom="Mammal",
        ability_school="Force",
        feature_choices=[{"feature_id": "F1", "choice_name": "Warm Blooded"}], # Example
        origin_choice="Commoner",
        childhood_choice="Street Urchin",
        coming_of_age_choice="Apprenticeship",
        training_choice="Militia",
        devotion_choice="None",
        ability_talent="Basic Strike",
        portrait_id="character_1"
    )

    # 3. Call Backend Service
    logger.info("Calling create_character...")
    try:
        with CharSession() as db:
            result = char_services.create_character(db, new_char, rules_data=rules_data)
            logger.info(f"Character Created Successfully: {result.name} (ID: {result.id})")
            logger.info(f"Stats: {result.stats}")
    except Exception as e:
        logger.exception(f"Character Creation Failed: {e}")

if __name__ == "__main__":
    reproduce()
