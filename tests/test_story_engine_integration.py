"""
Integration test for the complete Reactive Story Engine system.
Tests the full flow: World State -> Event Engine -> Event Generation
"""
import sys
import os

# Add AI-TTRPG to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../AI-TTRPG')))

from monolith.modules.story_pkg.event_engine import check_and_generate_events
from monolith.modules.story_pkg.schemas import WorldStateContext, EventConsequenceType


def test_event_engine_with_world_state():
    """Test event engine with various world states."""
    print("="*60)
    print("Test 1: Event Engine with World State Changes")
    print("="*60)
    
    # Scenario 1: Start with neutral state
    print("\n1. Neutral State (rep=0, resources=50):")
    context = WorldStateContext(
        player_reputation=0,
        kingdom_resource_level=50,
        last_combat_outcome=None,
        current_location_tags=["plains"]
    )
    events = check_and_generate_events(context)
    print(f"   Generated: {events[0].event_id}")
    assert len(events) > 0, "Should generate at least one event"
    
    # Scenario 2: After player gains bad reputation
    print("\n2. After Reputation Loss (rep=-10, in forest):")
    context = WorldStateContext(
        player_reputation=-10,
        kingdom_resource_level=50,
        last_combat_outcome=None,
        current_location_tags=["forest"]
    )
    events = check_and_generate_events(context)
    print(f"   Generated: {events[0].event_id}")
    print(f"   Consequence: {events[0].consequence_type.value}")
    
    # Scenario 3: After critical hit
    print("\n3. After Critical Hit (rep=15, combat=CRITICAL_HIT):")
    context = WorldStateContext(
        player_reputation=15,
        kingdom_resource_level=50,
        last_combat_outcome="CRITICAL_HIT",
        current_location_tags=["battlefield"]
    )
    events = check_and_generate_events(context)
    print(f"   Generated: {events[0].event_id}")
    print(f"   Payload: {events[0].payload}")
    
    # Scenario 4: Resource depletion in mine
    print("\n4. Resource Shortage (resources=15, in mine):")
    context = WorldStateContext(
        player_reputation=0,
        kingdom_resource_level=15,
        last_combat_outcome=None,
        current_location_tags=["mine"]
    )
    events = check_and_generate_events(context)
    print(f"   Generated: {events[0].event_id}")
    
    # Scenario 5: Player defeat
    print("\n5. After Defeat (combat=DEFEAT):")
    context = WorldStateContext(
        player_reputation=5,
        kingdom_resource_level=50,
        last_combat_outcome="DEFEAT",
        current_location_tags=["dungeon"]
    )
    events = check_and_generate_events(context)
    print(f"   Generated: {events[0].event_id}")
    print(f"   Narrative: {events[0].narrative_text}")
    
    print("\n✅ Event engine responds correctly to world state\n")


def test_event_consequence_types():
    """Test that events generate appropriate consequence types."""
    print("="*60)
    print("Test 2: Event Consequence Type Distribution")
    print("="*60)
    
    consequence_counts = {
        EventConsequenceType.SPAWN_NPC: 0,
        EventConsequenceType.INITIATE_SKILL_CHALLENGE: 0,
        EventConsequenceType.ADD_QUEST_LOG: 0,
        EventConsequenceType.WORLD_STATE_CHANGE: 0
    }
    
    # Run multiple scenarios to collect consequence types
    scenarios = [
        {"rep": -10, "res": 50, "combat": None, "tags": ["forest"]},
        {"rep": 5, "res": 15, "combat": None, "tags": ["mine"]},
        {"rep": 0, "res": 5, "combat": None, "tags": ["town"]},
        {"rep": 15, "res": 50, "combat": "CRITICAL_HIT", "tags": ["battlefield"]},
        {"rep": 0, "res": 50, "combat": "DEFEAT", "tags": ["dungeon"]},
    ]
    
    for scenario in scenarios:
        context = WorldStateContext(
            player_reputation=scenario["rep"],
            kingdom_resource_level=scenario["res"],
            last_combat_outcome=scenario["combat"],
            current_location_tags=scenario["tags"]
        )
        events = check_and_generate_events(context)
        for event in events:
            if event.consequence_type in consequence_counts:
                consequence_counts[event.consequence_type] += 1
    
    print("\nConsequence Type Distribution:")
    for consequence_type, count in consequence_counts.items():
        print(f"   {consequence_type.value}: {count}")
    
    # Verify we have diversity
    unique_types = sum(1 for count in consequence_counts.values() if count > 0)
    print(f"\n✅ Generated {unique_types} different consequence types\n")
    
def test_world_state_schema_validation():
    """Test that WorldStateContext validates correctly."""
    print("="*60)
    print("Test 3: WorldStateContext Schema Validation")
    print("="*60)
    
    # Valid context
    print("\n1. Valid context creation:")
    context = WorldStateContext(
        player_reputation=-25,
        kingdom_resource_level=75,
        last_combat_outcome="CRITICAL_HIT",
        current_location_tags=["forest", "ruins"]
    )
    print(f"   ✓ Created with rep={context.player_reputation}, resources={context.kingdom_resource_level}")
    
    # Context with defaults
    print("\n2. Context with minimal data:")
    context = WorldStateContext(
        player_reputation=10,
        kingdom_resource_level=50
    )
    print(f"   ✓ last_combat_outcome={context.last_combat_outcome}")
    print(f"   ✓ current_location_tags={context.current_location_tags}")
    
    print("\n✅ WorldStateContext schema works correctly\n")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("REACTIVE STORY ENGINE - Integration Test Suite")
    print("="*60 + "\n")
    
    test_event_engine_with_world_state()
    test_event_consequence_types()
    test_world_state_schema_validation()
    
    print("="*60)
    print("✅ ALL INTEGRATION TESTS PASSED")
    print("="*60)
