from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from ..world_pkg.database import Base

class Faction(Base):
    __tablename__ = "factions"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, nullable=True, index=True) # Added for campaign scoping
    name = Column(String, unique=True, index=True)
    goals = Column(String) # Description of what they want
    strength = Column(Integer, default=50) # 0-100
    relationship_matrix = Column(JSON, default={}) # {"faction_name": -10, ...}

    resources = relationship("WorldResource", back_populates="owner_faction")

class WorldResource(Base):
    __tablename__ = "world_resources"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String) # e.g., "Iron", "Magic", "Food"
    owner_faction_id = Column(Integer, ForeignKey("factions.id"))
    abundance_level = Column(Integer, default=50) # 0-100

    owner_faction = relationship("Faction", back_populates="resources")

class WorldState(Base):
    __tablename__ = "world_state"

    id = Column(Integer, primary_key=True, index=True)
    current_tension = Column(Integer, default=0) # 0-100
    turn_count = Column(Integer, default=0)
    recent_events = Column(JSON, default=[]) # List of strings
