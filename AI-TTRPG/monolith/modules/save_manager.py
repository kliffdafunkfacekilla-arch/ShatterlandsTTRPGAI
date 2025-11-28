"""
JSON-based Save Manager for Local Monolith Architecture

This module handles all game state persistence using JSON files and Pydantic validation.
Replaces the previous SQLAlchemy/database-based approach with direct file I/O.

Responsibilities:
- Save GameSaveState to JSON files
- Load and validate JSON save files
- Scan save directory for available saves
- Load character JSON files from external sources
"""
import logging
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import ValidationError

from .save_schemas import SaveFile, SaveGameData, CharacterSave

logger = logging.getLogger("monolith.save_manager")

# Save directory configuration
SAVE_DIR = Path("./saves")
CHARACTER_DIR = Path("./characters")
SAVE_DIR.mkdir(exist_ok=True)
CHARACTER_DIR.mkdir(exist_ok=True)


def _get_save_path(slot_name: str) -> Path:
    """Generate a clean file path for the save slot.
    
    Args:
        slot_name: Name of the save slot
        
    Returns:
        Path object for the save file
    """
    # Sanitize filename
    filename = "".join(c for c in slot_name if c.isalnum() or c in ('_', '-', ' '))
    filename = f"{filename}.json"
    return SAVE_DIR / filename


