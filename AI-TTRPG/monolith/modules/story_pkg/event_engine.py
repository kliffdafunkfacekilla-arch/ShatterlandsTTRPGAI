"""
Reactive Story Engine - Event Management System

This module implements the rule-based event generation logic for the AI Dungeon Master.
It monitors world state triggers and generates StoryEvent objects to drive narrative flow.
"""

import random
import logging
from typing import List, Dict, Any, Callable

# Import event schemas
from .schemas import (
    StoryEvent,
    EventTriggerType,
    EventConsequenceType,
    WorldStateContext
)

logger = logging.getLogger(__name__)


# Define the structure for a rule entry
Rule = Dict[str, Any]


# ============================================================================
# EVENT RULES DATABASE
# ============================================================================
# Each rule contains priority, chance, condition logic, and event generator
# In production, these could be loaded from JSON/database for hot-reloading

EVENT_RULES: List[Rule] = [
    {
        "event_id": "BANDIT_AMBUSH",
        "priority": 5,  # High priority means it is checked first
        "chance": 0.35,  # 35% chance to be considered if conditions pass
        "condition": lambda ctx: (
            ctx.current_location_tags and "forest" in ctx.current_location_tags
            and ctx.player_reputation < -5  # Only triggers if player has low reputation
        ),
        "generator": lambda ctx: StoryEvent(
            event_id="BANDIT_AMBUSH",
            trigger_type=EventTriggerType.REPUTATION_CHANGE,
            consequence_type=EventConsequenceType.SPAWN_NPC,
            narrative_text="A group of disgruntled bandits emerges from the shadows, intent on collecting the bounty on your head.",
            payload={"npc_type": "bandit_leader", "count": 3, "difficulty_mod": 1.2}
        )
    },
    {
        "event_id": "SILVER_DEPOSIT_FOUND",
        "priority": 1,
        "chance": 0.15,
        "condition": lambda ctx: (
            ctx.kingdom_resource_level < 20  # Kingdom needs silver
            and "mine" in ctx.current_location_tags
        ),
        "generator": lambda ctx: StoryEvent(
            event_id="SILVER_DEPOSIT_FOUND",
            trigger_type=EventTriggerType.RESOURCE_LOW,
            consequence_type=EventConsequenceType.INITIATE_SKILL_CHALLENGE,
            narrative_text="You discover a promising, unexploited vein of silver ore. Extracting it requires finesse.",
            payload={"skill_check": "Mining", "difficulty": 15}
        )
    },
    {
        "event_id": "PLAYER_DEFEATED",
        "priority": 10,  # Very high priority, always checked
        "chance": 1.0,  # 100% chance to be checked
        "condition": lambda ctx: (
            ctx.last_combat_outcome == "DEFEAT"
        ),
        "generator": lambda ctx: StoryEvent(
            event_id="PLAYER_DEFEATED",
            trigger_type=EventTriggerType.COMBAT_CRITICAL,
            consequence_type=EventConsequenceType.WORLD_STATE_CHANGE,
            narrative_text="Your recent defeat resonates through the region; rival factions will be emboldened.",
            payload={"global_morale_debuff": 5, "quest_status_update": "The path ahead is harder."}
        )
    },
    {
        "event_id": "CRITICAL_HIT_MORALE_BOOST",
        "priority": 7,
        "chance": 0.5,
        "condition": lambda ctx: (
            ctx.last_combat_outcome == "CRITICAL_HIT"
            and ctx.player_reputation > 10
        ),
        "generator": lambda ctx: StoryEvent(
            event_id="CRITICAL_HIT_MORALE_BOOST",
            trigger_type=EventTriggerType.COMBAT_CRITICAL,
            consequence_type=EventConsequenceType.WORLD_STATE_CHANGE,
            narrative_text="Your devastating blow inspires nearby allies! Word of your prowess spreads.",
            payload={"reputation_bonus": 2, "party_morale_boost": 10}
        )
    },
    {
        "event_id": "RESOURCE_SHORTAGE_QUEST",
        "priority": 3,
        "chance": 0.25,
        "condition": lambda ctx: (
            ctx.kingdom_resource_level < 10
            and "town" in ctx.current_location_tags
        ),
        "generator": lambda ctx: StoryEvent(
            event_id="RESOURCE_SHORTAGE_QUEST",
            trigger_type=EventTriggerType.RESOURCE_LOW,
            consequence_type=EventConsequenceType.ADD_QUEST_LOG,
            narrative_text="The townsfolk are desperate for supplies. A merchant approaches with an urgent request.",
            payload={
                "quest_id": "supply_run_001",
                "quest_title": "Desperate Times",
                "reward_gold": 50,
                "required_items": ["food_rations", "medicine"]
            }
        )
    }
]


# ============================================================================
# CORE EVENT ENGINE LOGIC
# ============================================================================

