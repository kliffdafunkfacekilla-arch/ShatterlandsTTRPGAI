# AI-TTRPG/monolith/modules/map.py
"""
Fully self-contained Map Generator module for the monolith.

This module loads all map generation data from its internal 'map_pkg/data/'
directory at startup and provides a synchronous function for other
modules (like 'world') to call directly.
"""
from typing import Any, Dict, List, Optional
import logging
import time

# Import from this module's own internal package
from .map_pkg import core as map_core
from .map_pkg import models as map_models
from .map_pkg import data_loader as map_data_loader

logger = logging.getLogger("monolith.map")

# --- Data Loading ---
# Load all map data into memory ONCE when this module is first imported
try:
    logger.info("[map] Loading all map data from 'map_pkg/data/'...")
    map_data_loader.load_data()
    logger.info("[map] Map data loaded successfully.")
except Exception as e:
    logger.exception(f"[map] FATAL: Failed to load map data: {e}")

# --- Public API Functions ---
def generate_map(tags: List[str], seed: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates a new map based on tags.
    This is a synchronous, CPU-bound operation.
    """
    logger.info(f"[map] Generating new map with tags: {tags}")

    # 1. Select Algorithm
    algorithm = map_core.select_algorithm(tags)
    if not algorithm:
        logger.warning(f"No algorithm found for tags: {tags}. Using default 'Forest'.")
        # Fallback to a known default if tags fail
        algorithm = map_core.select_algorithm(["forest", "outside"])
        if not algorithm: # Still no algorithm?
             raise Exception("Default map generation algorithm 'forest' not found.")

    # 2. Determine Seed
    seed_used = seed or str(time.time())

    # 3. Run Generation
    try:
        # We call the core logic directly
        response_model = map_core.run_generation(
            algorithm,
            seed_used,
            width_override=None,
            height_override=None
        )
        # Convert Pydantic model to dict for the caller
        return response_model.model_dump()
    except Exception as e:
        logger.exception(f"Error during core map generation: {e}")
        raise

def register(orchestrator) -> None:
    # This module is self-contained. It doesn't subscribe
    # to the event bus but is loaded and its data is cached.
    # Other modules will import and call its functions.
    logger.info("[map] module registered (self-contained logic)")
