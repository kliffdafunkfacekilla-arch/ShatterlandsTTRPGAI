from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Float

# Import the 'Base' we created in database.py
from .database import Base

# --- NEW: World Map and Tile Models ---
class Map(Base):
    __tablename__ = "maps"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    parent_map_id = Column(Integer, ForeignKey("maps.id"), nullable=True)
    grid_width = Column(Integer, default=100)
    grid_height = Column(Integer, default=100)
    layers = Column(Integer, default=1)
    description = Column(Text, nullable=True)
    tiles = relationship("Tile", back_populates="map", foreign_keys="Tile.map_id")
    parent_map = relationship("Map", remote_side=[id])

class Tile(Base):
    __tablename__ = "tiles"
    id = Column(Integer, primary_key=True, index=True)
    map_id = Column(Integer, ForeignKey("maps.id"))
    x = Column(Integer)
    y = Column(Integer)
    z = Column(Integer, default=0) # Layer
    terrain = Column(String, nullable=True)
    features = Column(JSON, default={})
    nested_map_id = Column(Integer, ForeignKey("maps.id"), nullable=True) # Reference to nested map
    map = relationship("Map", back_populates="tiles", foreign_keys=[map_id])
    nested_map = relationship("Map", foreign_keys=[nested_map_id])

class TrapInstance(Base):
    __tablename__ = "trap_instances"
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(String, index=True) # e.g., "pit_trap_t1"
    location_id = Column(Integer, ForeignKey("locations.id"))
    coordinates = Column(JSON, nullable=True) # e.g., [x, y] or [[x1,y1],[x2,y2]]
    status = Column(String, default="armed", index=True) # armed, disarmed, triggered

    # Relationships
    location = relationship("Location", back_populates="trap_instances")

# Faction model moved to simulation_pkg/models.py to avoid duplication

class Region(Base):
    """
    Tracks large areas like 'The Dragon's Spine Mountains'.
    This provides environmental context (weather, etc.)
    """
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, nullable=True, index=True)  # Campaign scoping
    name = Column(String, unique=True, index=True)
    current_weather = Column(String, default="clear")
    environmental_effects = Column(JSON, default=[]) # e.g., ["blight_level_2"]
    faction_influence = Column(JSON, default={}) # e.g., {"faction_id_1": 0.75}
    
    # --- REACTIVE STORY ENGINE: World State Tracking ---
    kingdom_resource_level = Column(Integer, default=50)  # 0-100 scale

    # This links a Region to its many Locations
    locations = relationship("Location", back_populates="region")

class Location(Base):
    """
    A specific, traversable map like 'Whispering Forest - Clearing'.
    This is where the player 'is'.
    """
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, nullable=True, index=True)  # Campaign scoping
    name = Column(String, index=True)
    tags = Column(JSON, default=[]) # e.g., ["forest", "outside", "hostile"]
    exits = Column(JSON, default={}) # e.g., {"north": "location_id_2"}
    description = Column(Text, nullable=True) # Human-readable description of the location

    # This stores the tile map array (e.g., [[0,1,0],[0,1,0]])
    # It starts as NULL until procedurally generated.
    generated_map_data = Column(JSON, nullable=True)
    map_seed = Column(String, nullable=True)

    # This links this Location to its parent Region
    region_id = Column(Integer, ForeignKey("regions.id"))

    # These link the Location to all NPCs and Items currently in it
    region = relationship("Region", back_populates="locations")
    npc_instances = relationship("NpcInstance", back_populates="location")
    item_instances = relationship("ItemInstance", back_populates="location")
    trap_instances = relationship("TrapInstance", back_populates="location") # Add this line
    ai_annotations = Column(JSON, nullable=True) # Store descriptions, interactions flags etc.
    spawn_points = Column(JSON, nullable=True)
    flavor_context = Column(JSON, nullable=True) # Stores MapFlavorContext data
    
    # --- REACTIVE STORY ENGINE: Location State ---
    player_reputation = Column(Integer, default=0)  # -100 to +100 scale
    last_combat_outcome = Column(String, nullable=True)  # e.g., "CRITICAL_HIT", "DEFEAT"

class NpcInstance(Base):
    """
    An *instance* of an NPC (e.g., 'Goblin_1') that
    has been spawned on a map.
    """
    __tablename__ = "npc_instances"
    id = Column(Integer, primary_key=True, index=True)
    # The 'blueprint' ID (e.g., "goblin_raider")
    template_id = Column(String, index=True)
    name_override = Column(String, nullable=True) # e.g., "Grak the Goblin"
    current_hp = Column(Integer)
    max_hp = Column(Integer)
    temp_hp = Column(Integer, default=0)
    max_composure = Column(Integer, default=10)
    current_composure = Column(Integer, default=10)
    resource_pools = Column(JSON, default={})
    abilities = Column(JSON, default=[])
    status_effects = Column(JSON, default=[])

    # --- ADD THIS LINE ---
    injuries = Column(JSON, default=[]) # e.g., [{"location": "Torso", "severity": "Minor"}]
    # --- END ADD ---

    # This links the NPC to the Location it is currently in
    location_id = Column(Integer, ForeignKey("locations.id"))
    behavior_tags = Column(JSON, default=[]) # Store tags like ["aggressive"]


    # --- ADD THIS LINE ---
    coordinates = Column(JSON, nullable=True) # e.g., [10, 5]

    location = relationship("Location", back_populates="npc_instances")
    # This links the NPC to the Items it is carrying (its inventory)
    item_instances = relationship("ItemInstance", back_populates="npc")

class ItemInstance(Base):
    """
    An *instance* of an item (e.g., 'a small potion') that
    exists in the world.
    """
    __tablename__ = "item_instances"
    id = Column(Integer, primary_key=True, index=True)
    # The 'blueprint' ID (e.g., "potion_health_small")
    template_id = Column(String, index=True)
    quantity = Column(Integer, default=1)

    # An item can be on the ground (location_id is set)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    # OR it can be in an NPC's inventory (npc_id is set)
    npc_id = Column(Integer, ForeignKey("npc_instances.id"), nullable=True)


    # --- ADD THIS LINE ---
    coordinates = Column(JSON, nullable=True) # e.g., [12, 8]

    location = relationship("Location", back_populates="item_instances")
    npc = relationship("NpcInstance", back_populates="item_instances")

# --- NEW MODEL: Global Game/World State ---
class GameState(Base):
    """
    A single-row table to store global game state and reactive variables.
    """
    __tablename__ = 'game_state'
    id = Column(Integer, primary_key=True) # Used to guarantee a single row (id=1)
    
    # Persistent Metrics for Event Engine Evaluation
    player_reputation = Column(Integer, default=0, nullable=False)
    kingdom_resource_level = Column(Integer, default=100, nullable=False)
    
    # Storing structured AI context for later use (e.g., save/load)
    # Using JSON for schema-less data like the MapFlavorContext pydantic model.
    last_map_flavor_context = Column(JSON, nullable=True) 
    last_event_text = Column(String, nullable=True)