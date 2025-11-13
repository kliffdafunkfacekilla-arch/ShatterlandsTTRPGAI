# Rules Engine Service

## 1. Overview

The Rules Engine is a stateless FastAPI service that functions as the single source of truth for all game mechanics, data, and calculations. It is designed to be a fast, reliable "calculator" that other services can call to resolve game actions.



# Rules Engine


-   **Data Loading:** On startup, it loads all core game data, including stats, skills, abilities, talents, weapons, armor, injuries, and status effects, into `app.state` for quick access.
## 3. Key API Endpoints

### Combat Calculations & Rolls


## Features
- Stores abilities, items, skills, and rules in JSON files.
- Used by character creation and game logic.
-   `POST /v1/calculate/damage`: Calculates the final damage dealt to a target after considering the base weapon damage, relevant stats, and the target's Damage Reduction (DR).
-   `POST /v1/calculate/base_vitals`: Calculates a character's `max_hp` and resource pools, called by the `character_engine` during creation.

## Usage
- Access data in `data/` for rules and item lookups.
- Start service: integrated via monolith runner.

-   `GET /v1/lookup/all_stats`, `/all_skills`, `/all_ability_schools`: Return the master lists for these core character attributes.
-   `GET /v1/lookup/melee_weapon/{category_name}`: Returns the complete data for a melee weapon (damage, skill used, properties).
-   `GET /v1/lookup/armor/{category_name}`: Returns the complete data for a piece of armor (Damage Reduction, skill used).
-   `POST /v1/lookup/injury_effects`: Returns the mechanical effects of a specific injury.
-   `GET /v1/lookup/status_effect/{status_name}`: Returns the description and effects of a status like "Staggered" or "Bleeding".
-   `POST /v1/lookup/talents`: Finds which talents a character is eligible for based on their current stats and skills.
-   `GET /v1/lookup/npc_template/{template_id}`: Returns the generation parameters for a given NPC template ID. This is a crucial endpoint used by the `story_engine` to orchestrate NPC creation.
-   `GET /v1/lookup/item_template/{item_id}`: Looks up the definition for a given item ID, returning its type and category. This is used by the `story_engine` to determine which skill to use for a player's equipped weapon or armor.

## 4. Data Sources

The Rules Engine is entirely data-driven. All of its knowledge comes from the JSON files located in the `AI-TTRPG/rules_engine/data/` directory. Key files include:

-   `stats_and_skills.json`: Defines the core character stats and the master list of all skills.
-   `melee_weapons.json` & `ranged_weapons.json`: Contains the stats for all weapon categories.
-   `armor.json`: Contains the stats for all armor categories.
-   `talents.json`: Defines the prerequisites and effects of all available talents.
-   `injuries.json` & `status_effects.json`: Define the mechanical impacts of combat afflictions.
-   `skill_mappings.json`: Defines the mapping between equipment categories and the skills used to wield them.
-   `npc_templates.json`: Maps NPC template IDs (e.g., "goblin_scout") to the parameters needed by the `npc_generator` to create them.
-   `item_templates.json`: Maps item IDs (e.g., "item_iron_sword") to their type ("melee", "armor") and category (e.g., "Double/dual wield", "Bows and Firearms").

## 5. Dependencies

The Rules Engine is a foundational service and has **no dependencies** on any other service in the system.
