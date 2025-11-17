from sqlalchemy import Column, Integer, String, JSON
from .database import Base


class Character(Base):
    __tablename__ = "characters"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    kingdom = Column(String)

    current_location_id = Column(Integer, default=1)

    # --- NEW COLUMN ---
    portrait_id = Column(String, nullable=True) # e.g., "character_1"
    # --- END NEW COLUMN ---

    # These are the separate columns that match your migration and services.py
    level = Column(Integer)
    stats = Column(JSON)
    skills = Column(JSON)
    max_hp = Column(Integer)
    current_hp = Column(Integer)
    temp_hp = Column(Integer, default=0)
    max_composure = Column(Integer, default=10)
    current_composure = Column(Integer, default=10)
    resource_pools = Column(JSON)
    talents = Column(JSON)
    abilities = Column(JSON)
    inventory = Column(JSON)
    equipment = Column(JSON)
    status_effects = Column(JSON)
    injuries = Column(JSON)
    position_x = Column(Integer)
    position_y = Column(Integer)