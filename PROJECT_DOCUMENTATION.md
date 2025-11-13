# AI-TTRPG System Documentation

## 1. High-Level Architecture

The AI-TTRPG system is a Python-based backend built on a **modular monolith architecture**. It consists of a single, unified application that internally organizes functionality into distinct modules, each handling a specific domain of the game. This design promotes modularity and maintainability while simplifying development and deployment.

The modules are contained within the `AI-TTRPG/monolith/modules/` directory and are managed by a central orchestrator.

The modules are divided into two primary categories:

* **Stateful Modules:** These three modules manage persistent game data using individual SQLite databases (e.g., `characters.db`, `world.db`, `story.db`). Their logic is contained in `_pkg` sub-directories (e.g., `world_pkg/`).
    * **`character`**: Manages the creation, state, and progression of player characters.
    * **`world`**: Manages the persistent state of the game world, including locations, NPCs, and items.
    * **`story`**: Manages campaign state, quests, and active combat encounters.

* **Stateless Modules:** These modules act as data providers and "calculators." They load their necessary data from local JSON files upon startup.
    * **`rules`**: The single source of truth for all game rules, combat calculations, and NPC generation.
    * **`map`**: Procedurally generates tile-based maps. This logic is called *by* the `world` module on demand.
    * **`encounter`**: A simple content library for pre-defined encounter templates.

### Inter-Module Communication Flow

Modules communicate via direct, in-process function calls, primarily orchestrated by the `story` module. The `story` module imports and calls functions from the `rules`, `world`, and `character` modules to execute complex game logic.

+------------------+ +-----------------+ +-----------------+ | player_interface |----->| story (Module) |----->| character (Module) | +------------------+ +-------+---------+ +-----------------+ ^ | (Player State - characters.db) | | | v | +---------------->+-----------------+ | | world (Module) | | +-----------------+ | (World State - world.db) v +-------+---------+ | rules (Module) | +-----------------+ (Rules, Calcs, NPC Gen)


## 2. Module Breakdown

### `story` (Orchestrator)

* **Purpose:** Acts as the central nervous system. It receives high-level requests (e.g., "start combat," "interact") and orchestrates the necessary calls to other modules to execute them.
* **Logic:** `monolith/modules/story_pkg/`
* **Core Logic:**
    * `combat_handler.py`: Manages the entire lifecycle of a combat encounter, from setup to turn-by-turn resolution.
    * `interaction_handler.py`: Processes non-combat player interactions with world objects.
* **Data:** Manages active campaign state, quests, story flags, and the state of ongoing combat encounters in `story.db`.
* **Dependencies:** Calls all other stateful and stateless modules.

### `world` (Stateful)

* **Purpose:** Manages the persistent state of the game world. It is the source of truth for "what is where".
* **Logic:** `monolith/modules/world_pkg/`
* **Core Logic:**
    * `crud.py`: Contains `get_location_context`, which retrieves the full state of a location.
    * **On-Demand Map Generation:** If `get_location_context` is called for a location with no map, this module automatically calls the `map` module to generate and save one.
* **Data:** Manages locations, NPCs, items, and their states in `world.db`.
* **Dependencies:** Calls the `map` module.

### `character` (Stateful)

* **Purpose:** The authoritative source for player character data. It manages character sheets, including stats, skills, inventory, and combat-related data.
* **Logic:** `monolith/modules/character_pkg/`
* **Core Logic:**
    * `services.py`: Handles character creation by calling the `rules` module.
    * `crud.py`: Provides functions to `apply_damage`, `add_item_to_inventory`, etc.
* **Data:** Manages character sheets in `characters.db`.
* **Dependencies:** Calls the `rules` module.

### `rules` (Stateless)

* **Purpose:** The definitive source for all game mechanics, data, and calculations. This module also contains the logic for **NPC generation**, consolidated from the old `npc_generator` service.
* **Logic:** `monolith/modules/rules_pkg/`
* **Core Logic:**
    * `core.py`: Contains all combat calculation functions (`calculate_contested_attack`, `calculate_damage`) and the NPC generation logic (`generate_npc_template_core`).
* **Data:** Loads all game rules from its `data/` directory (e.g., `stats_and_skills.json`, `talents.json`, `generation_rules.json`) on startup.
* **Dependencies:** None.

### `map` (Stateless)

* **Purpose:** Procedurally generates tile-based maps for game locations.
* **Logic:** `monolith/modules/map_pkg/`
* **Data:** Loads algorithm parameters and tile definitions from its `data/` directory.
* **Dependencies:** None.

### `encounter` (Stateless)

* **Purpose:** A simple content library for providing pre-defined combat or skill-based encounters.
* **Logic:** `monolith/modules/encounter_pkg/`
* **Data:** Loads encounter definitions from its `data/` directory (e.g., `combat_encounters.json`).
* **Dependencies:** None.

## 3. Case Study: Spawning an NPC in Combat

The process of spawning an NPC when combat starts is a prime example of the modular monolith in action:

1.  **Initiation (`story`):** The `story` module (in `combat_handler.py`) receives a request to start combat, which includes a list of NPC template IDs (e.g., `["goblin_scout"]`).

2.  **Parameter Lookup (`rules`):** The `story` module calls the `rules` module's API function: `rules_api.get_npc_generation_params("goblin_scout")`. The `rules` module looks this up in its cached `npc_templates.json` data and returns the generation parameters.

3.  **Procedural Generation (`rules`):** The `story` module then calls `rules_api.generate_npc_template(...)`, passing in the parameters it just received. The `rules` module (in `rules_pkg/core.py`) uses its internal logic from `generation_rules.json` to procedurally generate a full NPC template, including stats and `max_hp`. It returns this full template.

4.  **World State Update (`world`):** The `story` module now has a complete, statted NPC. It calls the `world` module's API function: `world_api.spawn_npc_in_world(...)`, providing the full template and coordinates. The `world` module (in `world_pkg/crud.py`) creates the new `NpcInstance` in its `world.db`, officially placing it in the game world.

5.  **Combat Begins:** The `story` module proceeds with the rest of the combat setup.

This flow ensures that each module is only responsible for its own domain: the `rules` module knows the *recipe*, the `world` module *stores the dish*, and the `story` module *directs the process*.
