# Shatterlands Game Client

This is the Kivy-based frontend for the Shatterlands TTRPG. It connects directly to the backend "Monolith" (in `AI-TTRPG/`) by importing its modules.

## Prerequisites

- Python 3.8+
- `AI-TTRPG` monolith dependencies installed (see `../AI-TTRPG/monolith/README.md`).
- Kivy and other frontend dependencies.

## Installation

1.  **Install Frontend Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Install Monolith Dependencies**:
    (If you haven't already)
    ```bash
    pip install -r ../AI-TTRPG/monolith/requirements.txt
    ```

## Running the Client

The client is designed to be run from the `game_client` directory or the root.

```bash
# From repo root
python game_client/main.py
```

## Troubleshooting

- **Import Errors**: Ensure your `PYTHONPATH` includes the `AI-TTRPG` directory if the script's auto-pathing fails.
- **Database Locks**: Since the monolith uses SQLite by default, ensure no other process (like a separate backend server) has the database locked if you encounter I/O errors.
- **Asset Errors**: Verify that `game_client/assets/` contains the required images and fonts.

## Architecture

The client uses a standard Kivy `ScreenManager` architecture:
- **`main.py`**: Entry point, sets up the async loop and initializes the Monolith's orchestrator.
- **`views/`**: Contains individual screens (Combat, Inventory, Character Sheet).
- **`asset_loader.py`**: Centralized handling of sprites and resources.
- **`settings_manager.py`**: Manages local client settings (audio, video).
