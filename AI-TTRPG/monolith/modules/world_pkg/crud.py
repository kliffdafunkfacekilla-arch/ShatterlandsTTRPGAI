# AI-TTRPG/monolith/modules/world_pkg/crud.py
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from . import models, schemas
from typing import List, Optional
from fastapi import HTTPException
import logging

# --- MONOLITH IMPORT ---
# Import our new, self-contained map module
from .. import map as map_api
# --- END IMPORT ---

logger = logging.getLogger("monolith.world.crud")

# --- Faction ---
def get_faction(db: Session, faction_id: int) -> Optional[models.Faction]:
    return db.query(models.Faction).filter(models.Faction.id == faction_id).first()

def create_faction(db: Session, faction: schemas.FactionCreate) -> models.Faction:
    db_faction = models.Faction(**faction.dict())
    db.add(db_faction)
    db.commit()
    db.refresh(db_faction)
    return db_faction

# --- Region ---
def get_region(db: Session, region_id: int) -> Optional[models.Region]:
    return db.query(models.Region).filter(models.Region.id == region_id).first()

def create_region(db: Session, region: schemas.RegionCreate) -> models.Region:
    db_region = models.Region(name=region.name)
    db.add(db_region)
    db.commit()
    db.refresh(db_region)
    return db_region

# --- Location ---
def get_location(db: Session, location_id: int) -> Optional[models.Location]:
    """
    Gets a single location by ID.
    The 'relationships' in models.py will auto-load its
    region, NPCs, and items.
    """
    return db.query(models.Location).filter(models.Location.id == location_id).first()

def create_location(db: Session, loc: schemas.LocationCreate) -> models.Location:
    db_loc = models.Location(
        name=loc.name,
        region_id=loc.region_id,
        tags=loc.tags,
        exits=loc.exits
    )
    db.add(db_loc)
    db.commit()
    db.refresh(db_loc)
    return db_loc

def update_location_map(db: Session, location_id: int, map_update: schemas.LocationMapUpdate) -> Optional[models.Location]:
    """
    This is how the story_engine saves a persistent map.
    """
    db_loc = get_location(db, location_id)
    if db_loc:
        db_loc.generated_map_data = map_update.generated_map_data
        db_loc.map_seed = map_update.map_seed
        db_loc.spawn_points = map_update.spawn_points

        # This line is important for JSON fields
        flag_modified(db_loc, "generated_map_data")
        flag_modified(db_loc, "spawn_points")

        db.commit()
        db.refresh(db_loc)
    return db_loc

def update_location_annotations(db: Session, location_id: int, annotations: dict) -> Optional[models.Location]:
    db_loc = get_location(db, location_id)
    if db_loc:
        db_loc.ai_annotations = annotations
        flag_modified(db_loc, "ai_annotations")
        db.commit()
        db.refresh(db_loc)
    return db_loc

# --- NPC Instance ---
def get_npc(db: Session, npc_id: int) -> Optional[models.NpcInstance]:
    return db.query(models.NpcInstance).filter(models.NpcInstance.id == npc_id).first()

def spawn_npc(db: Session, npc: schemas.NpcSpawnRequest) -> models.NpcInstance:
    # --- THIS FUNCTION IS MODIFIED ---
    db_npc = models.NpcInstance(
        template_id=npc.template_id,
        location_id=npc.location_id,
        name_override=npc.name_override,

        # Core Vitals
        current_hp=npc.current_hp if npc.current_hp is not None else 10,
        max_hp=npc.max_hp if npc.max_hp is not None else 10,

        # New Vitals
        temp_hp=npc.temp_hp if npc.temp_hp is not None else 0,
        max_composure=npc.max_composure if npc.max_composure is not None else 10,
        current_composure=npc.current_composure if npc.current_composure is not None else 10,

        # New JSON fields
        resource_pools=npc.resource_pools if npc.resource_pools is not None else {},
        abilities=npc.abilities if npc.abilities is not None else [],

        # Existing fields
        behavior_tags=npc.behavior_tags,
        coordinates=npc.coordinates # Save the coordinates
    )
    # --- END MODIFICATION ---

    db.add(db_npc)
    db.commit()
    db.refresh(db_npc)
    return db_npc

