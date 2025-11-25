"""
Core save/load logic. This module performs the direct database
queries and operations for creating save files and loading state.
It directly imports the models and sessions from all other modules.
"""
import logging
import os
import json
import datetime
from typing import List, Dict, Any
# Import all schemas
from .save_schemas import *
# Import all DB models and sessions
from .character_pkg import database as char_db
from .character_pkg import models as char_models
from .world_pkg import database as world_db
from .world_pkg import models as world_models
from .simulation_pkg import database as sim_db
from .simulation_pkg import models as sim_models
from .story_pkg import database as story_db
from .story_pkg import models as story_models

logger = logging.getLogger("monolith.save_manager")

SAVE_DIR = "saves"
os.makedirs(SAVE_DIR, exist_ok=True)

def _get_save_path(slot_name: str) -> str:
    """Generates a clean file path for the save slot."""
    filename = "".join(c for c in slot_name if c.isalnum() or c in ('_','-')) + ".json"
    return os.path.join(SAVE_DIR, filename)

def _get_active_character_info() -> (str, str):
    """Fetches the ID and name of the first active character."""
    # This is a simple placeholder. In a multi-character setup,
    # the client would pass this info to the save function.
    db = None
    try:
        db = char_db.SessionLocal()
        char = db.query(char_models.Character).first()
        if char:
            return char.id, char.name
        return None, None
    except Exception as e:
        logger.warning(f"Could not get active character for save: {e}")
        return None, None
    finally:
        if db:
            db.close()

