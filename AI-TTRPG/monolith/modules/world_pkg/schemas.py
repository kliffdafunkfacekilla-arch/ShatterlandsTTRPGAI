from pydantic import BaseModel
from typing import Dict, List, Any, Optional

# --- NEW: World Map and Tile Schemas ---
class TileBase(BaseModel):
    x: int
    y: int
    z: int = 0
    terrain: Optional[str] = None
    features: Optional[Dict[str, Any]] = {}
    nested_map_id: Optional[int] = None

class Tile(TileBase):
    id: int
    map_id: int
    class Config:
        from_attributes = True

class MapBase(BaseModel):
    name: str
    parent_map_id: Optional[int] = None
    grid_width: int = 100
    grid_height: int = 100
    layers: int = 1
    description: Optional[str] = None

class Map(MapBase):
    id: int
    tiles: List[Tile] = []
    parent_map: Optional['Map'] = None
    class Config:
        from_attributes = True

# Pydantic models are used to validate data.
# 'BaseModel' is the class they inherit from.

class TrapInstanceBase(BaseModel):
    template_id: str
    location_id: int
    coordinates: Optional[Any] = None
    status: str = "armed"

class TrapInstance(TrapInstanceBase):
    id: int
    class Config:
        from_attributes = True # or orm_mode = True

class TrapInstanceCreate(TrapInstanceBase):
    pass

class TrapUpdate(BaseModel):
    status: Optional[str] = None

# --- Base Models ---
# These models define how data should be READ from the database.
# 'orm_mode = True' tells Pydantic to read data from
# SQLAlchemy database objects.

class FactionBase(BaseModel):
    name: str
    status: str
    disposition: Dict[str, Any]
    resources: int

class Faction(FactionBase):
    id: int
    class Config:
        from_attributes = True

class RegionBase(BaseModel):
    name: str
    current_weather: Optional[str] = "clear"
    environmental_effects: Optional[List[str]] = []
    faction_influence: Optional[Dict[str, Any]] = {}

class Region(RegionBase):
    id: int
    class Config:
        from_attributes = True

class ItemInstanceBase(BaseModel):
    template_id: str
    quantity: int
    location_id: Optional[int] = None
    npc_id: Optional[int] = None
    # --- ADD THIS LINE ---
    coordinates: Optional[Any] = None # Expecting [x, y]

class ItemInstance(ItemInstanceBase):
    id: int
    class Config:
        from_attributes = True

class NpcInstanceBase(BaseModel):
    template_id: str
    name_override: Optional[str] = None
    current_hp: int
    max_hp: int
    temp_hp: int = 0
    max_composure: int = 10
    current_composure: int = 10
    resource_pools: Dict[str, Any] = {}
    abilities: List[str] = []
    status_effects: List[str]
    location_id: int
    # --- ADD THIS LINE ---
    coordinates: Optional[Any] = None # Expecting [x, y]

class NpcInstance(NpcInstanceBase):
    id: int
    # This automatically includes the list of items
    # from the database relationship
    item_instances: List[ItemInstance] = []
    behavior_tags: List[str] = [] # Add this
    class Config:
        from_attributes = True

class LocationBase(BaseModel):
    name: str
    tags: List[str]
    exits: Dict[str, Any]
    generated_map_data: Optional[Any] = None # Can be any JSON
    map_seed: Optional[str] = None
    spawn_points: Optional[Dict[str, Any]] = None # <-- ADD THIS
    region_id: int

class Location(LocationBase):
    id: int
    # These automatically include the related data
    region: Region
    npc_instances: List[NpcInstance] = []
    item_instances: List[ItemInstance] = []
    trap_instances: List[TrapInstance] = [] # Add this
    ai_annotations: Optional[Dict[str, Any]] = None # Add this

    class Config:
        from_attributes = True

# --- API Request/Create Models ---
# These models define the data we expect to RECEIVE
# when creating or updating things.

class FactionCreate(FactionBase):
    pass # Inherits all fields from FactionBase

class RegionCreate(BaseModel):
    name: str

class LocationCreate(BaseModel):
    name: str
    region_id: int
    tags: List[str] = []
    exits: Dict[str, Any] = {}

class NpcSpawnRequest(BaseModel):
    template_id: str
    location_id: int
    name_override: Optional[str] = None
    # We make these optional. If not provided,
    # the story_engine should get them from the rules.
    current_hp: Optional[int] = None
    max_hp: Optional[int] = None

    # --- ADD THESE NEW OPTIONAL FIELDS ---
    temp_hp: Optional[int] = 0
    max_composure: Optional[int] = 10
    current_composure: Optional[int] = 10
    resource_pools: Optional[Dict[str, Any]] = {}
    abilities: Optional[List[str]] = []
    # --- END NEW OPTIONAL FIELDS ---

    behavior_tags: List[str] = []
    # --- ADD THIS LINE ---
    coordinates: Optional[Any] = None # Expecting [x, y]

class LocationAnnotationUpdate(BaseModel):
    ai_annotations: Dict[str, Any]

class NpcUpdate(BaseModel):
    # All fields are optional. We only update what is provided.
    current_hp: Optional[int] = None

    # --- ADD THESE NEW OPTIONAL FIELDS ---
    temp_hp: Optional[int] = None
    current_composure: Optional[int] = None
    resource_pools: Optional[Dict[str, Any]] = None
    abilities: Optional[List[str]] = None
    # --- END NEW OPTIONAL FIELDS ---

    status_effects: Optional[List[str]] = None
    location_id: Optional[int] = None
    # --- ADD THIS LINE ---
    coordinates: Optional[Any] = None # To allow moving NPCs

class ItemSpawnRequest(ItemInstanceBase):
    pass # Inherits all fields

class LocationMapUpdate(BaseModel):
    # This is for saving the procedurally generated map
    generated_map_data: Any # The tile map array
    map_seed: str
    spawn_points: Optional[Dict[str, Any]] = None # <-- ADD THIS
