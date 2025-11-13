# AI-TTRPG

A Python framework to play a custom TTRPG with an AI running as DM.

This project is built as a **modular monolith**. The entire backend is a single, unified Python application that communicates with a React frontend.

## Getting Started

Follow these steps to run the complete application.

### 1. Run the Backend (Monolith)

The backend is a single application. It requires Python 3.11+.

```bash
# 1. Navigate to the monolith directory
cd AI-TTRPG/monolith

# 2. Install all required Python packages
pip install -r requirements.txt

# 3. Run the monolith server.
# This script will automatically run all database migrations
# and start the application.
python start_monolith.py
```
The backend is now running. You will see logs in your terminal indicating that all modules have registered and the server is running (indefinitely).

### 2. Run the Frontend (Player Interface)

The frontend is a React application. It requires Node.js.

```bash
# 1. Open a *new* terminal window
# 2. Navigate to the player_interface directory
cd player_interface

# 3. Install all required Node.js packages (only needed once)
npm install

# 4. Start the frontend development server
npm run dev
```

You can now open your browser to the URL shown in the terminal (usually http://localhost:5173) to play the game.

## Project Architecture

The backend logic is located in `AI-TTRPG/monolith/`. It is broken down into several key modules:

* **`story`**: The central orchestrator that manages combat and game flow.
* **`world`**: Manages the state of the game world, locations, and NPCs.
* **`character`**: Manages the state of player characters.
* **`rules`**: A stateless "calculator" for all game rules, combat, and NPC generation.
* **`map`**: A stateless generator for tile maps, called by the `world` module.
* **`encounter`**: A stateless library for encounter templates.

For more detailed information, see `PROJECT_DOCUMENTATION.md`.
