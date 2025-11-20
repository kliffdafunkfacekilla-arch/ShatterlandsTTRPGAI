# AI-TTRPG Monolith

This repository contains the backend "Monolith" for the Shatterlands TTRPG system. It is a modular application built with FastAPI, SQLAlchemy, and Pydantic, designed to serve as the game engine and state manager.

## Architecture

The monolith is organized into distinct packages (modules) representing different domains of the game:

- **`character_pkg`**: Manages player character data, stats, inventory, talents, and progression. Handles core logic like `apply_passive_modifiers` for derived stats.
- **`story_pkg`**: Contains the `combat_handler` and quest/campaign management.
    - **Combat Engine**: A turn-based, data-driven combat system. Handles actions, effects, status management (DOTs, buffs/debuffs), and reactions.
- **`world_pkg`**: Manages NPCs, locations, and map data.
- **`rules_pkg`**: The source of truth for game rules. Loads data from JSON templates (`abilities.json`, `item_templates.json`, `talents.json`) and provides calculation logic for stats and modifiers.
- **`camp_pkg`**: (In Development) Manages resting, crafting, and downtime activities.

## Key Features

- **Data-Driven Abilities**: Combat abilities and items are defined in JSON and processed by a central effect router in `combat_handler.py`.
- **Passive Modifier System**: A unified `PassiveModifier` system aggregates bonuses from equipment and talents to calculate final character stats.
- **Event-Based Reactions**: The combat engine supports complex reaction triggers (e.g., attacks of opportunity, defensive spells) via `_check_and_trigger_reactions`.
- **Persistence**: All game state (characters, world, combat) is persisted via SQLAlchemy (SQLite by default).

## Development Status

### Active Areas
- **Combat System**: Core loop is functional. Area of Effect (AoE), status effects, and basic AI are implemented.
- **Inventory**: Equipment slots and passive stat application are working.
- **Talents**: Talent trees are loadable and apply static modifiers.

### Known Issues / TODOs
- **Area Persistence**: Persistent area effects (like "Wall of Fire") are currently logged but not mechanically enforced in the grid state.
- **Advanced AI**: NPC AI is currently basic (attack/move).
- **Frontend Integration**: The `game_client` is currently unstable and may require specific environment configurations to run.

## Setup & Running

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Server**:
    The entry point is typically `start_monolith.py` or running via `uvicorn` if an API entry point is exposed (currently designed as an in-process module for the Kivy client, but can be decoupled).

3.  **Testing**:
    Tests are located in `tests/` and `modules/*/tests/`. Run with `pytest`.