def check_and_generate_events(context: WorldStateContext) -> List[StoryEvent]:
    """
    Main function for the Reactive Story Engine.
    Processes the current world state against predefined rules to generate events.

    Args:
        context: The WorldStateContext containing all necessary runtime data.

    Returns:
        A list of zero or more StoryEvent objects.
    """
    events: List[StoryEvent] = []
    
    # Sort by priority (higher value first) to ensure high-impact events are processed first
    sorted_rules = sorted(EVENT_RULES, key=lambda x: x["priority"], reverse=True)

    logger.info(
        f"Event Engine processing context: tags={context.current_location_tags}, "
        f"reputation={context.player_reputation}, resources={context.kingdom_resource_level}"
    )

    for rule in sorted_rules:
        # Step 1: Probability Check (Introduces randomness)
        if random.random() > rule["chance"]:
            continue
            
        # Step 2: Condition Logic Check
        try:
            if rule["condition"](context):
                # Condition is met and chance roll passed: generate event
                event = rule["generator"](context)
                events.append(event)
                logger.info(f"Generated event: {event.event_id}")

                # Best Practice: Stop processing low-priority events after a high-priority event is triggered.
                # This prevents event spam and ensures narrative coherence.
                if rule["priority"] >= 5:
                    logger.debug(f"Breaking after high-priority event: {event.event_id}")
                    break

        except Exception as e:
            logger.error(f"Error evaluating rule {rule['event_id']}: {e}")
            # Non-critical failure; continue checking other rules.

    # Fallback to a neutral event if nothing triggered, for narrative flow consistency
    if not events:
        logger.debug("No events triggered, generating neutral ambient flavor")
        events.append(StoryEvent(
            event_id="AMBIENT_FLAVOR_NEUTRAL",
            trigger_type=EventTriggerType.PLAYER_ACTION,
            consequence_type=EventConsequenceType.WORLD_STATE_CHANGE,
            narrative_text="The immediate area is quiet, offering a moment of respite.",
            payload={"player_stamina_regenerate": 1}
        ))
    
    return events


# ============================================================================
# DEMONSTRATION / TESTING
# ============================================================================

if __name__ == '__main__':
    # Scenario 1: Low Reputation in the Forest (Should trigger BANDIT_AMBUSH)
    print("="*60)
    print("SCENARIO 1: Low Reputation in Forest")
    print("="*60)
    
    mock_context_low_rep = WorldStateContext(
        player_reputation=-10,
        kingdom_resource_level=50,
        last_combat_outcome=None,
        current_location_tags=["forest", "road"]
    )
    
    generated_events = check_and_generate_events(mock_context_low_rep)
    
    for event in generated_events:
        print(f"\n[EVENT: {event.event_id}] ({event.trigger_type.value})")
        print(f"  Narrative: {event.narrative_text}")
        print(f"  Payload: {event.payload}")

    # Scenario 2: High Reputation, Safe Area (Should trigger AMBIENT_FLAVOR_NEUTRAL)
    print("\n" + "="*60)
    print("SCENARIO 2: Safe/Neutral Context")
    print("="*60)
    
    mock_context_safe = WorldStateContext(
        player_reputation=10,
        kingdom_resource_level=80,
        last_combat_outcome=None,
        current_location_tags=["city_outskirts"]
    )

    generated_events = check_and_generate_events(mock_context_safe)
    
    for event in generated_events:
        print(f"\n[EVENT: {event.event_id}] ({event.trigger_type.value})")
        print(f"  Narrative: {event.narrative_text}")
        print(f"  Payload: {event.payload}")

    # Scenario 3: Critical Hit with High Reputation (Should trigger CRITICAL_HIT_MORALE_BOOST)
    print("\n" + "="*60)
    print("SCENARIO 3: Critical Hit with High Reputation")
    print("="*60)
    
    mock_context_crit = WorldStateContext(
        player_reputation=15,
        kingdom_resource_level=50,
        last_combat_outcome="CRITICAL_HIT",
        current_location_tags=["battlefield"]
    )

    generated_events = check_and_generate_events(mock_context_crit)
    
    for event in generated_events:
        print(f"\n[EVENT: {event.event_id}] ({event.trigger_type.value})")
        print(f"  Narrative: {event.narrative_text}")
        print(f"  Payload: {event.payload}")

    # Scenario 4: Player Defeat (Should trigger PLAYER_DEFEATED)
    print("\n" + "="*60)
    print("SCENARIO 4: Player Defeat")
    print("="*60)
    
    mock_context_defeat = WorldStateContext(
        player_reputation=5,
        kingdom_resource_level=50,
        last_combat_outcome="DEFEAT",
        current_location_tags=["dungeon"]
    )

    generated_events = check_and_generate_events(mock_context_defeat)
    
    for event in generated_events:
        print(f"\n[EVENT: {event.event_id}] ({event.trigger_type.value})")
        print(f"  Narrative: {event.narrative_text}")
        print(f"  Payload: {event.payload}")
