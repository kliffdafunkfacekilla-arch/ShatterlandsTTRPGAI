"""
Test script for the Event Engine
Run from project root: python tests/test_event_engine.py
"""
import sys
import os

# Add AI-TTRPG to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../AI-TTRPG')))

from monolith.modules.story_pkg.event_engine import check_and_generate_events
from monolith.modules.story_pkg.schemas import WorldStateContext


def test_scenario(name: str, context: WorldStateContext):
    """Test a scenario and print results."""
    print("="*60)
    print(f"{name}")
    print("="*60)
    print(f"Context: reputation={context.player_reputation}, "
          f"resources={context.kingdom_resource_level}, "
          f"combat={context.last_combat_outcome}, "
          f"tags={context.current_location_tags}")
    print()
    
    events = check_and_generate_events(context)
    
    for event in events:
        print(f"[EVENT: {event.event_id}] ({event.trigger_type.value})")
        print(f"  Consequence: {event.consequence_type.value}")
        print(f"  Narrative: {event.narrative_text}")
        print(f"  Payload: {event.payload}")
    print()


if __name__ == '__main__':
    # Scenario 1: Low Reputation in the Forest (Should trigger BANDIT_AMBUSH)
    test_scenario(
        "SCENARIO 1: Low Reputation in Forest",
        WorldStateContext(
            player_reputation=-10,
            kingdom_resource_level=50,
            last_combat_outcome=None,
            current_location_tags=["forest", "road"]
        )
    )

    # Scenario 2: Safe Area (Should trigger AMBIENT_FLAVOR_NEUTRAL)
    test_scenario(
        "SCENARIO 2: Safe/Neutral Context",
        WorldStateContext(
            player_reputation=10,
            kingdom_resource_level=80,
            last_combat_outcome=None,
            current_location_tags=["city_outskirts"]
        )
    )

    # Scenario 3: Critical Hit with High Reputation
    test_scenario(
        "SCENARIO 3: Critical Hit with High Reputation",
        WorldStateContext(
            player_reputation=15,
            kingdom_resource_level=50,
            last_combat_outcome="CRITICAL_HIT",
            current_location_tags=["battlefield"]
        )
    )

    # Scenario 4: Player Defeat (Should trigger PLAYER_DEFEATED)
    test_scenario(
        "SCENARIO 4: Player Defeat",
        WorldStateContext(
            player_reputation=5,
            kingdom_resource_level=50,
            last_combat_outcome="DEFEAT",
            current_location_tags=["dungeon"]
        )
    )

    # Scenario 5: Mine with Low Resources
    test_scenario(
        "SCENARIO 5: Resource Shortage in Mine",
        WorldStateContext(
            player_reputation=0,
            kingdom_resource_level=15,
            last_combat_outcome=None,
            current_location_tags=["mine", "underground"]
        )
    )

    print("✅ All scenarios tested successfully!")
