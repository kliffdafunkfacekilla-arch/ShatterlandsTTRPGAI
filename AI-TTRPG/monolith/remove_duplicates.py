#!/usr/bin/env python3
"""
Script to remove duplicate talent entries from talents.json
"""

import json
from pathlib import Path

def remove_duplicates():
    """Remove duplicate talent entries from talents.json."""
    talents_path = Path(__file__).parent / 'modules' / 'rules_pkg' / 'data' / 'talents.json'
    
    with open(talents_path, 'r') as f:
        data = json.load(f)
    
    # Track duplicates to remove
    duplicates_removed = 0
    
    # Remove duplicate Camouflage entry (lines 555-575)
    armor_skills = data['single_skill_mastery']['Armor']
    camouflage_entries = [i for i, skill in enumerate(armor_skills) if skill.get('skill') == 'Camouflage']
    if len(camouflage_entries) > 1:
        # Keep the second one (has both Stealth and Evasion mentioned)
        del armor_skills[camouflage_entries[0]]
        duplicates_removed += 1
        print(f"Removed duplicate Camouflage entry (kept the one with Stealth/Evasion)")
    
    # Remove duplicate Leather/Hides entry (lines 702-722)
    leather_entries = [i for i, skill in enumerate(armor_skills) if skill.get('skill') == 'Leather/Hides']
    if len(leather_entries) > 1:
        # Keep the second one (has Stealth mentioned)
        del armor_skills[leather_entries[0]]
        duplicates_removed += 1
        print(f"Removed duplicate Leather/Hides entry (kept the one with Stealth)")
    
    # Remove duplicate Daggers/Small Blades and Nature Weapons entries in Melee
    melee_skills = data['single_skill_mastery']['Melee']
    
    # Find Daggers duplicates
    daggers_entries = [i for i, skill in enumerate(melee_skills) if skill.get('skill') == 'Daggers/Small Blades']
    if len(daggers_entries) > 1:
        # Keep the first one
        del melee_skills[daggers_entries[1]]
        duplicates_removed += 1
        print(f"Removed duplicate Daggers/Small Blades entry")
    
    # Find Nature Weapons duplicates
    nature_entries = [i for i, skill in enumerate(melee_skills) if skill.get('skill') == 'Nature Weapons']
    if len(nature_entries) > 1:
        # Keep the second one (has Athletics check)
        del melee_skills[nature_entries[0]]
        duplicates_removed += 1
        print(f"Removed duplicate Nature Weapons entry")
    
    # Find Quick Thrown duplicates in Ranged
    ranged_skills = data['single_skill_mastery']['Ranged']
    quick_thrown_entries = [i for i, skill in enumerate(ranged_skills) if skill.get('skill') == 'Quick Thrown']
    if len(quick_thrown_entries) > 1:
        # Keep the first one
        del ranged_skills[quick_thrown_entries[1]]
        duplicates_removed += 1
        print(f"Removed duplicate Quick Thrown entry")
    
    # Find Investigation duplicates in Utility
    utility_skills = data['single_skill_mastery']['Utility']
    investigation_entries = [i for i, skill in enumerate(utility_skills) if skill.get('skill') == 'Investigation']
    if len(investigation_entries) > 1:
        # Keep the second one (has Perception)
        del utility_skills[investigation_entries[0]]
        duplicates_removed += 1
        print(f"Removed duplicate Investigation entry")
    
    # Find Evasion duplicates in Conversational
    conversational_skills = data['single_skill_mastery']['Conversational']
    evasion_entries = [i for i, skill in enumerate(conversational_skills) if skill.get('skill') == 'Evasion']
    if len(evasion_entries) > 1:
        # Keep the second one (has Stealth)
        del conversational_skills[evasion_entries[0]]
        duplicates_removed += 1
        print(f"Removed duplicate Evasion entry")
    
    # Write back to file
    with open(talents_path, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"\n✓ Removed {duplicates_removed} duplicate entries")
    print(f"✓ Updated {talents_path}")
    
    return duplicates_removed

if __name__ == '__main__':
    removed = remove_duplicates()
    print(f"\nDone! Removed {removed} duplicates.")
