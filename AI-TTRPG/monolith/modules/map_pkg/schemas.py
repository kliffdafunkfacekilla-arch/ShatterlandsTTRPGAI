from pydantic import BaseModel, Field
from typing import List, Tuple, Optional, Dict

class EntitySchema(BaseModel):
    """
    Represents a non-player object or NPC on the map.
    """
    entity_id: str = Field(..., description="Unique identifier for the entity")
    entity_type: str = Field(..., description="Type of entity (e.g., 'goblin', 'chest', 'door')")
    current_hp: Optional[int] = Field(None, description="Current health points if applicable")
    description: str = Field(..., description="Visual description for the AI and UI")
    # Add position here for easier entity tracking, though it's also on the tile
    position: Tuple[int, int] = Field(..., description="(x, y) coordinates")

class MapTile(BaseModel):
    """
    Represents a single tile on the game map.
    """
    coordinates: Tuple[int, int] = Field(..., description="(x, y) coordinates")
    terrain_type: str = Field(..., description="Type of terrain (e.g., 'floor', 'wall', 'water')")
    visibility: str = Field("fogged", description="Visibility state: 'fogged', 'visible', 'explored'")
    entities: List[EntitySchema] = Field(default_factory=list, description="List of entities present on this tile")
    
    # Visual metadata (optional, for client rendering)
    texture_id: Optional[str] = None

class MapState(BaseModel):
    """
    The complete state of the current map.
    """
    map_id: str = Field(..., description="Unique ID for this map instance")
    width: int
    height: int
    tiles: Dict[str, MapTile] = Field(..., description="Map tiles keyed by 'x,y' string for easy lookup")
    
    def get_tile(self, x: int, y: int) -> Optional[MapTile]:
        return self.tiles.get(f"{x},{y}")
