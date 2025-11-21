# AI-TTRPG/monolith/modules/character_pkg/models.py
from sqlalchemy import Column, Integer, String, JSON
from .database import Base

class Character(Base):
    __tablename__ = "characters"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    kingdom = Column(String)

    current_location_id = Column(Integer, default=1)
    portrait_id = Column(String, nullable=True)

    level = Column(Integer)
    stats = Column(JSON)
    skills = Column(JSON)
    max_hp = Column(Integer)
    current_hp = Column(Integer)

    # --- ADD THIS COLUMN ---
    temp_hp = Column(Integer, default=0)
    xp = Column(Integer, default=0)
    available_ap = Column(Integer, default=3)  # <--- NEW: Ability Points
    is_dead = Column(Integer, default=0) # 0=False, 1=True (SQLite doesn't have native Bool)
    # --- END ADD ---

    max_composure = Column(Integer)
    current_composure = Column(Integer)
    resource_pools = Column(JSON)

    unlocked_abilities = Column(JSON)  # <--- NEW: List of strings ["Force_Offense_T1", ...]
    active_techniques = Column(JSON)   # List of active technique IDs

    talents = Column(JSON)
    abilities = Column(JSON)
    inventory = Column(JSON)
    equipment = Column(JSON)
    status_effects = Column(JSON)
    injuries = Column(JSON)
    position_x = Column(Integer)
    position_y = Column(Integer)
