import re

# Additional models needed based on core.py analysis
additional_models = '''
class InitiativeRequest(BaseModel):
    endurance: int
    reflexes: int
    fortitude: int
    logic: int
    intuition: int
    willpower: int

class InitiativeResponse(BaseModel):
    roll: int
    total: int
    breakdown: Dict[str, int]
'''

# Read the current models.py
with open('AI-TTRPG/monolith/modules/rules_pkg/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find a good insertion point (after DamageResponse)
if 'class DamageResponse(BaseModel):' in content:
    # Find where DamageResponse ends
    insertion_point = content.find('class DamageResponse(BaseModel):')
    # Find the next class or end of file
    next_class = content.find('\n\nclass ', insertion_point + 10)
    if next_class != -1:
        content = content[:next_class] + '\n' + additional_models + content[next_class:]
    else:
        content += '\n' + additional_models
else:
    # Just append at the end
    content += '\n' + additional_models

# Write back
with open('AI-TTRPG/monolith/modules/rules_pkg/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Added additional models to models.py")