def _save_game_internal(slot_name: str, active_character_id: str = None) -> Dict[str, Any]:
    """Internal function to query all data and write to file."""
    char_session = char_db.SessionLocal()
    world_session = world_db.SessionLocal()
    story_session = story_db.SessionLocal()
    sim_session = sim_db.SessionLocal()

    try:
        logger.info(f"--- Starting Save Game process for slot: {slot_name} ---")

        # --- 1. Query all data ---
        logger.info("Querying character data...")
        all_chars = char_session.query(char_models.Character).all()

        logger.info("Querying world data...")
        # all_factions = world_session.query(world_models.Faction).all() # MOVED TO SIM
        all_factions = sim_session.query(sim_models.Faction).all()
        all_regions = world_session.query(world_models.Region).all()
        all_locations = world_session.query(world_models.Location).all()
        all_npcs = world_session.query(world_models.NpcInstance).all()
        all_items = world_session.query(world_models.ItemInstance).all()
        all_traps = world_session.query(world_models.TrapInstance).all()

        logger.info("Querying story data...")
        all_campaigns = story_session.query(story_models.Campaign).all()
        all_campaign_states = story_session.query(story_models.CampaignState).all()
        all_quests = story_session.query(story_models.ActiveQuest).all()
        all_flags = story_session.query(story_models.StoryFlag).all()

        # --- 2. Serialize data using Pydantic Schemas ---
        logger.info("Serializing data...")
        data = SaveGameData(
            characters=[CharacterSave.from_orm(c) for c in all_chars],
            factions=[FactionSave.from_orm(f) for f in all_factions],
            regions=[RegionSave.from_orm(r) for r in all_regions],
            locations=[LocationSave.from_orm(l) for l in all_locations],
            npcs=[NpcInstanceSave.from_orm(n) for n in all_npcs],
            items=[ItemInstanceSave.from_orm(i) for i in all_items],
            traps=[TrapInstanceSave.from_orm(t) for t in all_traps],
            campaigns=[CampaignSave.from_orm(c) for c in all_campaigns],
            campaign_states=[CampaignStateSave.from_orm(c) for c in all_campaign_states],
            quests=[ActiveQuestSave.from_orm(q) for q in all_quests],
            flags=[StoryFlagSave.from_orm(f) for f in all_flags],
        )

        active_id = active_character_id
        active_name = "Unknown"
        
        if active_id:
            # Find name from loaded chars
            for c in all_chars:
                if c.id == active_id:
                    active_name = c.name
                    break
        else:
            # Fallback to auto-detect
            active_id, active_name = _get_active_character_info()

        save_file = SaveFile(
            save_name=slot_name,
            save_time=datetime.datetime.now().isoformat(),
            active_character_id=active_id,
            active_character_name=active_name,
            data=data
        )

        # --- 3. Write to file ---
        filepath = _get_save_path(slot_name)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_file.model_dump(), f, indent=2)

        logger.info(f"--- Save Game complete: {filepath} ---")
        return {"success": True, "path": filepath, "name": active_name}

    except Exception as e:
        logger.exception(f"Save game failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        char_session.close()
        world_session.close()
        story_session.close()
        sim_session.close()

def _load_game_internal(slot_name: str) -> Dict[str, Any]:
    """Internal function to read file, wipe DBs, and repopulate."""
    filepath = _get_save_path(slot_name)
    if not os.path.exists(filepath):
        logger.error(f"Save file not found: {filepath}")
        raise FileNotFoundError(f"Save file {slot_name}.json not found.")

    char_session = char_db.SessionLocal()
    world_session = world_db.SessionLocal()
    story_session = story_db.SessionLocal()
    sim_session = sim_db.SessionLocal()

    try:
        logger.info(f"--- Starting Load Game process from: {filepath} ---")

        # --- 1. Read and parse file ---
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        save_file = SaveFile(**raw_data)
        data = save_file.data

        # --- 2. Wipe existing data (in reverse dependency order) ---
        logger.info("Wiping existing database state...")
        # Story
        story_session.query(story_models.ActiveQuest).delete()
        story_session.query(story_models.StoryFlag).delete()
        story_session.query(story_models.CombatParticipant).delete()
        story_session.query(story_models.CombatEncounter).delete()
        story_session.query(story_models.CampaignState).delete()
        story_session.query(story_models.Campaign).delete()
        # World
        world_session.query(world_models.ItemInstance).delete()
        world_session.query(world_models.NpcInstance).delete()
        world_session.query(world_models.TrapInstance).delete()
        world_session.query(world_models.Tile).delete()
        world_session.query(world_models.Location).delete()
        world_session.query(world_models.Map).delete()
        world_session.query(world_models.Region).delete()
        # world_session.query(world_models.Faction).delete() # MOVED
        sim_session.query(sim_models.Faction).delete()

        # Character
        char_session.query(char_models.Character).delete()

        # --- 3. Repopulate data (in dependency order) ---
        logger.info("Repopulating databases...")
        # Character
        for char_data in data.characters:
            char_session.add(char_models.Character(**char_data.model_dump()))

        # World
        for faction_data in data.factions:
            # Check fields - sim_models.Faction has different fields than old world_models.Faction
            # This might fail if the schema in save file doesn't match.
            # But we assume the save file matches the Pydantic schema FactionSave.
            # We need to ensure sim_models.Faction is compatible with FactionSave.
            sim_session.add(sim_models.Faction(**faction_data.model_dump()))

        sim_session.commit()

        for region_data in data.regions:
            world_session.add(world_models.Region(**region_data.model_dump()))
        # Commit regions/factions so locations can link to them
        world_session.commit()

        for loc_data in data.locations:
            world_session.add(world_models.Location(**loc_data.model_dump()))
        # Commit locations so NPCs/Items can link
        world_session.commit()

        for npc_data in data.npcs:
            world_session.add(world_models.NpcInstance(**npc_data.model_dump()))
        for item_data in data.items:
            world_session.add(world_models.ItemInstance(**item_data.model_dump()))
        for trap_data in data.traps:
            world_session.add(world_models.TrapInstance(**trap_data.model_dump()))

        # Story
        for camp_data in data.campaigns:
            story_session.add(story_models.Campaign(**camp_data.model_dump()))
        story_session.commit() # Commit campaigns so quests can link

        for camp_state_data in data.campaign_states:
            story_session.add(story_models.CampaignState(**camp_state_data.model_dump()))

        for quest_data in data.quests:
            story_session.add(story_models.ActiveQuest(**quest_data.model_dump()))
        for flag_data in data.flags:
            story_session.add(story_models.StoryFlag(**flag_data.model_dump()))

        # --- 4. Commit all changes ---
        logger.info("Committing all changes...")
        char_session.commit()
        world_session.commit()
        story_session.commit()
        sim_session.commit()

        logger.info("--- Load Game complete ---")
        return {"success": True, "name": save_file.save_name, "active_character_name": save_file.active_character_name}

    except Exception as e:
        logger.exception(f"Load game failed: {e}")
        char_session.rollback()
        world_session.rollback()
        story_session.rollback()
        sim_session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        char_session.close()
        world_session.close()
        story_session.close()
        sim_session.close()
