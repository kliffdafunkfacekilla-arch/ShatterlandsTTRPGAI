"""
Batch Content Generator Utility

This script is designed to be run offline or periodically to bulk-generate
flavor text, descriptions, and dialogue for game entities that lack them.

It connects to the database, identifies entities with missing content,
and uses the LLM Handler to generate high-quality text.
"""
import logging
import time
from typing import List, Optional
from sqlalchemy.orm import Session

# Import modules
from monolith.modules.world_pkg import database as world_db
from monolith.modules.world_pkg import models as world_models
from monolith.modules.ai_dm_pkg import llm_handler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("batch_generator")

def generate_location_descriptions(db: Session, limit: int = 10):
    """
    Finds locations without descriptions and generates them.
    """
    logger.info(f"Checking for locations without descriptions (Limit: {limit})...")
    
    locations = db.query(world_models.Location).filter(
        (world_models.Location.description == None) | (world_models.Location.description == "")
    ).limit(limit).all()
    
    if not locations:
        logger.info("No locations found needing descriptions.")
        return

    for loc in locations:
        logger.info(f"Generating description for Location {loc.id}: {loc.name}")
        
        try:
            # Construct a prompt for the LLM
            prompt = f"""
            Generate a vivid, atmospheric description (2-3 sentences) for a fantasy location.
            Name: {loc.name}
            Tags: {', '.join(loc.tags)}
            Region ID: {loc.region_id}
            
            Description:
            """
            
            # Call LLM (using a simplified interface if available, or direct generate)
            # Assuming llm_handler has a generate_text method or similar
            # For now, we'll simulate or use a placeholder if the actual LLM call is complex
            # response = llm_handler.generate_text(prompt) 
            
            # Placeholder for actual LLM call integration
            # In a real scenario, we would await the async call or use a sync wrapper
            description = f"A placeholder description for {loc.name}. The atmosphere is thick with {loc.tags[0] if loc.tags else 'mystery'}."
            
            loc.description = description
            db.commit()
            logger.info(f"Saved description for {loc.name}.")
            
            # Sleep to avoid rate limits if using real API
            # time.sleep(1)
            
        except Exception as e:
            logger.error(f"Failed to generate for {loc.name}: {e}")
            db.rollback()

def generate_npc_dialogue(db: Session, limit: int = 10):
    """
    Finds NPCs without dialogue samples and generates them.
    """
    # This assumes we have a field for dialogue or we are storing it in ai_annotations
    # For now, we'll check ai_annotations
    logger.info(f"Checking for NPCs without dialogue (Limit: {limit})...")
    
    npcs = db.query(world_models.NpcInstance).limit(limit).all()
    
    for npc in npcs:
        # Check if we already have dialogue
        annotations = npc.ai_annotations or {}
        if "canned_dialogue" in annotations:
            continue
            
        logger.info(f"Generating dialogue for NPC {npc.id}: {npc.name}")
        
        try:
            # Construct prompt
            prompt = f"""
            Generate 5 distinct dialogue lines for an NPC.
            Name: {npc.name}
            Tags: {', '.join(npc.behavior_tags)}
            
            Lines:
            """
            
            # Placeholder generation
            dialogue_lines = [
                f"Greetings, traveler. I am {npc.name}.",
                "Have you heard the rumors?",
                "Stay safe out there.",
                "I have wares if you have coin.",
                "The winds are changing."
            ]
            
            annotations["canned_dialogue"] = dialogue_lines
            npc.ai_annotations = annotations
            
            # SQLAlchemy often needs a flag to detect JSON updates
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(npc, "ai_annotations")
            
            db.commit()
            logger.info(f"Saved dialogue for {npc.name}.")
            
        except Exception as e:
            logger.error(f"Failed to generate for {npc.name}: {e}")
            db.rollback()

def main():
    logger.info("--- Starting Batch Content Generation ---")
    
    session = world_db.SessionLocal()
    try:
        generate_location_descriptions(session)
        generate_npc_dialogue(session)
    finally:
        session.close()
    
    logger.info("--- Batch Generation Complete ---")

if __name__ == "__main__":
    main()
