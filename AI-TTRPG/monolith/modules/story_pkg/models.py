from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Untitled Campaign")
    main_plot_summary = Column(Text, nullable=True)
    active_quests = relationship("ActiveQuest", back_populates="campaign")

class ActiveQuest(Base):
    __tablename__ = "active_quests"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    steps = Column(JSON, default=[])
    current_step = Column(Integer, default=1)
    status = Column(String, default="active", index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    campaign = relationship("Campaign", back_populates="active_quests")

class StoryFlag(Base):
    __tablename__ = "story_flags"
    id = Column(Integer, primary_key=True, index=True)
    flag_name = Column(String, unique=True, index=True)
    value = Column(String, nullable=True)

class CombatEncounter(Base):
    __tablename__ = "combat_encounters"
    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, index=True)
    status = Column(String, default="active", index=True)
    turn_order = Column(JSON, default=[])
    current_turn_index = Column(Integer, default=0)

    # --- BURT'S NEW COLUMNS ---
    active_zones = Column(JSON, default=[])      # For Fire Walls/Hazards
    pending_reaction = Column(JSON, nullable=True) # For Interrupts
    # --------------------------

    participants = relationship("CombatParticipant", back_populates="encounter", cascade="all, delete-orphan")

class CombatParticipant(Base):
    __tablename__ = "combat_participants"
    id = Column(Integer, primary_key=True, index=True)
    combat_id = Column(Integer, ForeignKey("combat_encounters.id"))
    encounter = relationship("CombatEncounter", back_populates="participants")
    actor_id = Column(String, index=True)
    actor_type = Column(String)
    initiative_roll = Column(Integer)

    # --- BURT'S NEW COLUMN ---
    ability_usage = Column(JSON, default={})     # For "Once per encounter" limits
    # -------------------------
