import json
import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'AI-TTRPG')))

from monolith.modules.simulation_pkg import models
from monolith.modules.world_pkg.database import SessionLocal, engine, Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest_lore")

def ingest():
    logger.info("Starting lore ingestion...")
    
    # Ensure tables exist (including new columns)
    # Note: In a real prod env, we'd use Alembic. Here we rely on create_all 
    # which might not update existing tables if they already exist. 
    # For dev, we might need to drop/recreate or manually alter.
    # checking if we can force update schema is tricky without alembic.
    # We will assume the user handles the DB reset or we just try to write.
    Base.metadata.create_all(bind=engine)

    json_path = os.path.join(os.path.dirname(__file__), 'AI-TTRPG', 'lore', 'lore_data.json')
    
    if not os.path.exists(json_path):
        logger.error(f"Lore data file not found: {json_path}")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    with SessionLocal() as db:
        for entry in data:
            name = entry['name']
            logger.info(f"Processing faction: {name}")
            
            faction = db.query(models.Faction).filter(models.Faction.name == name).first()
            
            if not faction:
                logger.info(f"Creating new faction: {name}")
                faction = models.Faction(name=name)
                db.add(faction)
            
            # Update fields
            faction.faction_type = entry.get('faction_type')
            faction.capital_city = entry.get('capital_city')
            faction.goals = entry.get('goals')
            faction.lore = entry.get('lore')
            
            # Default strength if not set
            if faction.strength is None:
                faction.strength = 50
                
        db.commit()
        logger.info("Lore ingestion complete.")

if __name__ == "__main__":
    ingest()
