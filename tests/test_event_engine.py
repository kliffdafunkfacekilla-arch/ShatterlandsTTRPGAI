import pytest
from unittest.mock import patch
from monolith.modules.story_pkg.event_engine import check_and_generate_events
from monolith.modules.story_pkg.schemas import WorldStateContext, StoryEvent

# Scenarios for testing
scenarios = [
    (
        "Low Reputation in Forest",
        WorldStateContext(
            player_reputation=-10,
            kingdom_resource_level=50,
            last_combat_outcome=None,
            current_location_tags=["forest", "road"],
        ),
        "BANDIT_AMBUSH",
    ),
    (
        "Safe/Neutral Context",
        WorldStateContext(
            player_reputation=10,
            kingdom_resource_level=80,
            last_combat_outcome=None,
            current_location_tags=["city_outskirts"],
        ),
        "AMBIENT_FLAVOR_NEUTRAL",
    ),
    (
        "Critical Hit with High Reputation",
        WorldStateContext(
            player_reputation=15,
            kingdom_resource_level=50,
            last_combat_outcome="CRITICAL_HIT",
            current_location_tags=["battlefield"],
        ),
        "CRITICAL_HIT_MORALE_BOOST",
    ),
    (
        "Player Defeat",
        WorldStateContext(
            player_reputation=5,
            kingdom_resource_level=50,
            last_combat_outcome="DEFEAT",
            current_location_tags=["dungeon"],
        ),
        "PLAYER_DEFEATED",
    ),
]

@pytest.mark.parametrize("name, context, expected_event_type", scenarios)
@patch('random.random', return_value=0.0)
def test_scenario(mock_random, name, context, expected_event_type):
    print(f"--- Testing Scenario: {name} ---")
    generated_events = check_and_generate_events(context)
    assert generated_events
    # Look for the expected event type in the generated events
    found_event = False
    for event in generated_events:
        if event.event_type == expected_event_type:
            found_event = True
            break
    assert found_event, f"Expected event type '{expected_event_type}' not found in generated events for scenario '{name}'"
