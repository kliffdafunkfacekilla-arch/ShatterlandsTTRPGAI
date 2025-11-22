# AI-TTRPG/monolith/modules/world_pkg/crud.py
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from . import models, schemas
from typing import List, Optional
from fastapi import HTTPException
import logging

# --- MONOLITH IMPORT ---
# Import our new, self-contained map module
# from .. import map as map_api # MOVED TO SERVICES
# --- END IMPORT ---

logger = logging.getLogger("monolith.world.crud")

# --- Faction ---
def get_faction(db: Session, faction_id: int) -> Optional[models.Faction]:
    """
    Retrieves a faction by ID.
    """
    return db.query(models.Faction).filter(models.Faction.id == faction_id).first()

def create_faction(db: Session, faction: schemas.FactionCreate) -> models.Faction:
    """
    Creates a new faction entry in the database.
    """
    db_faction = models.Faction(**faction.dict())
    db.add(db_faction)
    db.commit()
    db.refresh(db_faction)
    return db_faction

# --- Region ---
def get_region(db: Session, region_id: int) -> Optional[models.Region]:
    """
    Retrieves a region by ID.
    """
    return db.query(models.Region).filter(models.Region.id == region_id).first()

def create_region(db: Session, region: schemas.RegionCreate) -> models.Region:
    """
    Creates a new region entry in the database.
    """
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
    """
    Creates a new location in the database.
    """
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
    Updates the generated map data, seed, and spawn points for a location.
    Used to persist a procedurally generated map.
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
    """
    Updates the AI annotations for a location (e.g., descriptions of scene elements).
    """
    db_loc = get_location(db, location_id)
    if db_loc:
        db_loc.ai_annotations = annotations
        flag_modified(db_loc, "ai_annotations")
        db.commit()
        db.refresh(db_loc)
    return db_loc

# --- NPC Instance ---
def get_npc(db: Session, npc_id: int) -> Optional[models.NpcInstance]:
    """
    Retrieves an NPC instance by ID.
    """
    return db.query(models.NpcInstance).filter(models.NpcInstance.id == npc_id).first()

def spawn_npc(db: Session, npc: schemas.NpcSpawnRequest) -> models.NpcInstance:
    """
    Creates a new NPC instance in the world from a spawn request.
    Initializes vitals, resource pools, and abilities.
    """
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
    Updates an existing NPC instance with new values.
    Handles damage, status updates, movement, etc.
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
    """
    Appends an injury record to an NPC's injury list.
    """
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
    """
    Removes the first occurrence of an injury with the specified severity from an NPC.
    """
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
    """
    Permanently deletes an NPC and their inventory from the database.
    """
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
    """
    Creates a new trap instance in the world.
    """
    db_trap = models.TrapInstance(**trap.dict())
    db.add(db_trap)
    db.commit()
    db.refresh(db_trap)
    return db_trap

def get_trap(db: Session, trap_id: int) -> Optional[models.TrapInstance]:
    """
    Retrieves a trap by ID.
    """
    return db.query(models.TrapInstance).filter(models.TrapInstance.id == trap_id).first()

def get_traps_for_location(db: Session, location_id: int) -> List[models.TrapInstance]:
    """
    Retrieves all traps in a specific location.
    """
    return db.query(models.TrapInstance).filter(models.TrapInstance.location_id == location_id).all()

def update_trap_status(db: Session, trap_id: int, status: str) -> Optional[models.TrapInstance]:
    """
    Updates the status of a trap (e.g., 'armed', 'triggered', 'disarmed').
    """
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

# --- CONTEXT GETTER (MOVED TO SERVICES) ---
# def get_location_context(db: Session, location_id: int):
#     ... moved to services.py ...
