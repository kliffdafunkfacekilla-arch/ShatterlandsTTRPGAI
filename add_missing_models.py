# Script to add all missing model definitions to models.py
import re

# Read core.py to find all the model usages
with open('AI-TTRPG/monolith/modules/rules_pkg/core.py', 'r', encoding='utf-8') as f:
    core_content = f.read()

# Models to add based on the code we've seen
models_to_add = '''
class ContestedAttackRequest(BaseModel):
    attacker_attacking_stat_score: int
    attacker_skill_rank: int
    attacker_attack_roll_bonus: int = 0
    attacker_attack_roll_penalty: int = 0
    defender_armor_stat_score: int
    defender_armor_skill_rank: int
    defender_weapon_penalty: int = 0
    defender_defense_roll_bonus: int = 0
   defender_defense_roll_penalty: int = 0

class ContestedAttackResponse(BaseModel):
    attacker_roll: int
    attacker_stat_mod: int
    attacker_skill_bonus: int
    attacker_total_modifier: int
    attacker_final_total: int
    defender_roll: int
    defender_stat_mod: int
    defender_skill_bonus: int
    defender_total_modifier: int
    defender_final_total: int
    outcome: str
    margin: int

class DamageRequest(BaseModel):
    damage_dice: str  # e.g. "1d6"
    stat_bonus: int = 0
    misc_bonus: int = 0
    misc_penalty: int = 0

class DamageResponse(BaseModel):
    dice_rolls: List[int]
    dice_total: int
    stat_bonus: int
    misc_bonus: int
    misc_penalty: int
    final_damage: int
'''

# Read the current models.py
with open('AI-TTRPG/monolith/modules/rules_pkg/models.py', 'r', encoding='utf-8') as f:
    models_content = f.read()

# Add the new models after NpcGenerationRequest
insertion_point = models_content.find('class NpcGenerationRequest(BaseModel):')
if insertion_point != -1:
    # Find the end of NpcGenerationRequest class
    next_class = models_content.find('\nclass ', insertion_point + 10)
    if next_class != -1:
        # Insert before the next class
        models_content = models_content[:next_class] + '\n' + models_to_add + models_content[next_class:]
    else:
        # Add at the end
        models_content += '\n' + models_to_add

# Write back
with open('AI-TTRPG/monolith/modules/rules_pkg/models.py', 'w', encoding='utf-8') as f:
    f.write(models_content)

print("Added missing models to models.py")
