# Shatterlands TTRPG - Modding Guide

## Introduction

Shatterlands is designed to be **highly moddable**. Game content is defined in JSON files, making it easy to add custom abilities, talents, characters, and more.

---

## Modding Philosophy

- **Data-Driven**: All game content in JSON
- **No Code Required**: Just edit JSON files
- **Hot-Reload**: Some changes apply immediately
- **Validation**: Automatic error checking
- **Documentation**: Clear schemas

---

## Character Creation

### Character JSON Format

Create a new file in `./characters/your_character.json`:

```json
{
  "id": "unique_char_id",
  "name": "Character Name",
  "level": 1,
  "stats": {
    "Might": 12,
    "Endurance": 10,
    "Finesse": 14,
    "Logic": 8,
    "Charm": 10,
    "Instinct": 12
  },
  "max_hp": 30,
  "current_hp": 30,
  "current_location_id": 1,
  "position_x": 5,
  "position_y": 5,
  "talents": ["talent_id_1", "talent_id_2"],
  "abilities": ["ability_id_1", "ability_id_2"]
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Display name |
| `level` | integer | Character level (1-20) |
| `stats` | object | Six core stats |
| `max_hp` | integer | Maximum hit points |
| `current_hp` | integer | Current hit points |
| `current_location_id` | integer | Starting location |
| `position_x` | integer | X coordinate |
| `position_y` | integer | Y coordinate |

### Optional Fields

- `talents` - List of talent IDs
- `abilities` - List of ability IDs
- `equipment` - Equipped items
- `inventory` - Carried items
- `status_effects` - Active effects

---

## Creating Custom Abilities

### Location
`./AI-TTRPG/monolith/modules/rules_pkg/data/abilities.json`

### Ability Structure

```json
{
  "ability_id": "fireball_custom",
  "name": "Custom Fireball",
  "description": "Throws a ball of fire",
  "school": "Arcana",
  "tier": 1,
  "resource_cost": {
    "hp": 0,
    "stamina": 5,
    "composure": 0
  },
  "modifiers": [
    {
      "type": "damage",
      "damage_type": "fire",
      "base_damage": "2d6",
      "stat_modifier": "Logic"
    },
    {
      "type": "area_effect",
      "radius": 2,
      "shape": "circle"
    }
  ],
  "target_type": "single",
  "range": 10
}
```

### Available Modifier Types

1. **damage** - Deal damage
   ```json
   {
     "type": "damage",
     "damage_type": "physical|fire|cold|poison",
     "base_damage": "2d6",
     "stat_modifier": "Might"
   }
   ```

2. **heal** - Restore HP
   ```json
   {
     "type": "heal",
     "amount": "1d8",
     "stat_modifier": "Charm"
   }
   ```

3. **restore_resource** - Restore stamina/composure
   ```json
   {
     "type": "restore_resource",
     "resource": "stamina|composure",
     "amount": 10
   }
   ```

4. **buff** - Increase stats temporarily
   ```json
   {
     "type": "buff",
     "stat": "Might",
     "amount": 2,
     "duration_turns": 3
   }
   ```

5. **status** - Apply status effect
   ```json
   {
     "type": "status",
     "status_id": "poisoned",
     "duration_turns": 3,
     "save_stat": "Endurance",
     "save_dc": 12
   }
   ```

6. **immunity** - Grant immunity
   ```json
   {
     "type": "immunity",
     "damage_types": ["fire", "cold"],
     "duration_turns": 5
   }
   ```

7. **resource_max** - Increase max resources
   ```json
   {
     "type": "resource_max",
     "resource": "stamina",
     "increase": 10,
     "permanent": true
   }
   ```

---

## Creating Custom Talents

### Location
`./AI-TTRPG/monolith/modules/rules_pkg/data/talents.json`

### Talent Structure

```json
{
  "talent_name": "My Custom Talent",
  "category": "Single Stat",
  "stat": "Might",
  "score": 14,
  "tier": 1,
  "description": "Boost when Might is 14+",
  "modifiers": [
    {
      "type": "stat_bonus",
      "stat": "Might",
      "bonus": 2
    },
    {
      "type": "skill_check",
      "skill": "Athletics",
      "bonus": 3
    }
  ]
}
```

### Talent Categories

- **Single Stat** - Based on one stat reaching a threshold
- **Skill** - Based on skill proficiency
- **Dual Stat** - Based on two stats combined

### Common Talent Modifiers

1. **stat_bonus** - Permanent stat increase
2. **skill_check** - Bonus to skill checks
3. **damage_bonus** - Extra damage on attacks
4. **damage_resistance** - Reduce incoming damage
5. **advantage** - Roll twice, take best
6. **reroll** - Reroll failed checks

---

## Data Validation

### Automatic Checking

The game validates all JSON files on startup:

```
Loading Game Rules...
✅ Rules loaded: {
  'stats': 12,
  'skills': 72,
  'abilities': 531,
  'talents': 42
}
```

### Common Errors

**Missing Required Field**:
```
ERROR: Character missing 'name' field in warrior.json
```

**Invalid Stat Value**:
```
ERROR: Stat 'Might' must be between 1-20, got 25
```

**Unknown Ability ID**:
```
WARNING: Ability 'fireball_typo' not found in abilities.json
```

### Error Messages

All errors show:
- File name
- Line number (when possible)
- Exact problem
- Suggested fix

---

## Testing Your Mods

### 1. Validate JSON

Use an online validator: https://jsonlint.com/

### 2. Check Console

Launch game and watch for validation errors:
```bash
python game_client/main.py
```

### 3. In-Game Test

1. Create character with your custom content
2. Start new game
3. Test abilities/talents
4. Check effects apply correctly

---

## Advanced Modding

### Custom Status Effects

Edit `./AI-TTRPG/monolith/modules/rules_pkg/data/status_effects.json`:

```json
{
  "status_id": "custom_burn",
  "name": "Burning",
  "description": "Takes fire damage each turn",
  "damage_per_turn": "1d6",
  "damage_type": "fire",
  "duration_type": "turns",
  "removable": true,
  "stacks": false
}
```

### Custom Equipment

Edit `./AI-TTRPG/monolith/modules/rules_pkg/data/equipment.json`:

```json
{
  "item_id": "sword_of_awesome",
  "name": "Sword of Awesome",
  "type": "weapon",
  "damage": "1d8+2",
  "damage_type": "physical",
  "stat_bonuses": {
    "Might": 1
  },
  "special_properties": ["magical", "glowing"]
}
```

---

## Best Practices

### 1. Use Clear IDs
```json
// Good
"ability_id": "fireball_tier_2"