def update_npc(db: Session, npc_id: int, updates: schemas.NpcUpdate) -> Optional[models.NpcInstance]:
    """
    This is how we deal damage, apply status, or move an NPC.
    """
    db_npc = get_npc(db, npc_id)
    if db_npc:
        # 'exclude_unset=True' means we only get the fields
        # that were actually sent in the request.
        update_data = updates.dict(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_npc, key, value)

        # --- THIS SECTION IS MODIFIED ---
        # Flag all JSON fields as modified if they are in the update
        if "status_effects" in update_data:
            flag_modified(db_npc, "status_effects")
        if "coordinates" in update_data:
            flag_modified(db_npc, "coordinates")
        if "resource_pools" in update_data:
            flag_modified(db_npc, "resource_pools")
        if "abilities" in update_data:
            flag_modified(db_npc, "abilities")
        if "injuries" in update_data:
            flag_modified(db_npc, "injuries")
        # --- END MODIFICATION ---

        db.commit()
        db.refresh(db_npc)
    return db_npc

def apply_status_to_npc(db: Session, npc_id: int, status_id: str) -> Optional[models.NpcInstance]:
    """Adds a status effect ID to the NPC's status_effects list."""
    db_npc = get_npc(db, npc_id)
    if db_npc:
        status_effects = db_npc.status_effects or []
        if status_id not in status_effects:
            status_effects.append(status_id)
            logger.info(f"Applying status '{status_id}' to NPC {npc_id}")
        db_npc.status_effects = status_effects
        flag_modified(db_npc, "status_effects")
        db.commit()
        db.refresh(db_npc)
    return db_npc

def remove_status_from_npc(db: Session, npc_id: int, status_id: str) -> Optional[models.NpcInstance]:
    """Removes a status effect ID from the NPC's status_effects list."""
    db_npc = get_npc(db, npc_id)
    if db_npc:
        status_effects = db_npc.status_effects or []
        if status_id in status_effects:
            status_effects.remove(status_id)
            logger.info(f"Removing status '{status_id}' from NPC {npc_id}")
        db_npc.status_effects = status_effects
        flag_modified(db_npc, "status_effects")
        db.commit()
        db.refresh(db_npc)
    return db_npc


def apply_injury_to_npc(db: Session, npc_id: int, injury: dict) -> Optional[models.NpcInstance]:
    """Applies an injury to an NPC."""
    db_npc = get_npc(db, npc_id)
    if db_npc:
        injuries = db_npc.injuries or []
        injuries.append(injury)
        db_npc.injuries = injuries
        flag_modified(db_npc, "injuries")
        db.commit()
        db.refresh(db_npc)
        logger.info(f"Applied injury to NPC {npc_id}")
    return db_npc


def remove_injury_from_npc(db: Session, npc_id: int, severity: str) -> Optional[models.NpcInstance]:
    """Removes the first injury of a given severity from an NPC."""
    db_npc = get_npc(db, npc_id)
    if db_npc:
        injuries = db_npc.injuries or []
        injury_to_remove = None
        for inj in injuries:
            if inj.get("severity") == severity:
                injury_to_remove = inj
                break

        if injury_to_remove:
            injuries.remove(injury_to_remove)
            db_npc.injuries = injuries
            flag_modified(db_npc, "injuries")
            db.commit()
            db.refresh(db_npc)
            logger.info(f"Removed '{severity}' injury from NPC {npc_id}")
    return db_npc


def delete_npc(db: Session, npc_id: int) -> bool:
    """This is how we remove a dead NPC from the world."""
    db_npc = get_npc(db, npc_id)
    if db_npc:
        # Also delete all items in their inventory
        db.query(models.ItemInstance).filter(models.ItemInstance.npc_id == npc_id).delete()

        db.delete(db_npc)
        db.commit()
        return True
    return False

# --- Trap Instance ---
def create_trap(db: Session, trap: schemas.TrapInstanceCreate) -> models.TrapInstance:
    db_trap = models.TrapInstance(**trap.dict())
    db.add(db_trap)
    db.commit()
    db.refresh(db_trap)
    return db_trap

def get_trap(db: Session, trap_id: int) -> Optional[models.TrapInstance]:
    return db.query(models.TrapInstance).filter(models.TrapInstance.id == trap_id).first()

