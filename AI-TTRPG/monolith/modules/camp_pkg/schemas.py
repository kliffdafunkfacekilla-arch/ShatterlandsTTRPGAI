"""
Schemas for the camp system.
"""
from pydantic import BaseModel

class CampRestRequest(BaseModel):
    char_id: str
    duration: int
