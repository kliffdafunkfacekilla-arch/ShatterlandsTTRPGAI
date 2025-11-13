
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
from contextlib import asynccontextmanager
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
import httpx
import logging
import json

logger = logging.getLogger("uvicorn.error")
MAP_GENERATOR_URL = "http://127.0.0.1:8006" # The address of your Map Tool

# Import all our other files
from . import crud, models, schemas
from .database import SessionLocal, engine, Base, DATABASE_URL # <-- Import Base and DATABASE_URL
from sqlalchemy.orm import joinedload

# --- NEW LIFESPAN FUNCTION ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("INFO: World Engine: Lifespan startup...")

    # 1. Define paths relative to this file
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _service_root = os.path.abspath(os.path.join(_current_dir, ".."))
    alembic_ini_path = os.path.join(_service_root, "alembic.ini")
    alembic_script_location = os.path.join(_service_root, "alembic")

    print(f"INFO: World Engine: Database URL: {DATABASE_URL}")
    print(f"INFO: World Engine: Alembic .ini path: {alembic_ini_path}")

    try:
        # 2. Create Alembic Config object
        alembic_cfg = AlembicConfig(alembic_ini_path)

        # 3. Set the script location (must be absolute)
        alembic_cfg.set_main_option("script_location", alembic_script_location)

        # 4. Set the database URL to be the same one the app uses
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        # 5. Run the "upgrade head" command programmatically
        print("INFO: World Engine: Running Alembic upgrade head...")
        alembic_command.upgrade(alembic_cfg, "head")
        print("INFO: World Engine: Alembic upgrade complete.")

    except Exception as e:
        print(f"FATAL: World Engine: Database migration failed on startup: {e}")
        # As a fallback, create tables directly (won't run seeding, but prevents crash)
        print("INFO: World Engine: Running Base.metadata.create_all() as fallback...")
        Base.metadata.create_all(bind=engine)

    # App is ready to start
    yield

    # Shutdown logic
    print("INFO: World Engine: Shutting down.")

    # --- LORE LOADER ---
    def load_lore() -> list[dict]:
        lore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "lore.json")
        try:
            with open(lore_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load lore: {e}")
            return []


# This creates the FastAPI application instance
app = FastAPI(
    title="World Engine",
    description="Manages the state of all locations, NPCs, items, and world data.",
    lifespan=lifespan  # <--- ASSIGN THE LIFESPAN FUNCTION
)

# Add CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # The origin of the frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency ---
def get_db():
    """
    This function is a 'dependency'.
    Each API call will run this function to get a
    database session, and it automatically closes
    the session when the API call is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API Endpoints ---
# These are the 'doors' our story_engine will use.

@app.get("/")
def read_root():
    return {"status": "World Engine is running."}

# --- LORE ENDPOINTS ---
@app.get("/v1/lore", response_model=List[Dict[str, Any]])
def get_lore():
    """Return all lore entries."""
    return load_lore()

@app.get("/v1/lore/{lore_id}", response_model=Dict[str, Any])
def get_lore_entry(lore_id: str):
    """Return a single lore entry by id."""
    for entry in load_lore():
        if entry.get("id") == lore_id:
            return entry
    raise HTTPException(status_code=404, detail="Lore entry not found")

# --- MAP ENDPOINTS ---
@app.post("/v1/maps", response_model=schemas.Map)
def create_map(map_data: schemas.MapBase, db: Session = Depends(get_db)):
    db_map = models.Map(**map_data.dict())
    db.add(db_map)
    db.commit()
    db.refresh(db_map)
    return db_map

@app.get("/v1/maps/{map_id}", response_model=schemas.Map)
def get_map(map_id: int, db: Session = Depends(get_db)):
    db_map = db.query(models.Map).options(joinedload(models.Map.tiles)).filter(models.Map.id == map_id).first()
    if not db_map:
        raise HTTPException(status_code=404, detail="Map not found")
    return db_map

@app.get("/v1/maps", response_model=List[schemas.Map])
def list_maps(db: Session = Depends(get_db)):
    db_maps = db.query(models.Map).all()
    return db_maps

@app.post("/v1/tiles", response_model=schemas.Tile)
def create_tile(tile_data: schemas.TileBase, db: Session = Depends(get_db)):
    db_tile = models.Tile(**tile_data.dict())
    db.add(db_tile)
    db.commit()
    db.refresh(db_tile)
    return db_tile

@app.get("/v1/tiles/{tile_id}", response_model=schemas.Tile)
def get_tile(tile_id: int, db: Session = Depends(get_db)):
    db_tile = db.query(models.Tile).filter(models.Tile.id == tile_id).first()
    if not db_tile:
        raise HTTPException(status_code=404, detail="Tile not found")
    return db_tile

@app.get("/v1/tiles", response_model=List[schemas.Tile])
def list_tiles(db: Session = Depends(get_db)):
    db_tiles = db.query(models.Tile).all()
    return db_tiles

# --- Location Endpoints ---

@app.get("/v1/locations/{location_id}", response_model=schemas.Location)
def read_location(location_id: int, db: Session = Depends(get_db)):
    """
    Get all data for a single location.
    If the map doesn't exist, this function will generate, save,
    and populate it before returning.
    """
    try:
        # 1. Get the location data from the database
        db_loc = crud.get_location(db, location_id=location_id)
        if db_loc is None:
            raise HTTPException(status_code=404, detail="Location not found")

        # 2. CHECK: Does the map already exist?
        if db_loc.generated_map_data is not None:
            logger.info(f"Map for {location_id} already exists. Returning from DB.")
            return db_loc # The map is already generated. Just return it.

        # 3. GENERATE: The map is null, so we must build it.
        logger.info(f"Map for {location_id} not found. Generating...")

        # 4. BUILD PROMPT: Gather all tags from our own data
        prompt_tags = []

        # Add static biome tags
        if db_loc.tags:
            prompt_tags.extend(db_loc.tags)

        # Add "sticky pin" tags from annotations
        if db_loc.ai_annotations:
            for key, value in db_loc.ai_annotations.items():
                if isinstance(value, dict) and "type" in value:
                    prompt_tags.append(f"spawn:{value['type']}") # e.g., "spawn:quest_item"

        # (Optional) Add region-level tags (weather, war_zone, etc.)
        if db_loc.region and db_loc.region.environmental_effects:
            prompt_tags.extend(db_loc.region.environmental_effects)

        # (Optional) Fill in blanks
        if not any("size:" in tag for tag in prompt_tags):
            prompt_tags.append("size:medium")

        logger.info(f"Calling Map Generator tool with tags: {prompt_tags}")

        # 5. CALL TOOL: Call the map_generator
        import asyncio
        async def generate_map():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{MAP_GENERATOR_URL}/v1/generate",
                    json={"tags": prompt_tags},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        map_gen_data = asyncio.run(generate_map())

        # 6. SAVE TO ATLAS: Save the new map data back to the DB
        map_update = schemas.LocationMapUpdate(
            generated_map_data=map_gen_data.get("map_data"),
            map_seed=map_gen_data.get("seed_used"),
            spawn_points=map_gen_data.get("spawn_points")
        )
        db_loc = crud.update_location_map(db, location_id, map_update)
        logger.info(f"New map for {location_id} saved to database.")

        # 7. PLACE PINS: Spawn items/NPCs from the "sticky pins"
        spawn_points = db_loc.spawn_points or {}
        player_spawns = spawn_points.get("player", [[1,1]])

        if db_loc.ai_annotations:
            logger.info("Placing 'sticky pin' items/NPCs...")
            for key, pin in db_loc.ai_annotations.items():
                if not isinstance(pin, dict): continue

                # Use a pin's coords, or default to a player spawn point
                coords = pin.get("coordinates", player_spawns[0])

                if pin.get("type") == "item":
                    item_req = schemas.ItemSpawnRequest(
                        template_id=pin.get("item_id", "item_iron_key"),
                        quantity=pin.get("quantity", 1),
                        location_id=location_id,
                        coordinates=coords
                    )
                    crud.spawn_item(db, item_req)
                    logger.info(f"Spawned pin item: {item_req.template_id}")

                # (Add logic for "npc" pins here later)

        # 8. RETURN: Return the fully generated and populated location
        db.refresh(db_loc)
        return db_loc

    except httpx.RequestError as e:
        logger.error(f"Failed to connect to map_generator: {e}")
        raise HTTPException(status_code=503, detail="Map generation service unavailable.")
    except httpx.HTTPStatusError as e:
        logger.error(f"map_generator returned error: {e.response.text}")
        raise HTTPException(status_code=500, detail="Map generation failed.")
    except Exception as e:
        logger.exception(f"Error in read_location for {location_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/v1/locations/{location_id}/annotations", response_model=schemas.Location)
def update_location_ai_annotations(
    location_id: int,
    annotation_update: schemas.LocationAnnotationUpdate,
    db: Session = Depends(get_db)
):
    """
    Used by the story_engine to save its own notes, descriptions,
    or flags about a location.
    """
    db_loc = crud.update_location_annotations(db, location_id, annotation_update.ai_annotations)
    if db_loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return db_loc

@app.put("/v1/locations/{location_id}/map", response_model=schemas.Location)
def update_location_generated_map(
    location_id: int,
    map_update: schemas.LocationMapUpdate,
    db: Session = Depends(get_db)
):
    """
    Used by the story_engine to save a procedurally generated
    map to the database, making it persistent.
    """
    db_loc = crud.update_location_map(db, location_id, map_update)
    if db_loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return db_loc


@app.post("/v1/locations/", response_model=schemas.Location, status_code=201)
def create_new_location(
    location: schemas.LocationCreate, db: Session = Depends(get_db)
):
    """
    Create a new location within a specific region.
    You must create a Region first via POST /v1/regions/.
    """
    # Optional: Check if region_id exists
    db_region = crud.get_region(db, region_id=location.region_id)
    if db_region is None:
        raise HTTPException(status_code=404, detail=f"Region with id {location.region_id} not found. Cannot create location.")

    return crud.create_location(db=db, loc=location)


# --- NPC Endpoints ---

@app.post("/v1/npcs/spawn", response_model=schemas.NpcInstance, status_code=201)
def spawn_new_npc(npc: schemas.NpcSpawnRequest, db: Session = Depends(get_db)):
    """
    Used by the story_engine to create a new NPC in the world
    during an encounter.
    """
    return crud.spawn_npc(db=db, npc=npc)

@app.get("/v1/npcs/{npc_id}", response_model=schemas.NpcInstance)
def read_npc(npc_id: int, db: Session = Depends(get_db)):
    """Get the current status of a single NPC."""
    db_npc = crud.get_npc(db, npc_id=npc_id)
    if db_npc is None:
        raise HTTPException(status_code=404, detail="NPC not found")
    return db_npc

@app.put("/v1/npcs/{npc_id}", response_model=schemas.NpcInstance)
def update_existing_npc(
    npc_id: int,
    updates: schemas.NpcUpdate,
    db: Session = Depends(get_db)
):
    """
    Used to update an NPC (deal damage, move them, etc.)
    """
    db_npc = crud.update_npc(db, npc_id, updates)
    if db_npc is None:
        raise HTTPException(status_code=404, detail="NPC not found")
    return db_npc

@app.delete("/v1/npcs/{npc_id}", response_model=Dict[str, bool])
def delete_existing_npc(npc_id: int, db: Session = Depends(get_db)):
    """Used to remove a dead NPC from the world."""
    if not crud.delete_npc(db, npc_id):
        raise HTTPException(status_code=404, detail="NPC not found")
    return {"success": True}

# --- Item Endpoints ---

@app.post("/v1/items/spawn", response_model=schemas.ItemInstance, status_code=201)
def spawn_new_item(item: schemas.ItemSpawnRequest, db: Session = Depends(get_db)):
    """
    Used to create a new item (loot, quest item, etc.)
    """
    return crud.spawn_item(db=db, item=item)

@app.delete("/v1/items/{item_id}", response_model=Dict[str, bool])
def delete_existing_item(item_id: int, db: Session = Depends(get_db)):
    """
    Used when a player picks up an item from the ground.
    """
    if not crud.delete_item(db, item_id):
        raise HTTPException(status_code=44, detail="Item not found")
    return {"success": True}

# --- Region/Faction Endpoints (for setup) ---

@app.post("/v1/regions/", response_model=schemas.Region, status_code=201)
def create_new_region(region: schemas.RegionCreate, db: Session = Depends(get_db)):
    """Used to set up a new region in the world."""
    return crud.create_region(db, region)

@app.get("/v1/regions/{region_id}", response_model=schemas.Region)
def read_region(region_id: int, db: Session = Depends(get_db)):
    """Get high-level data about a region (weather, factions)."""
    db_region = crud.get_region(db, region_id)
    if db_region is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return db_region

@app.post("/v1/factions/", response_model=schemas.Faction, status_code=201)
def create_new_faction(faction: schemas.FactionCreate, db: Session = Depends(get_db)):
    """Used to set up a new faction in the world."""
    return crud.create_faction(db, faction)

@app.get("/v1/factions/{faction_id}", response_model=schemas.Faction)
def read_faction(faction_id: int, db: Session = Depends(get_db)):
    """Get high-level data about a faction."""
    db_faction = crud.get_faction(db, faction_id)
    if db_faction is None:
        raise HTTPException(status_code=404, detail="Faction not found")
    return db_faction

# --- Trap Endpoints ---

@app.post("/v1/traps/spawn", response_model=schemas.TrapInstance, status_code=201)
def spawn_new_trap(trap: schemas.TrapInstanceCreate, db: Session = Depends(get_db)):
    """Used by the story_engine to create a new trap in the world."""
    return crud.create_trap(db=db, trap=trap)

@app.put("/v1/traps/{trap_id}", response_model=schemas.TrapInstance)
def update_existing_trap(
    trap_id: int,
    updates: schemas.TrapUpdate,
    db: Session = Depends(get_db)
):
    """Used to update a trap (disarm, trigger, etc.)"""
    db_trap = crud.update_trap_status(db, trap_id, updates.status)
    if db_trap is None:
        raise HTTPException(status_code=404, detail="Trap not found")
    return db_trap

@app.get("/v1/locations/{loc_id}/traps", response_model=List[schemas.TrapInstance])
def read_traps_for_location(loc_id: int, db: Session = Depends(get_db)):
    """Get all traps for a single location by its ID."""
    return crud.get_traps_for_location(db, location_id=loc_id)
