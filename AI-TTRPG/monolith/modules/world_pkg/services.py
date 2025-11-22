from sqlalchemy.orm import Session
from fastapi import HTTPException
import logging
from typing import Dict, Any, List, Optional

from . import models, schemas, crud
from .. import map as map_api

logger = logging.getLogger("monolith.world.services")

def get_location_context(db: Session, location_id: int) -> Dict[str, Any]:
    """
    Retrieves the full context for a given location, including region,
    NPCs, and items. Handles on-demand map generation if missing.
    """
    logger.info(f"Getting full context for location_id: {location_id}")
    
    # 1. Get Location (Simple Fetch)
    location = crud.get_location(db, location_id)
    if not location:
        logger.error(f"Location not found for id: {location_id}")
        raise HTTPException(status_code=404, detail="Location not found")

    # 2. On-Demand Map Generation
    if not location.generated_map_data:
        logger.warning(f"Location {location_id} ('{location.name}') has no map data. Generating one.")
        try:
            # Get tags or default
            tags = location.tags
            if not tags or not isinstance(tags, list):
                tags = ["forest", "outside", "clearing"]

            # Call map API (Synchronous for now, could be async in future)
            map_response_dict = map_api.generate_map(tags=tags)

            # Create update schema
            map_update_schema = schemas.LocationMapUpdate(
                generated_map_data=map_response_dict.get("map_data"),
                map_seed=map_response_dict.get("seed_used"),
                spawn_points=map_response_dict.get("spawn_points")
            )

            # Save to DB
            location = crud.update_location_map(db, location_id, map_update_schema)
            logger.info(f"Successfully generated and saved new map for location {location_id}.")

        except Exception as e:
            logger.exception(f"Failed to generate map for location {location_id}: {e}")
            # Continue without map data

    # 3. Fetch Relations
    npcs = db.query(models.NpcInstance).filter(models.NpcInstance.location_id == location_id).all()
    items = db.query(models.ItemInstance).filter(models.ItemInstance.location_id == location_id).all()
    region = crud.get_region(db, location.region_id)

    if not region:
        logger.error(f"Data integrity error: Location {location_id} has region_id {location.region_id} but no matching region was found.")
        raise HTTPException(status_code=500, detail=f"Data integrity error: Region {location.region_id} not found for location {location_id}.")

    # 4. Build Response Dictionary
    return {
        "id": location.id,
        "name": location.name,
        "region_name": region.name,
        "description": getattr(location, 'description', None),
        "generated_map_data": location.generated_map_data,
        "map_seed": location.map_seed,
        "ai_annotations": location.ai_annotations,
        "spawn_points": location.spawn_points,
        "npcs": [schemas.NpcInstance.from_orm(npc).model_dump() for npc in npcs],
        "items": [schemas.ItemInstance.from_orm(item).model_dump() for item in items],
        "trap_instances": [schemas.TrapInstance.from_orm(trap).model_dump() for trap in location.trap_instances],
        "tags": location.tags,
        "exits": location.exits,
        "region": schemas.Region.from_orm(region).model_dump(),
    }