def save_game(
    data: SaveGameData,
    slot_name: str = "CurrentSave",
    active_character_id: Optional[str] = None,
    active_character_name: Optional[str] = None
) -> Dict[str, Any]:
    """Save game state to JSON file.
    
    Args:
        data: Complete game state data (Pydantic model)
        slot_name: Name of the save slot
        active_character_id: ID of the currently active character
        active_character_name: Name of the currently active character
        
    Returns:
        Result dictionary with success status and metadata
    """
    try:
        logger.info(f"Starting save game to slot: {slot_name}")
        
        # Auto-detect active character if not provided
        if not active_character_id and data.characters:
            active_character_id = data.characters[0].id
            active_character_name = data.characters[0].name
            logger.info(f"Auto-detected active character: {active_character_name}")
        
        # Create save file structure
        save_file = SaveFile(
            save_name=slot_name,
            save_time=datetime.now().isoformat(),
            active_character_id=active_character_id,
            active_character_name=active_character_name,
            data=data
        )
        
        # Serialize to JSON
        filepath = _get_save_path(slot_name)
        json_data = save_file.model_dump_json(indent=2)
        
        # Write to file
        filepath.write_text(json_data, encoding='utf-8')
        
        logger.info(f"Save complete: {filepath}")
        return {
            "success": True,
            "path": str(filepath),
            "name": active_character_name or "Unknown",
            "timestamp": save_file.save_time
        }
        
    except Exception as e:
        logger.exception(f"Save game failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def load_game(slot_name: str) -> Dict[str, Any]:
    """Load game state from JSON file with Pydantic validation.
    
    Args:
        slot_name: Name of the save slot to load
        
    Returns:
        Result dictionary with SaveFile data or error
    """
    filepath = _get_save_path(slot_name)
    
    try:
        logger.info(f"Loading game from: {filepath}")
        
        if not filepath.exists():
            raise FileNotFoundError(f"Save file not found: {filepath}")
        
        # Read and parse JSON
        json_content = filepath.read_text(encoding='utf-8')
        
        # Validate with Pydantic
        save_file = SaveFile.model_validate_json(json_content)
        
        logger.info(f"Load complete: {save_file.save_name}")
        return {
            "success": True,
            "save_file": save_file,
            "name": save_file.save_name,
            "active_character_name": save_file.active_character_name,
            "timestamp": save_file.save_time
        }
        
    except FileNotFoundError as e:
        logger.error(f"Save file not found: {e}")
        return {
            "success": False,
            "error": f"Save file '{slot_name}' not found"
        }
    except ValidationError as e:
        logger.exception(f"Save file validation failed: {e}")
        return {
            "success": False,
            "error": f"Save file corrupted or incompatible: {e}"
        }
    except Exception as e:
        logger.exception(f"Load game failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def scan_saves() -> List[Dict[str, Any]]:
    """Scan the saves directory for all available save files.
    
    Returns:
        List of save file metadata dictionaries
    """
    saves = []
    
    try:
        for save_file in SAVE_DIR.glob("*.json"):
            try:
                # Read minimal metadata without full validation
                json_content = save_file.read_text(encoding='utf-8')
                data = json.loads(json_content)
                
                saves.append({
                    "name": data.get("save_name", save_file.stem),
                    "path": str(save_file),
                    "timestamp": data.get("save_time", "Unknown"),
                    "active_character": data.get("active_character_name", "Unknown")
                })
            except Exception as e:
                logger.warning(f"Could not read save metadata from {save_file}: {e}")
                # Include corrupted files in list but mark them
                saves.append({
                    "name": save_file.stem,
                    "path": str(save_file),
                    "timestamp": "Unknown",
                    "active_character": "Corrupted",
                    "error": str(e)
                })
        
        logger.info(f"Found {len(saves)} save files")
        return saves
        
    except Exception as e:
        logger.exception(f"Error scanning save directory: {e}")
        return []


def load_character_from_json(filepath: str) -> Dict[str, Any]:
    """Load and validate an external character JSON file.
    
    This is used during character creation and game setup to import
    standalone character definitions.
    
    Args:
        filepath: Path to the character JSON file
        
    Returns:
        Result dictionary with CharacterSave data or error
    """
    try:
        logger.info(f"Loading character from: {filepath}")
        
        char_path = Path(filepath)
        if not char_path.exists():
            raise FileNotFoundError(f"Character file not found: {filepath}")
        
        # Read and validate
        json_content = char_path.read_text(encoding='utf-8')
        character = CharacterSave.model_validate_json(json_content)
        
        logger.info(f"Character loaded: {character.name}")
        return {
            "success": True,
            "character": character,
            "name": character.name,
            "id": character.id
        }
        
    except FileNotFoundError as e:
        logger.error(f"Character file not found: {e}")
        return {
            "success": False,
            "error": f"Character file not found: {filepath}"
        }
    except ValidationError as e:
        logger.exception(f"Character validation failed: {e}")
        # Provide detailed error for modding/debugging
        return {
            "success": False,
            "error": f"Character file validation failed:\n{e}",
            "validation_details": str(e)
        }
    except Exception as e:
        logger.exception(f"Load character failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def save_character_to_json(character: CharacterSave, filename: Optional[str] = None) -> Dict[str, Any]:
    """Save a character to a standalone JSON file.
    
    Used after character creation to export the character for later use.
    
    Args:
        character: CharacterSave Pydantic model
        filename: Optional custom filename (defaults to character name)
        
    Returns:
        Result dictionary with success status and path
    """
    try:
        if not filename:
            filename = f"{character.name}.json"
        
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', ' '))
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = CHARACTER_DIR / filename
        
        logger.info(f"Saving character to: {filepath}")
        
        # Serialize and write
        json_data = character.model_dump_json(indent=2)
        filepath.write_text(json_data, encoding='utf-8')
        
        logger.info(f"Character saved: {character.name}")
        return {
            "success": True,
            "path": str(filepath),
            "name": character.name
        }
        
    except Exception as e:
        logger.exception(f"Save character failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def scan_characters() -> List[Dict[str, Any]]:
    """Scan the characters directory for available character files.
    
    Returns:
        List of character metadata dictionaries
    """
    characters = []
    
    try:
        for char_file in CHARACTER_DIR.glob("*.json"):
            try:
                # Read minimal metadata
                json_content = char_file.read_text(encoding='utf-8')
                data = json.loads(json_content)
                
                characters.append({
                    "name": data.get("name", char_file.stem),
                    "path": str(char_file),
                    "id": data.get("id", "unknown"),
                    "level": data.get("level", 1),
                    "kingdom": data.get("kingdom", "Unknown")
                })
            except Exception as e:
                logger.warning(f"Could not read character from {char_file}: {e}")
                characters.append({
                    "name": char_file.stem,
                    "path": str(char_file),
                    "error": str(e)
                })
        
        logger.info(f"Found {len(characters)} character files")
        return characters
        
    except Exception as e:
        logger.exception(f"Error scanning character directory: {e}")
        return []


def delete_save(slot_name: str) -> Dict[str, Any]:
    """Delete a save file.
    
    Args:
        slot_name: Name of the save slot to delete
        
    Returns:
        Result dictionary with success status
    """
    try:
        filepath = _get_save_path(slot_name)
        
        if not filepath.exists():
            return {
                "success": False,
                "error": f"Save file '{slot_name}' not found"
            }
        
        filepath.unlink()
        logger.info(f"Deleted save: {filepath}")
        
        return {
            "success": True,
            "message": f"Save '{slot_name}' deleted"
        }
        
    except Exception as e:
        logger.exception(f"Delete save failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
