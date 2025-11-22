import json
import sys

def load_json(path):
    """Helper to load a JSON file."""
    with open(path, 'r') as f:
        return json.load(f)

def verify_skills():
    """
    Verifies consistency between `stats_and_skills.json` and `talents.json`.

    Ensures that every skill defined in the master skill list has a corresponding
    entry in the talent skill mastery section, and that their governing stats match.
    """
    stats_skills = load_json("monolith/modules/rules_pkg/data/stats_and_skills.json")
    talents = load_json("monolith/modules/rules_pkg/data/talents.json")
    
    skill_categories = stats_skills.get("skill_categories", {})
    talent_skill_mastery = talents.get("single_skill_mastery", {})
    
    errors = []
    
    for category, skills_map in skill_categories.items():
        if category not in talent_skill_mastery:
            print(f"Note: Category '{category}' found in stats_and_skills but not in talents (might be intended).")
            continue
            
        talent_category_list = talent_skill_mastery[category]
        # talent_category_list is a list of dicts: {"skill": "Name", "stat_focus": "Stat", "talents": []}
        
        talent_skills = {item["skill"]: item["stat_focus"] for item in talent_category_list}
        
        for skill_name, stat in skills_map.items():
            if skill_name not in talent_skills:
                errors.append(f"Missing Skill in Talents: '{skill_name}' in category '{category}'")
            else:
                talent_stat = talent_skills[skill_name]
                if talent_stat != stat:
                    errors.append(f"Stat Mismatch for '{skill_name}': stats_and_skills says '{stat}', talents says '{talent_stat}'")
                    
        for skill_name in talent_skills:
            if skill_name not in skills_map:
                errors.append(f"Extra Skill in Talents: '{skill_name}' in category '{category}' not found in stats_and_skills")

    if errors:
        print("\nVerification Failed with Errors:")
        for e in errors:
            print(f"- {e}")
        sys.exit(1)
    else:
        print("\nVerification Successful! All skill categories align.")

if __name__ == "__main__":
    verify_skills()
