"""
Enhanced LLM Handler with Async Narrative Generation

This module provides:
- Async narrative generation (doesn't block UI)
- Narrative caching and pre-loading
- Context window management for token optimization
- Integration with existing Gemini API handler
- Fallback to synchronous if no API key

Design:
- Wraps existing generate_dm_response() in async executor
- Maintains narrative cache for common scenarios
- Pre-loads narratives for likely player actions
- Thread-safe cache management
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger("monolith.ai_dm.llm_enhanced")

# Import existing handler
try:
    from .llm_handler import generate_dm_response, HAS_GENAI
except ImportError:
    logger.warning("Could not import llm_handler, AI DM will be disabled")
    HAS_GENAI = False
    def generate_dm_response(*args, **kwargs):
        return "AI DM not available"


class NarrativeCache:
    """Thread-safe cache for pre-generated narratives"""
    
    def __init__(self, max_size: int = 50):
        self.cache: Dict[str, str] = {}
        self.max_size = max_size
        self._lock = threading.Lock()
        logger.info(f"Narrative cache initialized (max size: {max_size})")
    
    def get(self, key: str) -> Optional[str]:
        """Get cached narrative"""
        with self._lock:
            narrative = self.cache.get(key)
            if narrative:
                logger.info(f"Cache HIT: {key}")
            return narrative
    
    def set(self, key: str, narrative: str):
        """Store narrative in cache"""
        with self._lock:
            # Simple FIFO eviction if full
            if len(self.cache) >= self.max_size:
                # Remove oldest (first inserted)
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f"Cache evicted: {oldest_key}")
            
            self.cache[key] = narrative
            logger.info(f"Cache SET: {key}")
    
    def clear(self):
        """Clear all cached narratives"""
        with self._lock:
            self.cache.clear()
            logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        with self._lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size
            }


class AIContentManager:
    """Manages AI narrative generation with async execution and caching"""
    
    def __init__(self, api_key: Optional[str] = None, max_cache_size: int = 50):
        """Initialize AI DM manager
        
        Args:
            api_key: Google API key for Gemini (optional, can use env var)
            max_cache_size: Maximum number of cached narratives
        """
        self.api_key = api_key
        self.cache = NarrativeCache(max_cache_size)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ai_dm_")
        
        # Context management
        self.max_context_history = 5  # Keep last 5 interactions
        self.context_history: List[Dict[str, Any]] = []
        
        logger.info("AIContentManager initialized")
    
    def _generate_cache_key(self, action_type: str, context: Dict[str, Any]) -> str:
        """Generate a cache key from action and context
        
        Args:
            action_type: Type of action (e.g., "move", "ability")
            context: Game context
            
        Returns:
            Cache key string
        """
        # Simple key generation - could be more sophisticated
        location = context.get("location_name", "unknown")
        outcome = context.get("outcome", "")
        return f"{action_type}:{location}:{outcome}"
    
    async def generate_narrative_async(
        self,
        prompt_text: str,
        char_context: Dict[str, Any],
        loc_context: Dict[str, Any],
        recent_log: Optional[List] = None,
        action_type: str = "generic",
        use_cache: bool = True
    ) -> str:
        """Generate narrative asynchronously (non-blocking)
        
        Args:
            prompt_text: Player action description
            char_context: Character state
            loc_context: Location context
            recent_log: Recent event log
            action_type: Type of action for caching
            use_cache: Whether to use cached narratives
            
        Returns:
            Generated narrative text
        """
        # Check cache first
        if use_cache:
            cache_context = {
                "location_name": loc_context.get("name"),
                "outcome": prompt_text[:50]  # First 50 chars as outcome
            }
            cache_key = self._generate_cache_key(action_type, cache_context)
            cached = self.cache.get(cache_key)
            
            if cached:
                logger.info("Using cached narrative")
                return cached
        
        # Generate in background thread
        loop = asyncio.get_event_loop()
        
        try:
            narrative = await loop.run_in_executor(
                self.executor,
                self._synchronous_llm_call,
                prompt_text,
                char_context,
                loc_context,
                recent_log
            )
            
            # Update context history
            self._update_context_history({
                "prompt": prompt_text,
                "narrative": narrative,
                "action_type": action_type
            })
            
            # Cache the result
            if use_cache:
                self.cache.set(cache_key, narrative)
            
            return narrative
            
        except Exception as e:
            logger.exception(f"Async narrative generation failed: {e}")
            return f"The DM pauses momentarily... (Error: {str(e)})"
    
    def _synchronous_llm_call(
        self,
        prompt_text: str,
        char_context: Dict[str, Any],
        loc_context: Dict[str, Any],
        recent_log: Optional[List] = None
    ) -> str:
        """Synchronous LLM call (runs in thread pool)
        
        This wraps the existing generate_dm_response function.
        """
        try:
            # Use recent context history
            context_log = recent_log or self._get_recent_context()
            
            narrative = generate_dm_response(
                prompt_text=prompt_text,
                char_context=char_context,
                loc_context=loc_context,
                recent_log=context_log,
                api_key=self.api_key,
                request_type="narrative"
            )
            
            logger.info(f"Generated narrative ({len(narrative)} chars)")
            return narrative
            
        except Exception as e:
            logger.exception(f"LLM call failed: {e}")
            return f"The DM considers the situation... (Error: {str(e)})"
    
    def _update_context_history(self, interaction: Dict[str, Any]):
        """Update rolling context window"""
        self.context_history.append(interaction)
        
        # Keep only recent history
        if len(self.context_history) > self.max_context_history:
            self.context_history.pop(0)
    
    def _get_recent_context(self) -> List[Dict]:
        """Get recent context for LLM prompt"""
        return self.context_history[-3:] if self.context_history else []
    
    async def pre_generate_narratives(
        self,
        likely_actions: List[Dict[str, Any]],
        char_context: Dict[str, Any],
        loc_context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Pre-generate narratives for likely player actions
        
        Args:
            likely_actions: List of {action_type, prompt, context} dicts
            char_context: Character state
            loc_context: Location context
            
        Returns:
            Dict mapping action types to generated narratives
        """
        logger.info(f"Pre-generating {len(likely_actions)} narratives...")
        
        tasks = []
        for action in likely_actions:
            task = self.generate_narrative_async(
                prompt_text=action.get("prompt", ""),
                char_context=char_context,
                loc_context=loc_context,
                action_type=action.get("action_type", "generic"),
                use_cache=True  # Will cache results
            )
            tasks.append((action.get("action_type"), task))
        
        results = {}
        for action_type, task in tasks:
            try:
                narrative = await task
                results[action_type] = narrative
            except Exception as e:
                logger.error(f"Pre-generation failed for {action_type}: {e}")
        
        logger.info(f"Pre-generated {len(results)} narratives")
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the narrative cache"""
        return {
            "cache": self.cache.get_stats(),
            "context_history_size": len(self.context_history),
            "has_api": HAS_GENAI
        }
    
    def shutdown(self):
        """Clean shutdown of executor"""
        self.executor.shutdown(wait=True)
        logger.info("AIContentManager shut down")


# Module-level singleton
_ai_manager_instance: Optional[AIContentManager] = None

def get_ai_manager(api_key: Optional[str] = None) -> AIContentManager:
    """Get or create the singleton AI manager
    
    Args:
        api_key: Optional API key (only used on first call)
        
    Returns:
        AIContentManager instance
    """
    global _ai_manager_instance
    if _ai_manager_instance is None:
        _ai_manager_instance = AIContentManager(api_key=api_key)
    return _ai_manager_instance


# Convenience function for backward compatibility
async def generate_narrative_async(
    prompt_text: str,
    char_context: Dict[str, Any],
    loc_context: Dict[str, Any],
    recent_log: Optional[List] = None,
    api_key: Optional[str] = None
) -> str:
    """Convenience wrapper for async narrative generation
    
    This maintains backward compatibility while using the enhanced system.
    """
    manager = get_ai_manager(api_key)
    return await manager.generate_narrative_async(
        prompt_text=prompt_text,
        char_context=char_context,
        loc_context=loc_context,
        recent_log=recent_log
    )
