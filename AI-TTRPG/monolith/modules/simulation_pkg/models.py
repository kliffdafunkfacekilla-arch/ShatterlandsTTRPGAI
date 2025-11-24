from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Faction(Base):
    """
    Tracks factions like 'The Silver Hand'.
    This is high-level data for the AI DM.
    """
    __tablename__ = "factions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    goals = Column(String, nullable=True) # e.g., "Expand territory"
    strength = Column(Integer, default=100) # Replaces 'resources' in older model
    relationship_matrix = Column(JSON, default={}) # e.g., {"faction_id_2": "war"} - Replaces 'disposition'

    # Reverse relationship for resources owned by this faction
    owned_resources = relationship("WorldResource", back_populates="owner_faction")

class WorldResource(Base):
    """
    Represents a strategic resource in the world (e.g., 'Iron Mine').
    """
    __tablename__ = "world_resources"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, index=True) # e.g., "Iron Mine", "Manor"
    owner_faction_id = Column(Integer, ForeignKey("factions.id"), nullable=True)
    abundance_level = Column(Integer, default=50) # 0-100 scale

    owner_faction = relationship("Faction", back_populates="owned_resources")

class WorldState(Base):
    """
    Holds global simulation variables.
    There should typically be only one row in this table.
    """
    __tablename__ = "world_state"

    id = Column(Integer, primary_key=True, index=True)
    current_tension = Column(Integer, default=0) # 0-100
    turn_count = Column(Integer, default=0)
