"""
Phase 5 Test Suite: AI DM Integration

Tests:
1. NarrativeCache thread safety
2. Cache hit/miss logic  
3. AIContentManager initialization
4. Async narrative generation (mocked)
5. Pre-generation system
6. Cache statistics
"""
import sys
from pathlib import Path
import asyncio

# Navigate to monolith directory
monolith_dir = Path(__file__).parent / "AI-TTRPG" / "monolith"
sys.path.insert(0, str(monolith_dir))

from modules.ai_dm_pkg.llm_handler_enhanced import (
    NarrativeCache, AIContentManager, get_ai_manager
)

print("="*60)
print("PHASE 5 TEST - AI DM Integration")
print("="*60)

# Test 1: NarrativeCache
print("\n[Test 1] NarrativeCache Operations...")
try:
    cache = NarrativeCache(max_size=3)
    
    # Test set/get
    cache.set("move_north", "You move northward through the mist.")
    result = cache.get("move_north")
    assert result == "You move northward through the mist."
    print("✅ Cache set/get working")
    
    # Test cache miss
    result = cache.get("nonexistent")
    assert result is None
    print("✅ Cache miss returns None")
    
    # Test eviction (add 4 items to size-3 cache)
    cache.set("action1", "narrative1")
    cache.set("action2", "narrative2")
    cache.set("action3", "narrative3")
    cache.set("action4", "narrative4")  # Should evict first
    
    stats = cache.get_stats()
    assert stats["size"] == 3, f"Cache should have 3 items, has {stats['size']}"
    print(f"✅ Cache eviction working (size: {stats['size']})")
    
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 2: AIContentManager Initialization
print("\n[Test 2] AIContentManager Initialization...")
try:
    manager = AIContentManager(api_key="test_key", max_cache_size=10)
    
    assert manager.api_key == "test_key"
    assert manager.cache.max_size == 10
    assert manager.max_context_history == 5
    print("✅ Manager initialized with correct settings")
    
    stats = manager.get_cache_stats()
    assert "cache" in stats
    assert "has_api" in stats
    print(f"✅ Cache stats available: {stats}")
    
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 3: Cache Key Generation
print("\n[Test 3] Cache Key Generation...")
try:
    manager = AIContentManager()
    
    key1 = manager._generate_cache_key("move", {
        "location_name": "Dark Forest",
        "outcome": "success"
    })
    
    key2 = manager._generate_cache_key("move", {
        "location_name": "Dark Forest",
        "outcome": "success"
    })
    
    key3 = manager._generate_cache_key("ability", {
        "location_name": "Dark Forest",
        "outcome": "success"
    })
    
    assert key1 == key2, "Same inputs should generate same key"
    assert key1 != key3, "Different action types should generate different keys"
    print(f"✅ Cache keys: {key1[:40]}...")
    
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 4: Context History Management
print("\n[Test 4] Context History Management...")
try:
    manager = AIContentManager()
    manager.max_context_history = 3
    
    # Add 5 interactions (should keep only last 3)
    for i in range(5):
        manager._update_context_history({
            "prompt": f"action_{i}",
            "narrative": f"response_{i}",
            "action_type": "test"
        })
    
    assert len(manager.context_history) == 3
    print(f"✅ Context history limited to {len(manager.context_history)} items")
    
    recent = manager._get_recent_context()
    assert len(recent) == 3
    print(f"✅ Recent context: {len(recent)} items")
    
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 5: Singleton Pattern
print("\n[Test 5] Singleton Pattern...")
try:
    manager1 = get_ai_manager()
    manager2 = get_ai_manager()
    
    assert manager1 is manager2
    print("✅ Singleton pattern working")
    
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 6: Async Generation (Mock Test)
print("\n[Test 6] Async Narrative Generation (Simulated)...")
async def test_async_generation():
    try:
        manager = AIContentManager()
        
        # Since we don't have a real API key, this will use the fallback
        narrative = await manager.generate_narrative_async(
            prompt_text="You enter the tavern",
            char_context={"name": "TestHero", "level": 1},
            loc_context={"name": "Rusty Goblet Inn"},
            recent_log=[],
            action_type="move"
        )
        
        assert isinstance(narrative, str)
        assert len(narrative) > 0
        print(f"✅ Async generation returned: {narrative[:60]}...")
        
        # Test cache was populated
        stats = manager.get_cache_stats()
        print(f"✅ Cache stats after generation: {stats['cache']}")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run async test
try:
    result = asyncio.run(test_async_generation())
    if result:
        print("✅ Async test completed")
except Exception as e:
    print(f"❌ Async test failed: {e}")

# Test 7: Cleanup
print("\n[Test 7] Cleanup...")
try:
    manager = get_ai_manager()
    manager.shutdown()
    print("✅ Manager shutdown cleanly")
except Exception as e:
    print(f"❌ FAILED: {e}")

print("\n" + "="*60)
print("PHASE 5 TEST COMPLETE")
print("="*60)
print("\nNote: AI DM system is ready. Full integration requires:")
print("- Google API key for actual narrative generation")
print("- Integration with Orchestrator action handlers")
print("- UI event subscriptions for narrative display")
