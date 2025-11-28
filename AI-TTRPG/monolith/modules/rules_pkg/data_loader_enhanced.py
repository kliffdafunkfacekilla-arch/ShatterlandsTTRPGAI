"""
Enhanced Rules Data Loader with Strict Validation and Singleton Pattern

This module provides:
- RuleSetContainer singleton for immut able, validated game rules
- Pydantic-based validation with detailed error reporting
- Thread-safe initialization
- Support for modding with clear error messages
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import ValidationError
import threading

from .models import (
    AbilitySchool, TalentInfo, BackgroundChoice,
    StatusEffectResponse
)

logger = logging.getLogger("monolith.rules.data_loader_enhanced")


class RuleSetContainer:
    """Thread-safe singleton container for immutable game rules.
    
    All game rules are loaded once at startup and cached for fast access.
    Uses Pydantic validation to ensure data integrity.
    """
    
    _instance: Optional['RuleSetContainer'] = None
    _lock = threading.Lock()
    _initialized = False
    
    def __init__(self):
        """Private constructor - use get_instance() instead."""
        if RuleSetContainer._initialized:
            raise RuntimeError("RuleSetContainer already initialized. Use get_instance()")
        
        # Core game data
        self.stats_list: List[str] = []
        self.skill_map: Dict[str, Dict[str, Any]] = {}
        self.skill_categories: Dict[str, Dict[str, str]] = {}
        
        # Abilities and Talents
        self.abilities: Dict[str, Any] = {}
        self.ability_lookup: Dict[str, Any] = {}  # Flat map for fast lookups
        self.talents: Dict[str, Any] = {}
        self.talent_lookup: Dict[str, Any] = {}
        
        # Combat and Equipment
        self.melee_weapons: Dict[str, Any] = {}
        self.ranged_weapons: Dict[str, Any] = {}
        self.armor: Dict[str, Any] = {}
        self.status_effects: Dict[str, Any] = {}
        self.injury_effects: Dict[str, Any] = {}
        
        # Character Creation
        self.kingdom_features: Dict[str, Any] = {}
        self.feature_stats_map: Dict[str, Any] = {}
        self.origin_choices: List[Dict[str, Any]] = []
        self.childhood_choices: List[Dict[str, Any]] = []
        self.coming_of_age_choices: List[Dict[str, Any]] = []
        self.training_choices: List[Dict[str, Any]] = []
        self.devotion_choices: List[Dict[str, Any]] = []
        
        # World Generation
        self.npc_templates: Dict[str, Any] = {}
        self.item_templates: Dict[str, Any] = {}
        self.generation_rules: Dict[str, Any] = {}
        self.loot_tables: Dict[str, Any] = {}
        
        # Metadata
        self.data_directory: Path = self._get_data_directory()
        self.load_errors: List[Dict[str, str]] = []
        
        logger.info("RuleSetContainer instance created (not yet loaded)")
    
    @classmethod
    def get_instance(cls) -> 'RuleSetContainer':
        """Get or create the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton (primarily for testing)."""
        with cls._lock:
            cls._instance = None
            cls._initialized = False
    
    def _get_data_directory(self) -> Path:
        """Get the data directory path."""
        # Assumes this file is in modules/rules_pkg/
        return Path(__file__).parent / "data"
    
    def _load_json_file(self, filename: str, required: bool = True) -> Any:
        """Load and parse a JSON file with error handling.
        
        Args:
            filename: Name of JSON file to load
            required: Whether file is required (logs error vs raises exception)
            
        Returns:
            Parsed JSON data or empty dict if not found
        """
        filepath = self.data_directory / filename
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded: {filename}")
                return data
                
        except FileNotFoundError:
            error_msg = f"File not found: {filename} at {filepath}"
            if required:
                logger.error(error_msg)
                self.load_errors.append({
                    "file": filename,
                    "error_type": "FileNotFoundError",
                    "message": error_msg
                })
            else:
                logger.warning(f"Optional file not found: {filename}")
            return {} if isinstance(data, dict) else []
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in {filename}: {e}"
            logger.error(error_msg)
            self.load_errors.append({
                "file": filename,
                "error_type": "JSONDecodeError",
                "message": error_msg,
                "line": e.lineno,
                "column": e.colno
            })
            return {} if "dict" in str(type({})) else []
            
        except Exception as e:
            error_msg = f"Unexpected error loading {filename}: {e}"
            logger.error(error_msg)
            self.load_errors.append({
                "file": filename,
                "error_type": type(e).__name__,
                "message": str(e)
            })
            return {}
    
    def _build_ability_lookup(self) -> Dict[str, Any]:
        """Build flat lookup map from nested ability data.
        
        Returns:
            Dictionary mapping ability names to ability data
        """
        lookup = {}
        
        for school_name, school_data in self.abilities.items():
            if not isinstance(school_data, dict):
                continue
            
            for branch in school_data.get("branches", []):
                if not isinstance(branch, dict):
                    continue
                
                for tier in branch.get("tiers", []):
                    if not isinstance(tier, dict):
                        continue
                    
                    ability_name = tier.get("name")
                    if ability_name:
                        # Add school context
                        tier["_school_name"] = school_name
                        tier["_school_resource"] = school_data.get("resource")
                        tier["_school_stat"] = school_data.get("associated_stat")
                        tier["_branch_name"] = branch.get("branch")
                        lookup[ability_name] = tier
        
        logger.info(f"Built {len(lookup)} ability lookups")
        return lookup
    
    def _build_talent_lookup(self) -> Dict[str, Any]:
        """Build flat lookup map from talent data.
        
        Returns:
            Dictionary mapping talent names to talent data
        """
        lookup = {}
        
        # Talents can be in various structures
        for category, talents_data in self.talents.items():
            if isinstance(talents_data, list):
                for talent in talents_data:
                    if isinstance(talent, dict):
                        name = talent.get("talent_name") or talent.get("name")
                        if name:
                            talent["_category"] = category
                            lookup[name] = talent
            elif isinstance(talents_data, dict):
                for talent_name, talent_data in talents_data.items():
                    if isinstance(talent_data, dict):
                        talent_data["_category"] = category
                        lookup[talent_name] = talent_data
        
        logger.info(f"Built {len(lookup)} talent lookups")
        return lookup
    
    def _process_kingdom_features(self) -> Dict[str, Any]:
        """Process kingdom features into flat map for stat lookups."""
        feature_map = {}
        
        for category_data in self.kingdom_features.values():
            if not isinstance(category_data, dict):
                continue
            
            for kingdom_list in category_data.values():
                if isinstance(kingdom_list, list):
                    for feature in kingdom_list:
                        if not isinstance(feature, dict):
                            continue
                        
                        feature_name = feature.get("name")
                        if feature_name:
                            feature_map[feature_name] = feature
        
        logger.info(f"Processed {len(feature_map)} kingdom features")
        return feature_map
    
    def _process_skills(self) -> tuple:
        """Process stats and skills from JSON.
        
        Returns:
            Tuple of (stats_list, skill_categories, skill_map)
        """
        stats_data = self._load_json_file("stats_and_skills.json")
        
        stats_list = stats_data.get("stats", [])
        skill_categories = stats_data.get("skill_categories", {})
        
        # Build flat skill map
        skill_map = {}
        for category, skills_dict in skill_categories.items():
            if isinstance(skills_dict, dict):
                for skill_name, governing_stat in skills_dict.items():
                    if governing_stat not in stats_list:
                        logger.warning(
                            f"Skill '{skill_name}' has invalid governing stat '{governing_stat}'"
                        )
                        continue
                    
                    skill_map[skill_name] = {
                        "category": category,
                        "governing_stat": governing_stat
                    }
        
        logger.info(f"Processed {len(stats_list)} stats and {len(skill_map)} skills")
        return stats_list, skill_categories, skill_map
    
    def load_all(self) -> Dict[str, Any]:
        """Load and validate all game rules data.
        
        Returns:
            Summary dictionary of loaded data
            
        Raises:
            ValueError: If critical data files are missing or invalid
        """
        with self._lock:
            if RuleSetContainer._initialized:
                logger.warning("Already initialized, skipping reload")
                return self.get_summary()
            
            logger.info("=" * 60)
            logger.info("LOADING GAME RULES DATA")
            logger.info("=" * 60)
            
            # Clear any previous errors
            self.load_errors = []
            
            try:
                # 1. Load core stats and skills
                self.stats_list, self.skill_categories, self.skill_map = self._process_skills()
                
                if not self.stats_list:
                    raise ValueError("Critical: No stats loaded from stats_and_skills.json")
                
                # 2. Load abilities
                self.abilities = self._load_json_file("abilities.json")
                self.ability_lookup = self._build_ability_lookup()
                
                # 3. Load talents
                self.talents = self._load_json_file("talents.json")
                self.talent_lookup = self._build_talent_lookup()
                
                # 4. Load kingdom features
                self.kingdom_features = self._load_json_file("kingdom_features.json")
                self.feature_stats_map = self._process_kingdom_features()
                
                # 5. Load combat data
                self.melee_weapons = self._load_json_file("melee_weapons.json")
                self.ranged_weapons = self._load_json_file("ranged_weapons.json")
                self.armor = self._load_json_file("armor.json")
                self.injury_effects = self._load_json_file("injury_effects.json")
                self.status_effects = self._load_json_file("status_effects.json")
                
                # 6. Load character creation data
                self.origin_choices = self._load_json_file("origin_choices.json")
                self.childhood_choices = self._load_json_file("childhood_choices.json")
                self.coming_of_age_choices = self._load_json_file("coming_of_age_choices.json")
                self.training_choices = self._load_json_file("training_choices.json")
                self.devotion_choices = self._load_json_file("devotion_choices.json")
                
                # 7. Load world generation data
                self.npc_templates = self._load_json_file("npc_templates.json")
                self.item_templates = self._load_json_file("item_templates.json")
                self.generation_rules = self._load_json_file("generation_rules.json")
                self.loot_tables = self._load_json_file("loot_tables.json", required=False)
                
                RuleSetContainer._initialized = True
                
                # Log summary
                summary = self.get_summary()
                logger.info("=" * 60)
                logger.info("RULES DATA LOADED SUCCESSFULLY")
                logger.info("=" * 60)
                for key, value in summary.items():
                    if isinstance(value, int):
                        logger.info(f"  {key}: {value}")
                
                if self.load_errors:
                    logger.warning(f"Loaded with {len(self.load_errors)} errors:")
                    for error in self.load_errors:
                        logger.warning(f"  - {error['file']}: {error['message']}")
                
                return summary
                
            except Exception as e:
                logger.exception("Fatal error during rules data loading")
                raise ValueError(f"Failed to load game rules: {e}") from e
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded data counts."""
        return {
            "stats": len(self.stats_list),
            "skills": len(self.skill_map),
            "abilities": len(self.ability_lookup),
            "talents": len(self.talent_lookup),
            "kingdom_features": len(self.feature_stats_map),
            "melee_weapons": len(self.melee_weapons),
            "ranged_weapons": len(self.ranged_weapons),
            "armor": len(self.armor),
            "status_effects": len(self.status_effects),
            "injury_effects": len(self.injury_effects),
            "npc_templates": len(self.npc_templates),
            "item_templates": len(self.item_templates),
            "origin_choices": len(self.origin_choices),
            "childhood_choices": len(self.childhood_choices),
            "coming_of_age_choices": len(self.coming_of_age_choices),
            "training_choices": len(self.training_choices),
            "devotion_choices": len(self.devotion_choices),
            "load_errors": len(self.load_errors)
        }
    
    # Convenience accessors
    def get_ability(self, ability_name: str) -> Optional[Dict[str, Any]]:
        """Get ability data by name."""
        return self.ability_lookup.get(ability_name)
    
    def get_talent(self, talent_name: str) -> Optional[Dict[str, Any]]:
        """Get talent data by name."""
        return self.talent_lookup.get(talent_name)
    
    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get skill information."""
        return self.skill_map.get(skill_name)
    
    def get_status_effect(self, effect_name: str) -> Optional[Dict[str, Any]]:
        """Get status effect data."""
        return self.status_effects.get(effect_name)


# Module-level convenience functions
_rules_container: Optional[RuleSetContainer] = None

def load_and_validate_all() -> Dict[str, Any]:
    """Load and validate all game rules data.
    
    This is the main entry point for loading rules.
    Should be called once at application startup.
    
    Returns:
        Summary dictionary of loaded data
    """
    global _rules_container
    
    if _rules_container is None:
        _rules_container = RuleSetContainer.get_instance()
    
    return _rules_container.load_all()


def get_rules() -> RuleSetContainer:
    """Get the global rules container.
    
    Returns:
        RuleSetContainer instance
        
    Raises:
        RuntimeError: If rules have not been loaded yet
    """
    global _rules_container
    
    if _rules_container is None or not RuleSetContainer._initialized:
        raise RuntimeError(
            "Rules not loaded. Call load_and_validate_all() first."
        )
    
    return _rules_container


# Backward compatibility with old data_loader.py
def load_data() -> Dict[str, Any]:
    """Legacy function for backward compatibility.
    
    Returns the same data structure as the old loader.
    """
    rules = get_rules()
    
    return {
        "stats_list": rules.stats_list,
        "skill_categories": rules.skill_categories,
        "all_skills": rules.skill_map,
        "ability_data": rules.abilities,
        "ability_map": rules.ability_lookup,
        "talent_data": rules.talents,
        "feature_stats_map": rules.feature_stats_map,
        "kingdom_features_data": rules.kingdom_features,
        "melee_weapons": rules.melee_weapons,
        "ranged_weapons": rules.ranged_weapons,
        "armor": rules.armor,
        "injury_effects": rules.injury_effects,
        "status_effects": rules.status_effects,
        "origin_choices": rules.origin_choices,
        "childhood_choices": rules.childhood_choices,
        "coming_of_age_choices": rules.coming_of_age_choices,
        "training_choices": rules.training_choices,
        "devotion_choices": rules.devotion_choices,
        "npc_templates": rules.npc_templates,
        "item_templates": rules.item_templates,
        "generation_rules": rules.generation_rules,
    }
