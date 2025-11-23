import logging
from fastapi import FastAPI, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from monolith.modules.auth_pkg.dependencies import get_current_user
from monolith.modules import map as map_module
from monolith.modules import story as story_module
from monolith.modules import character as character_module
from monolith.start_monolith import _main as start_monolith_background

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monolith.api")

app = FastAPI(title="Shatterlands Monolith API", version="1.0.0")

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    """
    Start the orchestrator and background services when the API starts.
    """
    # We can reuse the logic from start_monolith, but we need to be careful 
    # not to block the event loop if it has a while True loop.
    # For now, we'll assume the orchestrator needs to be initialized.
    from monolith.orchestrator import get_orchestrator
    from monolith.modules import register_all
    
    orch = get_orchestrator()
    register_all(orch)
    await orch.start()
    logger.info("Monolith Orchestrator started via FastAPI.")

# --- Pydantic Models for API ---
class MapGenerationRequest(BaseModel):
    tags: List[str]
    seed: Optional[str] = None

class StoryEventRequest(BaseModel):
    # Placeholder for generic story requests if needed
    pass

# --- Secured Routes ---

@app.post("/map/generate", tags=["Map"])
async def generate_map_endpoint(
    request: MapGenerationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generates a map based on tags. Requires Authentication.
    """
    logger.info(f"Map generation requested by user: {current_user.get('sub')}")
    try:
        # Call the synchronous map module
        result = map_module.generate_map(request.tags, request.seed)
        return result
    except Exception as e:
        logger.error(f"Map generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/story/start-combat", tags=["Story"])
async def start_combat_endpoint(
    request: Dict[str, Any], # Using Dict for now, should import schema
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Starts a combat encounter. Requires Authentication.
    """
    from monolith.modules.story_pkg import schemas as se_schemas
    try:
        # Validate request using the schema from story_pkg
        combat_req = se_schemas.CombatStartRequest(**request)
        result = story_module.start_combat(combat_req)
        return result
    except Exception as e:
        logger.error(f"Start combat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Include Existing Routers ---
# Character module already has a router, we should secure it too if possible, 
# or it might handle its own security (currently it doesn't seem to).
# For now, we'll include it as is, but ideally we'd wrap it or add dependencies.
app.include_router(
    character_module.router, 
    dependencies=[Depends(get_current_user)] # Apply auth to all character routes
)

from monolith.modules.map_pkg import data_loader as map_loader
from monolith.modules.rules_pkg import data_loader as rules_loader

# --- Admin Routes ---

@app.post("/admin/reload-rules", tags=["Admin"])
async def reload_rules_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Hot-reloads static game data (rules, items, map configs) from disk.
    Requires Authentication.
    """
    logger.warning(f"Hot-reload triggered by user: {current_user.get('sub')}")
    try:
        # Reload Map Data
        map_loader.load_data()
        
        # Reload Rules Data
        rules_loader.load_all_data()
        
        return {"status": "success", "message": "Game rules and map data reloaded successfully."}
    except Exception as e:
        logger.error(f"Hot-reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "monolith-api"}
