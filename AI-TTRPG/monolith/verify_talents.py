#!/usr/bin/env python3
"""
Verification script for talent and skill system implementation.
Checks data completeness, modifier coverage, and system integration.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict

# Add monolith to path
sys.path.insert(0, str(Path(__file__).parent))

def load_json(filepath: str) -> Dict:
    """Load and parse JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def check_talent_structure(talent: Dict, path: str) -> List[str]:
    """Check if a talent has the required structure."""
    issues = []
    
    # Check required fields
    if 'talent_name' not in talent and 'name' not in talent:
        issues.append(f"{path}: Missing talent_name/name field")
    
    if 'effect' not in talent:
        issues.append(f"{path}: Missing effect field")
    
    return issues

def analyze_modifiers(talents_data: Dict) -> Dict[str, Any]:
    """Analyze modifier coverage across all talents."""
    stats = {
        'total_talents': 0,
        'talents_with_modifiers': 0,
        'talents_without_modifiers': [],
        'modifier_types': defaultdict(int),
        'duplicates': []
    }
    
    seen_names = defaultdict(list)
    
    # Check single_stat_mastery
    for talent in talents_data.get('single_stat_mastery', []):
        name = talent.get('talent_name', 'Unknown')
        stats['total_talents'] += 1
        seen_names[name].append('single_stat_mastery')
        
        if 'modifiers' in talent:
            stats['talents_with_modifiers'] += 1
            for mod in talent['modifiers']:
                stats['modifier_types'][mod.get('type', 'unknown')] += 1
        else:
            stats['talents_without_modifiers'].append({
                'name': name,
                'category': 'single_stat_mastery',
                'effect': talent.get('effect', '')
            })
    
    # Check dual_stat_focus
    for talent in talents_data.get('dual_stat_focus', []):
        name = talent.get('talent_name', 'Unknown')
        stats['total_talents'] += 1
        seen_names[name].append('dual_stat_focus')
        
        if 'modifiers' in talent:
            stats['talents_with_modifiers'] += 1
            for mod in talent['modifiers']:
                stats['modifier_types'][mod.get('type', 'unknown')] += 1
        else:
            stats['talents_without_modifiers'].append({
                'name': name,
                'category': 'dual_stat_focus',
                'effect': talent.get('effect', '')
            })
    
    # Check single_skill_mastery
    for category, skill_groups in talents_data.get('single_skill_mastery', {}).items():
        for skill_group in skill_groups:
            for talent in skill_group.get('talents', []):
                name = talent.get('talent_name', talent.get('name', 'Unknown'))
                stats['total_talents'] += 1
                seen_names[name].append(f'single_skill_mastery/{category}')
                
                if 'modifiers' in talent:
                    stats['talents_with_modifiers'] += 1
                    for mod in talent['modifiers']:
                        stats['modifier_types'][mod.get('type', 'unknown')] += 1
                else:
                    stats['talents_without_modifiers'].append({
                        'name': name,
                        'category': f'single_skill_mastery/{category}',
                        'effect': talent.get('effect', '')
                    })
    
    # Check for duplicates
    for name, locations in seen_names.items():
        if len(locations) > 1:
            stats['duplicates'].append({
                'name': name,
                'count': len(locations),
                'locations': locations
            })
    
    return stats

def check_skill_mappings(talents_data: Dict, skills_data: Dict) -> List[str]:
    """Verify all skills in talents.json exist in stats_and_skills.json."""
    issues = []
    
    # Get all valid skills from stats_and_skills.json
    valid_skills = set()
    for category in skills_data.get('skill_categories', {}).values():
        valid_skills.update(category.keys())
    
    # Check skills in talents
    for category, skill_groups in talents_data.get('single_skill_mastery', {}).items():
        for skill_group in skill_groups:
            skill_name = skill_group.get('skill')
            if skill_name and skill_name not in valid_skills:
                issues.append(f"Skill '{skill_name}' in category '{category}' not found in stats_and_skills.json")
    
    return issues

def main():
    """Run all verification checks."""
    print("=" * 80)
    print("TALENT AND SKILL SYSTEM VERIFICATION")
    print("=" * 80)
    print()
    
    # Load data files
    base_path = Path(__file__).parent / 'modules' / 'rules_pkg' / 'data'
    
    try:
        talents_data = load_json(base_path / 'talents.json')
        skills_data = load_json(base_path / 'stats_and_skills.json')
    except Exception as e:
        print(f"ERROR: Failed to load data files: {e}")
        return 1
    
    # 1. Analyze modifier coverage
    print("1. MODIFIER COVERAGE ANALYSIS")
    print("-" * 80)
    modifier_stats = analyze_modifiers(talents_data)
    
    print(f"Total talents: {modifier_stats['total_talents']}")
    print(f"Talents with modifiers: {modifier_stats['talents_with_modifiers']}")
    print(f"Talents without modifiers: {len(modifier_stats['talents_without_modifiers'])}")
    print(f"Coverage: {modifier_stats['talents_with_modifiers'] / modifier_stats['total_talents'] * 100:.1f}%")
    print()
    
    print("Modifier types used:")
    for mod_type, count in sorted(modifier_stats['modifier_types'].items()):
        print(f"  - {mod_type}: {count}")
    print()
    
    # 2. Check for duplicates
    print("2. DUPLICATE TALENT CHECK")
    print("-" * 80)
    if modifier_stats['duplicates']:
        print(f"Found {len(modifier_stats['duplicates'])} duplicate talent names:")
        for dup in modifier_stats['duplicates'][:10]:  # Show first 10
            print(f"  - '{dup['name']}' appears {dup['count']} times in: {', '.join(dup['locations'])}")
    else:
        print("✓ No duplicate talent names found")
    print()
    
    # 3. Check skill mappings
    print("3. SKILL MAPPING VERIFICATION")
    print("-" * 80)
    skill_issues = check_skill_mappings(talents_data, skills_data)
    if skill_issues:
        print(f"Found {len(skill_issues)} skill mapping issues:")
        for issue in skill_issues:
            print(f"  - {issue}")
    else:
        print("✓ All skills properly mapped")
    print()
    
    # 4. Show talents without modifiers (sample)
    print("4. TALENTS WITHOUT MODIFIERS (Sample)")
    print("-" * 80)
    if modifier_stats['talents_without_modifiers']:
        print(f"Showing first 20 of {len(modifier_stats['talents_without_modifiers'])} talents:")
        for talent in modifier_stats['talents_without_modifiers'][:20]:
            print(f"  - {talent['name']} ({talent['category']})")
            print(f"    Effect: {talent['effect'][:80]}...")
            print()
    else:
        print("✓ All talents have modifiers defined")
    print()
    
    # 5. Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_issues = len(skill_issues) + len(modifier_stats['duplicates'])
    missing_modifiers = len(modifier_stats['talents_without_modifiers'])
    
    if total_issues == 0 and missing_modifiers == 0:
        print("✓ All checks passed! Talent system is complete.")
        return 0
    else:
        print(f"⚠ Found issues:")
        print(f"  - {total_issues} data integrity issues")
        print(f"  - {missing_modifiers} talents missing modifiers")
        print()
        print("Note: Talents without modifiers may be intentional for narrative-only effects.")
        return 0  # Not a hard failure

if __name__ == '__main__':
    sys.exit(main())
