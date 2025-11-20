import json
from pathlib import Path

def audit_talents():
    """
    Checks `talents.json` for any talent entries missing the 'modifiers' field.

    Iterates through Single Stat Mastery, Dual Stat Focus, and Single Skill Mastery
    categories and reports any talents that lack mechanical modifier definitions.
    """
    path = Path("monolith/modules/rules_pkg/data/talents.json")
    with open(path, "r") as f:
        data = json.load(f)
    
    missing_mods = []
    total_talents = 0
    
    # Check single_stat_mastery
    for t in data.get("single_stat_mastery", []):
        total_talents += 1
        if "modifiers" not in t:
            missing_mods.append(f"SingleStat: {t.get('talent_name')}")
            
    # Check dual_stat_focus
    for t in data.get("dual_stat_focus", []):
        total_talents += 1
        if "modifiers" not in t:
            missing_mods.append(f"DualStat: {t.get('talent_name')}")
            
    # Check single_skill_mastery
    skill_mastery = data.get("single_skill_mastery", {})
    for category, skills in skill_mastery.items():
        if isinstance(skills, list): # It's a list of skill objects
             for skill_group in skills:
                 for t in skill_group.get("talents", []):
                     total_talents += 1
                     if "modifiers" not in t:
                         name = t.get("talent_name") or t.get("name")
                         missing_mods.append(f"SkillMastery ({category}): {name}")
        elif isinstance(skills, dict): # Nested dict structure
            for skill_name, skill_data in skills.items():
                # Check if skill_data has talents list
                if isinstance(skill_data, dict) and "talents" in skill_data:
                    for t in skill_data["talents"]:
                        total_talents += 1
                        if "modifiers" not in t:
                            name = t.get("talent_name") or t.get("name")
                            missing_mods.append(f"SkillMastery ({skill_name}): {name}")

    print(f"Total Talents: {total_talents}")
    print(f"Missing Modifiers: {len(missing_mods)}")
    if missing_mods:
        print("First 20 missing:")
        for m in missing_mods[:20]:
            print(f"- {m}")

if __name__ == "__main__":
    audit_talents()
