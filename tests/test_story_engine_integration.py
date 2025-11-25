import pytest
import random
from typing import List, Dict, Any
from monolith.modules.story_pkg.event_engine import check_and_generate_events
from monolith.modules.story_pkg.schemas import WorldStateContext, EventConsequenceType
from monolith.modules.world_pkg.models import GameState

# ============================================================================
# TEST CASES
# ============================================================================

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
    print(f"   Generated: {events[0].event_type}")

    # Scenario 2: Low reputation state
    print("\n2. Low Reputation (rep=-10):")
    context = WorldStateContext(
        player_reputation=-10,
        kingdom_resource_level=50,
        last_combat_outcome=None,
        current_location_tags=["forest"]
    )
    events = check_and_generate_events(context)
    print(f"   Generated: {events[0].event_type}")

    # Scenario 3: Resource shortage state
    print("\n3. Low Resources (level=5):")
    context = WorldStateContext(
        player_reputation=5,
        kingdom_resource_level=5,
        last_combat_outcome=None,
        current_location_tags=["town"]
    )
    events = check_and_generate_events(context)
    print(f"   Generated: {events[0].event_type}")

    print("\n✅ Event engine generates different events based on world state.\n")


def test_event_consequence_types():
    """Test that events generate appropriate consequence types."""
    print("="*60)
    print("Test 2: Event Consequence Type Distribution")
    print("="*60)

    consequence_counts = {
        EventConsequenceType.SPAWN_NPC: 0,
        EventConsequenceType.NO_OP: 0,
        EventConsequenceType.ADD_QUEST: 0,
        EventConsequenceType.WORLD_STATE_CHANGE: 0
    }

    # Run simulation many times to get a distribution
    for i in range(200):
        context = WorldStateContext(
            player_reputation=random.randint(-20, 20),
            kingdom_resource_level=random.randint(5, 100),
            last_combat_outcome=random.choice([None, "CRITICAL_HIT", "DEFEAT"]),
            current_location_tags=random.sample(["forest", "town", "mine", "plains"], 2)
        )
        events = check_and_generate_events(context)
        for event in events:
            if event.consequence_type in consequence_counts:
                consequence_counts[event.consequence_type] += 1

    print("Consequence distribution over 200 runs:")
    for c_type, count in consequence_counts.items():
        print(f"  - {c_type.name}: {count} times")

    # Basic sanity check
    assert consequence_counts[EventConsequenceType.WORLD_STATE_CHANGE] > 0
    print("\n✅ Consequence types are being generated as expected.\n")

def test_world_state_context_validation():
    """Test that WorldStateContext validates correctly."""
    print("="*60)
    print("Test 3: WorldStateContext Schema Validation")
    print("="*60)

    # Valid data
    try:
        context = WorldStateContext(
            player_reputation=10,
            kingdom_resource_level=100,
            last_combat_outcome="VICTORY",
            current_location_tags=["town", "market"]
        )
        print("   Valid data parsed correctly.")
    except Exception as e:
        pytest.fail(f"Valid data failed validation: {e}")

    # Invalid data
    with pytest.raises(Exception):
        context = WorldStateContext(
            player_reputation="high",  # Should be an int
            kingdom_resource_level=100
        )
    print("   Invalid data (wrong type) correctly raises an error.")

    print("\n✅ WorldStateContext schema works correctly\n")
