import sys
import os
import logging
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'AI-TTRPG')))

from monolith.modules.simulation_pkg import models
from monolith.modules.world_pkg.database import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_lore")

def verify():
    logger.info("Verifying lore ingestion...")
    
    with SessionLocal() as db:
        factions = db.query(models.Faction).all()
        
        if not factions:
            logger.warning("No factions found in database!")
            return

        for f in factions:
            print(f"\n--- Faction: {f.name} ---")
            print(f"Type: {f.faction_type}")
            print(f"Capital: {f.capital_city}")
            print(f"Goals: {f.goals}")
            print(f"Lore: {f.lore}")

if __name__ == "__main__":
    verify()
