import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'AI-TTRPG')))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_world")

try:
    from monolith.modules.world_pkg import crud, schemas
    from monolith.modules.world_pkg.database import SessionLocal, engine, Base
except ImportError as e:
    logger.error(f"Import failed: {e}")
    sys.exit(1)

def seed():
    logger.info("Seeding default world data...")
    
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        # Check if region exists
        region = crud.get_region(db, 1)
        if not region:
            logger.info("Creating default region...")
            region = crud.create_region(db, schemas.RegionCreate(name="The Shattered Isles"))
        
        # Check if location exists
        location = crud.get_location(db, 1)
        if not location:
            logger.info("Creating default location (ID 1)...")
            location = crud.create_location(db, schemas.LocationCreate(
                name="Starting Clearing",
                region_id=region.id,
                tags=["forest", "clearing", "safe"],
                exits={}
            ))
            logger.info(f"Created location: {location.name} (ID: {location.id})")
        else:
            logger.info(f"Location already exists: {location.name} (ID: {location.id})")

if __name__ == "__main__":
    seed()
