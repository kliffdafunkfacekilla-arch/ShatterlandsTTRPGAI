# Shatterlands AI-TTRPG

A Python-based framework for playing a custom Tabletop RPG (TTRPG) with an AI running as the Dungeon Master (DM). The project is split into a backend monolith and a Kivy-based frontend client.

## Architecture

The project follows a modular monolith architecture with a separate frontend client.

### Backend Monolith (`AI-TTRPG/monolith`)
The core game logic resides in the `monolith` directory. It is composed of several specialized packages:

*   **`rules_pkg`**: The Rules Engine. Handles all game mechanics, including stat calculation, dice rolling, talent logic, and item definitions. It loads data from JSON files in `rules_pkg/data/`.
*   **`world_pkg`**: The World Engine. Manages the persistent world state, including locations, NPCs, items on the ground, and traps. Handles database operations for world entities.
*   **`character_pkg`**: The Character Engine. Manages player character state, including stats, inventory, equipment, and health.
*   **`story_pkg`**: The Story Engine. Orchestrates gameplay loops, combat encounters, dialogue, and shop interactions. It acts as the glue between the other packages.
*   **`ai_dm_pkg`**: A placeholder for the AI Dungeon Master logic (currently keyword-based).
*   **`camp_pkg`**: Manages camping and resting mechanics.

The monolith uses an `EventBus` and `Orchestrator` for internal communication, though many interactions are currently synchronous direct calls for simplicity.

### Frontend Client (`game_client`)
The game client is built using the **Kivy** framework. It provides a graphical user interface for the player to interact with the game world.

*   **`main.py`**: The entry point for the client application.
*   **`views/`**: Contains the screen classes (e.g., `MainInterfaceScreen`, `CombatScreen`, `CharacterSheetScreen`).
*   **`asset_loader.py`**: Handles loading and caching of game assets (images, tilemaps).
*   **`settings_manager.py`**: Manages user preferences.

## Setup

### Prerequisites
*   Python 3.9+
*   `pip` (Python package manager)
*   `virtualenv` (recommended)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_folder>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/macOS
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    The project has dependencies for both the monolith and the client.
    ```bash
    pip install -r AI-TTRPG/monolith/requirements.txt
    pip install -r game_client/requirements.txt
    ```
    *Note: You may need to install system dependencies for Kivy (e.g., SDL2, GStreamer) depending on your OS.*

## Usage

### Running the Game
To launch the full game (Client + Monolith), run the client's entry point. The client handles initializing the monolith in the background.

```bash
python game_client/main.py
```

### Development

*   **Running Tests:**
    Tests are located in `AI-TTRPG/monolith/tests`.
    ```bash
    export PYTHONPATH=$PYTHONPATH:$(pwd)/AI-TTRPG
    pytest AI-TTRPG/monolith/tests/
    ```

*   **Database Migrations:**
    The monolith uses Alembic for database migrations (if configured). The startup script `start_monolith.py` attempts to run migrations automatically. To reset the database state, you may need to delete the `*.db` files (usually `test.db` or similar in the module folders) and restart the application.

## Directory Structure

```text
.
├── AI-TTRPG/               # Backend Monolith
│   └── monolith/
│       ├── modules/        # Domain packages (rules, world, story, etc.)
│       ├── tests/          # Unit and integration tests
│       ├── event_bus.py    # Internal event system
│       └── orchestrator.py # Central coordinator
├── game_client/            # Frontend Application
│   ├── assets/             # Graphics and data files
│   ├── views/              # UI Screens
│   ├── main.py             # Entry point
│   └── asset_loader.py     # Asset management
└── README.md
```

## Contributing
Please ensure all new code includes docstrings following the Google Python Style Guide. Run existing tests before submitting changes to ensure no regressions.
