import os
import json
import logging
import hashlib
import google.generativeai as genai
from typing import List, Dict, Any, Optional

logger = logging.getLogger("monolith.ai_dm.llm")

# Helper for safe JSON parsing
def clean_json_response(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    return text

class LLMCache:
    """
    Simple in-memory cache for LLM responses to reduce latency and costs.
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _generate_key(self, tags: List[str]) -> str:
        """
        Generates a deterministic cache key based on sorted tags.
        """
        # Sort tags to ensure ["forest", "dark"] == ["dark", "forest"]
        sorted_tags = sorted([t.lower().strip() for t in tags])
        key_str = "|".join(sorted_tags)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, tags: List[str]) -> Optional[Dict[str, Any]]:
        """Retrieves cached context if available."""
        key = self._generate_key(tags)
        result = self._cache.get(key)
        if result:
            logger.info(f"Cache HIT for tags: {tags}")
        else:
            logger.info(f"Cache MISS for tags: {tags}")
        return result

    def set(self, tags: List[str], data: Dict[str, Any]) -> None:
        """Stores valid context in the cache."""
        key = self._generate_key(tags)
        self._cache[key] = data
        logger.debug(f"Cached result for tags: {tags}")


import requests

class OllamaClient:
    """Client for local Ollama instance."""
    def __init__(self, model="llama3", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        
    def generate_content(self, prompt: str, generation_config: Optional[Dict] = None) -> Any:
        """Mimics the Google GenAI generate_content interface."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            if generation_config and generation_config.get("response_mime_type") == "application/json":
                payload["format"] = "json"
                
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            text = result.get("response", "")
            
            # Return an object with a .text attribute to match GenAI
            class ResponseWrapper:
                def __init__(self, t): self.text = t
            return ResponseWrapper(text)
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise e

class LLMService:
    def __init__(self):
        self.model = None
        self.cache = LLMCache()
        self._setup_client()

    def _setup_client(self):
        # Check for Gemini Key first
        api_key = os.environ.get("GEMINI_API_KEY")
        
        # Check for Local Preference or Missing Key
        use_local = os.environ.get("USE_LOCAL_LLM", "false").lower() == "true"
        
        if use_local or not api_key:
            logger.info("Using Local LLM (Ollama)...")
            try:
                # Default to llama3:latest, but allow override
                model_name = os.environ.get("LOCAL_LLM_MODEL", "llama3:latest")
                self.model = OllamaClient(model=model_name)
                logger.info(f"Local AI Client initialized with model: {model_name}")
            except Exception as e:
                logger.error(f"Local AI Init failed: {e}")
        else:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini AI Client initialized.")
            except Exception as e:
                logger.error(f"Gemini AI Init failed: {e}")

    def generate_map_flavor(self, tags: List[str], lore_context: str = "") -> Dict[str, Any]:
        """
        Generates a batch of flavor text based on map tags.
        Returns a dictionary matching MapFlavorContext.
        Checks cache first.
        """
        # 1. Check Cache
        cached_result = self.cache.get(tags)
        if cached_result:
            return cached_result

        if not self.model:
            return self._get_fallback_flavor()

        try:
            # Lazy import to avoid circular dependency if any
            from monolith.modules.map_pkg.models import MapFlavorContext
        except ImportError:
            logger.error("Could not import MapFlavorContext")
            return self._get_fallback_flavor()

        tag_str = ", ".join(tags)
        prompt = f"""
        You are a Fantasy RPG Content Generator.
        I need a JSON object containing atmospheric descriptions and combat flavor text for a map with these tags: [{tag_str}].
        
        Lore Context:
        {lore_context}
        
        The output MUST be a valid JSON object that strictly adheres to this schema:
        {{
            "environment_description": "string",
            "visuals": ["string", "string", "string"],
            "sounds": ["string", "string", "string"],
            "smells": ["string", "string"],
            "combat_hits": ["string", "string", "string", "string", "string"],
            "combat_misses": ["string", "string", "string", "string", "string"],
            "spell_casts": ["string", "string", "string"],
            "enemy_intros": ["string", "string", "string"]
        }}
        
        Ensure the content is thematic and immersive, drawing from the provided Lore Context where applicable.
        """

        try:
            # Use generation_config to enforce JSON response if supported by the model version,
            # otherwise rely on the prompt and cleaning.
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            clean_text = clean_json_response(response.text)
            data = json.loads(clean_text)
            
            # Validate with Pydantic
            validated_context = MapFlavorContext(**data)
            result_dict = validated_context.model_dump()
            
            # 2. Populate Cache
            self.cache.set(tags, result_dict)
            
            return result_dict
            
        except Exception as e:
            logger.warning(f"Flavor generation failed with primary model: {e}")
            
            # Fallback to Ollama if not already using it
            if not isinstance(self.model, OllamaClient):
                logger.info("Attempting fallback to Local LLM (Ollama)...")
                try:
                    self.model = OllamaClient(model=os.environ.get("LOCAL_LLM_MODEL", "llama3:latest"))
                    # Retry with new model
                    return self.generate_map_flavor(tags, lore_context)
                except Exception as ollama_e:
                    logger.error(f"Fallback to Ollama failed: {ollama_e}")
            
            return self._get_fallback_flavor()

    def generate_combat_narrative(self, combat_log: List[str]) -> str:
        """Legacy method for live narration (still available if needed)."""
        if not self.model or not combat_log: return ""
        clean_log = [l for l in combat_log if "Error" not in l]
        if not clean_log: return ""

        prompt = f"""
        Narrate this combat sequence in 2 gritty sentences. Do not use numbers.
        Events:
        {chr(10).join(clean_log)}
        """
        try:
            return self.model.generate_content(prompt).text.strip()
        except:
            return ""

    def _get_fallback_flavor(self) -> Dict[str, Any]:
        return {
            "environment_description": "A quiet area with nothing notable.",
            "visuals": ["Grey stones", "Dust"],
            "sounds": ["Silence"],
            "smells": ["Stale air"],
            "combat_hits": ["You hit the target.", "A solid strike."],
            "combat_misses": ["You miss.", "The attack goes wide."],
            "spell_casts": ["Energy gathers."],
            "enemy_intros": ["An enemy approaches."]
        }

ai_client = LLMService()
