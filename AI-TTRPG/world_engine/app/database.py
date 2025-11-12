import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use an absolute path for the SQLite DB file so behavior is consistent
# whether the package is imported from the monolith runner or run in-place.
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "world.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

# The connect_args is recommended for SQLite with FastAPI to allow multithreading.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# This SessionLocal is what our API endpoints will use
# to get a connection to the database.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the class our database models will inherit from.
Base = declarative_base()
