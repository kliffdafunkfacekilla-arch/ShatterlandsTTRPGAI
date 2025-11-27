import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'AI-TTRPG')))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fix_db_schema")

try:
    from monolith.modules.world_pkg.database import engine, Base
    # Import ALL models that use this Base to ensure they are registered
    from monolith.modules.world_pkg import models as world_models
    from monolith.modules.simulation_pkg import models as sim_models
except ImportError as e:
    logger.error(f"Import failed: {e}")
    sys.exit(1)

def fix_schema():
    logger.info("Fixing database schema...")
    logger.info(f"Registered tables in metadata: {Base.metadata.tables.keys()}")
    
    # Create all missing tables
    Base.metadata.create_all(bind=engine)
    logger.info("Schema update complete.")

if __name__ == "__main__":
    fix_schema()