def get_traps_for_location(db: Session, location_id: int) -> List[models.TrapInstance]:
    return db.query(models.TrapInstance).filter(models.TrapInstance.location_id == location_id).all()

def update_trap_status(db: Session, trap_id: int, status: str) -> Optional[models.TrapInstance]:
    db_trap = get_trap(db, trap_id)
    if db_trap:
        db_trap.status = status
        db.commit()
        db.refresh(db_trap)
    return db_trap

# --- Item Instance ---
def spawn_item(db: Session, item: schemas.ItemSpawnRequest) -> models.ItemInstance:
    """Spawns an item, either on the ground or in an NPC's inventory."""
    db_item = models.ItemInstance(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def delete_item(db: Session, item_id: int) -> bool:
    """This is how a player picks up an item."""
    db_item = db.query(models.ItemInstance).filter(models.ItemInstance.id == item_id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
        return True
    return False

# --- CONTEXT GETTER (MODIFIED) ---
def get_location_context(db: Session, location_id: int):
    """
    Retrieves the full context for a given location, including region,
    NPCs, and items.

    *** REFACTORED: This function now handles on-demand map generation. ***
    """
    logger.info(f"Getting full context for location_id: {location_id}")
    location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not location:
        logger.error(f"Location not found for id: {location_id}")
        raise HTTPException(status_code=404, detail="Location not found")

    # --- NEW: On-Demand Map Generation ---
    if not location.generated_map_data:
        logger.warning(f"Location {location_id} ('{location.name}') has no map data. Generating one.")
        try:
            # 1. Get tags from location, or provide a default
            tags = location.tags
            if not tags or not isinstance(tags, list):
                tags = ["forest", "outside", "clearing"] # A safe default

            # 2. Call the monolith's map_api synchronously
            map_response_dict = map_api.generate_map(tags=tags)

            # 3. Create the Pydantic schema for the update
            map_update_schema = schemas.LocationMapUpdate(
                generated_map_data=map_response_dict.get("map_data"),
                map_seed=map_response_dict.get("seed_used"),
                spawn_points=map_response_dict.get("spawn_points")
            )

            # 4. Save the new map to the database
            # This call commits to the DB and refreshes the 'location' object
            update_location_map(db, location_id, map_update_schema)
            logger.info(f"Successfully generated and saved new map for location {location_id}.")

        except Exception as e:
            logger.exception(f"Failed to generate map for location {location_id}: {e}")
            # Do not raise an error; we can still return the context without a map
    # --- END NEW LOGIC ---

    npcs = db.query(models.NpcInstance).filter(models.NpcInstance.location_id == location_id).all()
    items = db.query(models.ItemInstance).filter(models.ItemInstance.location_id == location_id).all()

    # Get Region name
    region = db.query(models.Region).filter(models.Region.id == location.region_id).first()

    # --- START OF NEW FIX ---
    if not region:
        logger.error(f"Data integrity error: Location {location_id} has region_id {location.region_id} but no matching region was found.")
        raise HTTPException(status_code=500, detail=f"Data integrity error: Region {location.region_id} not found for location {location_id}.")

    # Return a DICTIONARY (to match the old API response)
    return {
        "id": location.id, # <-- ADDED (was missing from your old code, but implied by schema)
        "name": location.name,
        "region_name": region.name,
        "description": getattr(location, 'description', None),
        "generated_map_data": location.generated_map_data,
        "map_seed": location.map_seed,
        "ai_annotations": location.ai_annotations,
        "spawn_points": location.spawn_points, # <-- ADDED
        # Use the Pydantic schemas to convert ORM objects
        "npcs": [schemas.NpcInstance.from_orm(npc).model_dump() for npc in npcs],
        "items": [schemas.ItemInstance.from_orm(item).model_dump() for item in items],
        # Add traps and other fields if they exist in your schema/model
        "trap_instances": [schemas.TrapInstance.from_orm(trap).model_dump() for trap in location.trap_instances],
        "tags": location.tags,
        "exits": location.exits,
        "region": schemas.Region.from_orm(region).model_dump(),
        # Use the current schema model names
        "npcs": [schemas.NpcInstance.from_orm(npc) for npc in npcs],
        "items": [schemas.ItemInstance.from_orm(item) for item in items],

    }
