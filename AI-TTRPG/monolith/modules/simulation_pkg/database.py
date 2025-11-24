# AI-TTRPG/monolith/modules/simulation_pkg/database.py
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use an absolute path for the SQLite DB file so behavior is consistent.
# Path(__file__).resolve() is this file: .../monolith/modules/simulation_pkg/database.py
# .parents[0] = simulation_pkg
# .parents[1] = modules
# .parents[2] = monolith
# .parents[3] = AI-TTRPG (where simulation.db will be)
BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "simulation.db"

# Ensure the parent directory exists (though it should be the root)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

# The connect_args is recommended for SQLite with FastAPI to allow multithreading.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# This SessionLocal is what our API endpoints will use
# to get a connection to the database.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the class our database models will inherit from.
Base = declarative_base()