// Bad
"ability_id": "fb2"
```

### 2. Document Your Mods
Add comments in a separate README:
```
my_mod_pack/
├── abilities.json
├── talents.json
└── README.md  (explains what each does)
```

### 3. Test Incrementally
- Add one ability at a time
- Test before adding more
- Keep backups of working versions

### 4. Share Your Mods
- ZIP your JSON files
- Include README with:
  - What it adds
  - How to install
  - Any dependencies

---

## Mod Installation

### Installing Mods from Others

1. **Download** mod files (usually JSON)
2. **Backup** original files
3. **Copy** new files to correct directories:
   - Abilities → `./AI-TTRPG/monolith/modules/rules_pkg/data/abilities.json`
   - Talents → `./AI-TTRPG/monolith/modules/rules_pkg/data/talents.json`
   - Characters → `./characters/`
4. **Launch** game and check for errors

### Merging Mods

To combine multiple mods:

1. Open both JSON files
2. Merge arrays (don't duplicate IDs)
3. Save combined file
4. Validate JSON syntax

---

## Schema Reference

### Character Schema
See `./AI-TTRPG/monolith/modules/save_schemas.py` → `CharacterSave`

### Ability Schema
See abilities.json for examples

### Talent Schema
See talents.json for examples

---

## Getting Help

### Validation Errors
- Read the error message carefully
- Check file path and line number
- Compare to working examples

### Effect Not Working
- Verify modifier type is spelled correctly
- Check required fields are present
- Review console for warnings

### Game Crashes
- Check JSON syntax (use validator)
- Ensure all required fields present
- Review error logs

---

## Examples

### Example 1: Simple Healing Ability

```json
{
  "ability_id": "minor_heal",
  "name": "Minor Heal",
  "school": "Divine",
  "tier": 1,
  "resource_cost": {"composure": 3},
  "modifiers": [
    {
      "type": "heal",
      "amount": "1d8",
      "stat_modifier": "Charm"
    }
  ],
  "target_type": "ally",
  "range": 5
}
```

### Example 2: Area Damage Spell

```json
{
  "ability_id": "lightning_storm",
  "name": "Lightning Storm",
  "school": "Arcana",
  "tier": 3,
  "resource_cost": {"stamina": 10},
  "modifiers": [
    {
      "type": "damage",
      "damage_type": "lightning",
      "base_damage": "4d6",
      "stat_modifier": "Logic"
    },
    {
      "type": "area_effect",
      "radius": 3,
      "shape": "circle"
    }
  ],
  "target_type": "area",
  "range": 15
}
```

### Example 3: Buff Talent

```json
{
  "talent_name": "Iron Will",
  "category": "Single Stat",
  "stat": "Endurance",
  "score": 16,
  "modifiers": [
    {
      "type": "stat_bonus",
      "stat": "Endurance",
      "bonus": 2
    },
    {
      "type": "advantage",
      "check_type": "saving_throw",
      "stat": "Endurance"
    }
  ]
}
```

---

**Happy Modding!** 🎲
