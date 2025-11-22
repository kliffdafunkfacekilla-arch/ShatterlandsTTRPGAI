import re

# Read the file
with open('game_client/views/combat_screen.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add from __future__ import annotations after the docstring
content = content.replace(
    '"""\nimport logging',
    '"""\nfrom __future__ import annotations\n\nimport logging'
)

# 2. Add world_services import
content = content.replace(
    'from monolith.modules.world_pkg import crud as world_crud\n    from monolith.modules.world_pkg.database import SessionLocal as WorldSession',
    'from monolith.modules.world_pkg import crud as world_crud\n    from monolith.modules.world_pkg import services as world_services\n    from monolith.modules.world_pkg.database import SessionLocal as WorldSession'
)

#3. Update except block to include world_services
content = content.replace(
    'world_crud, WorldSession = None, None',
    'world_crud, world_services, WorldSession = None, None, None'
)

# 4. Replace world_crud.get_location_context calls with world_services.get_location_context
content = re.sub(
    r'self\.location_context = world_crud\.get_location_context\(world_db, loc_id\)',
    'self.location_context = world_services.get_location_context(world_db, loc_id)',
    content
)

content = re.sub(
    r'self\.location_context = world_crud\.get_location_context\(\s*world_db, self\.location_context\.get\(\'id\'\)\s*\)',
    'self.location_context = world_services.get_location_context(\n                    world_db, self.location_context.get(\'id\')\n                )',
    content
)

# Write the file back
with open('game_client/views/combat_screen.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("File updated successfully")
