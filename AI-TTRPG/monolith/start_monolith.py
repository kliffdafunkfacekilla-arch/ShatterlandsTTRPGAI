# AI-TTRPG/monolith/start_monolith.py
"""
Main runner to start the TTRPG Monolith.

This script ensures all database migrations for all
stateful modules are applied before starting the orchestrator.
"""
import asyncio
import sys
from pathlib import Path
import traceback
from typing import Optional
import os
import logging

# --- Setup Logging ---
# Configure basic logging to see startup messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
logger = logging.getLogger("monolith.startup")

# --- Alembic Import ---
try:
    from alembic.config import Config as AlembicConfig
    from alembic import command as alembic_command
except ImportError:
    logger.warning("Alembic not found. `pip install alembic` is required. Skipping migrations.")
    AlembicConfig = None
    alembic_command = None

# --- Path Setup ---
# Ensure AI-TTRPG folder is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from monolith.orchestrator import get_orchestrator
from monolith.modules import register_all

# --- Database Migration Function ---
def _run_migrations_for_module(module_name: str, root_path: Path, mode: str):
    """
    Generic function to find and run Alembic migrations for a module.

    Resolves paths to the module's package and alembic configuration.
    Supports 'migrate', 'auto', and 'none' modes for database initialization.

    Args:
        module_name (str): The name of the module (e.g., 'character').
        root_path (Path): The root directory of the monolith.
        mode (str): The migration mode ('migrate', 'auto', 'none').
    """
    if not AlembicConfig or not alembic_command:
        logger.warning(f"Skipping migrations for '{module_name}' (Alembic not loaded).")
        return

    logger.info(f"--- Running Migrations for: {module_name} (Mode: {mode}) ---")

    if mode == "none":
        logger.info(f"Skipping migrations for '{module_name}' as per mode=none.")
        return

    try:
        pkg_path = root_path / "monolith" / "modules" / module_name / f"{module_name}_pkg"
        alembic_ini_path = pkg_path / "alembic.ini"
        alembic_script_location = pkg_path / "alembic"

        if not alembic_ini_path.exists():
            logger.warning(f"alembic.ini not found for '{module_name}' at: {alembic_ini_path}. Skipping migrations.")
            return

        if not alembic_script_location.exists():
            logger.warning(f"alembic script location not found for '{module_name}' at: {alembic_script_location}. Skipping migrations.")
            return

        # Dynamically get the DATABASE_URL from the module's database.py
        try:
            db_module_path = f"monolith.modules.{module_name}_pkg.database"
            db_module = importlib.import_module(db_module_path)
            database_url = getattr(db_module, "DATABASE_URL")
            logger.info(f"Using DB URL from module: {database_url}")
        except Exception as e:
            logger.exception(f"Could not import DATABASE_URL from {db_module_path}: {e}")
            if mode == "migrate":
                raise
            return

        # Configure and run Alembic
        cfg = AlembicConfig(str(alembic_ini_path))
        cfg.set_main_option("script_location", str(alembic_script_location))
        cfg.set_main_option("sqlalchemy.url", database_url)

        logger.info(f"Running alembic upgrade head for '{module_name}'...")
        alembic_command.upgrade(cfg, "head")
        logger.info(f"Alembic upgrade complete for '{module_name}'.")

    except Exception as e:
        logger.exception(f"Alembic migration failed for '{module_name}': {e}")
        if mode == "migrate":
            raise RuntimeError(f"Migration failed for {module_name} in 'migrate' mode.")

        # Fallback to create_all()
        if mode == "auto":
            try:
                logger.warning(f"Falling back to create_all() for '{module_name}'...")
                db_module = importlib.import_module(f"monolith.modules.{module_name}_pkg.database")
                engine = getattr(db_module, "engine")
                Base = getattr(db_module, "Base")
                Base.metadata.create_all(bind=engine)
                logger.info(f"create_all() successful for '{module_name}'.")
            except Exception as create_e:
                logger.exception(f"Fallback create_all() ALSO FAILED for '{module_name}': {create_e}")
                raise

# --- Main Startup Function ---
async def _main():
    """
    The main async entry point for the Monolith.

    1. Runs database migrations for all modules.
    2. Registers modules with the Orchestrator.
    3. Starts the Orchestrator.
    4. Enters a keep-alive loop (unless run-once mode is set).
    """
    orch = get_orchestrator()
    bus = orch.bus

    # 1. Run Migrations for all stateful modules
    import importlib # Move import to top-level

    # Get migration mode from environment, default to 'auto'
    # 'auto': Try Alembic, fallback to create_all()
    # 'migrate': Force Alembic, fail on error
    # 'none': Skip all DB initialization
    migration_mode = os.environ.get("MONOLITH_DB_INIT", "auto").lower()

    _run_migrations_for_module("character", ROOT, migration_mode)
    _run_migrations_for_module("world", ROOT, migration_mode)
    _run_migrations_for_module("story", ROOT, migration_mode)

    # 2. Register all modules (this loads their data, etc.)
    logger.info("Registering all monolith modules...")
    register_all(orch)

    # 3. Start the orchestrator
    await orch.start()

    # Give modules a moment to subscribe their handlers
    await asyncio.sleep(0.1)
    
    # 4. Monolith is now running
    logger.info("--- AI-TTRPG Monolith is now running ---")
    logger.info("The application is ready to accept connections.")
    logger.info("This script will now run indefinitely.")
    
    # Keep the event loop alive indefinitely, unless in test mode
    if os.environ.get("MONOLITH_RUN_ONCE"):
        logger.info("MONOLITH_RUN_ONCE is set. Exiting after startup.")
        # Give a brief moment for any final logs to flush
        await asyncio.sleep(0.1)
    else:
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(_main())
