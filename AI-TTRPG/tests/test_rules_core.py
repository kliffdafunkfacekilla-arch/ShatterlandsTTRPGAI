import sys
import os
import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from monolith.modules.rules_pkg import core as rules_core
from monolith.modules.rules_pkg import models as rules_models

def test_calculate_modifier():
    assert rules_core.calculate_modifier(10) == 0
    assert rules_core.calculate_modifier(12) == 1
    assert rules_core.calculate_modifier(13) == 1
    assert rules_core.calculate_modifier(8) == -1
    assert rules_core.calculate_modifier(9) == -1
    assert rules_core.calculate_modifier(20) == 5
    assert rules_core.calculate_modifier(1) == -5

def test_calculate_base_vitals_all_10():
    """
    Tests the calculate_base_vitals function with all stats at a baseline of 10.
    """
    stats = {
        "Vitality": 10,
        "Endurance": 10,
        "Finesse": 10,
        "Reflexes": 10,
        "Knowledge": 10,
        "Might": 10,
        "Charm": 10,
        "Awareness": 10,
        "Logic": 10,
        "Intuition": 10,
        "Willpower": 10,
    }

    # With all stats at 10, all modifiers are 0.
    # Max HP = 5 + Vit Score (10) + End Mod (0) = 15
    # Resource Max = 5 + (Mod1 (0) + Mod2 (0)) = 5

    vitals = rules_core.calculate_base_vitals(stats)

    assert vitals.max_hp == 15
    assert vitals.resources["Chi"]["max"] == 5
    assert vitals.resources["Stamina"]["max"] == 5
    assert vitals.resources["Guile"]["max"] == 5
    assert vitals.resources["Presence"]["max"] == 5
    assert vitals.resources["Tactics"]["max"] == 5
    assert vitals.resources["Instinct"]["max"] == 5
    # Check that current is set to max
    assert vitals.resources["Stamina"]["current"] == 5


def test_calculate_base_vitals_varied_stats():
    """
    Tests the calculate_base_vitals function with a mix of different stat scores.
    """
    stats = {
        "Vitality": 14,    # Score: 14, Mod: +2
        "Endurance": 12,   # Score: 12, Mod: +1
        "Finesse": 16,     # Score: 16, Mod: +3
        "Reflexes": 8,     # Score: 8,  Mod: -1
        "Knowledge": 13,   # Score: 13, Mod: +1
        "Might": 18,       # Score: 18, Mod: +4
        "Charm": 5,        # Score: 5,  Mod: -3
        "Awareness": 11,   # Score: 11, Mod: +0
        "Logic": 14,       # Score: 14, Mod: +2
        "Intuition": 9,    # Score: 9,  Mod: -1
        "Willpower": 15,   # Score: 15, Mod: +2
    }

    # Max HP = 5 + Vit Score (14) + End Mod (+1) = 20
    # Chi = 5 + Finesse Mod (+3) + Reflexes Mod (-1) = 7
    # Stamina = 5 + Endurance Mod (+1) + Vitality Mod (+2) = 8
    # Guile = 5 + Finesse Mod (+3) + Knowledge Mod (+1) = 9
    # Presence = 5 + Might Mod (+4) + Charm Mod (-3) = 6
    # Tactics = 5 + Awareness Mod (+0) + Logic Mod (+2) = 7
    # Instinct = 5 + Intuition Mod (-1) + Willpower Mod (+2) = 6

    vitals = rules_core.calculate_base_vitals(stats)

    assert vitals.max_hp == 20
    assert vitals.resources["Chi"]["max"] == 7
    assert vitals.resources["Stamina"]["max"] == 8
    assert vitals.resources["Guile"]["max"] == 9
    assert vitals.resources["Presence"]["max"] == 6
    assert vitals.resources["Tactics"]["max"] == 7
    assert vitals.resources["Instinct"]["max"] == 6

def test_calculate_base_vitals_low_stats():
    """
    Tests that resource pools have a minimum value of 1.
    """
    stats = {
        "Vitality": 1,
        "Endurance": 1,
        "Finesse": 1,
        "Reflexes": 1,
        "Knowledge": 1,
        "Might": 1,
        "Charm": 1,
        "Awareness": 1,
        "Logic": 1,
        "Intuition": 1,
        "Willpower": 1,
    }
    # All mods are -5
    # Max HP = 5 + 1 + (-5) = 1. Should be max(1, 1) = 1
    # Resources = 5 + (-5) + (-5) = -5. Should be 1

    vitals = rules_core.calculate_base_vitals(stats)

    assert vitals.max_hp == 1
    assert vitals.resources["Chi"]["max"] == 1
    assert vitals.resources["Stamina"]["max"] == 1
    assert vitals.resources["Guile"]["max"] == 1
    assert vitals.resources["Presence"]["max"] == 1
    assert vitals.resources["Tactics"]["max"] == 1
    assert vitals.resources["Instinct"]["max"] == 1
    assert vitals.resources["Instinct"]["current"] == 1
