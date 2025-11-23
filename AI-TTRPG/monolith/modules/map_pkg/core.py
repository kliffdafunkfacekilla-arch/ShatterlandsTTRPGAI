import random
import numpy as np
from typing import List, Dict, Optional, Any
from . import models
from .data_loader import GENERATION_ALGORITHMS, TILE_DEFINITIONS

# --- Import AI Service ---
try:
    from ..ai_dm_pkg.llm_service import ai_client
except ImportError:
    ai_client = None

# --- Algorithm Selection ---
def select_algorithm(tags: List[str]) -> Optional[Dict[str, Any]]:
    """Finds a generation algorithm matching the input tags."""
    tag_set = set(t.lower() for t in tags)
    possible_matches = []
    for algo in GENERATION_ALGORITHMS:
        required_tags = set(t.lower() for t in algo.get("required_tags", []))
        if required_tags.issubset(tag_set):
            possible_matches.append(algo)

    if not possible_matches:
        return None
    return random.choice(possible_matches)

# --- Cellular Automata Implementation ---
def _count_neighbors(grid: np.ndarray, x: int, y: int, wall_id: int) -> int:
    """Counts wall neighbors for a cell, including diagonals."""
    count = 0
    height, width = grid.shape
    for i in range(-1, 2):
        for j in range(-1, 2):
            if i == 0 and j == 0:
                continue # Skip self
            nx, ny = x + i, y + j
            # Check bounds or count out-of-bounds as walls
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                count += 1
            elif grid[ny, nx] == wall_id:
                count += 1
    return count

def _run_ca_iteration(grid: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    """Runs a single iteration of the Cellular Automata simulation."""
    height, width = grid.shape
    new_grid = grid.copy()
    wall_id = params.get("wall_tile_id", 1)
    birth_limit = params.get("birth_limit", 4)
    death_limit = params.get("death_limit", 3)
    floor_id = params.get("floor_tile_id", 0)

    for y in range(height):
        for x in range(width):
            neighbors = _count_neighbors(grid, x, y, wall_id)
            # Apply rules
            if grid[y, x] == wall_id: # If it's currently a wall
                if neighbors < death_limit:
                    new_grid[y, x] = floor_id # Dies (becomes floor)
            else: # If it's currently a floor
                if neighbors > birth_limit:
                    new_grid[y, x] = wall_id # Born (becomes wall)
    return new_grid

def generate_cellular_automata(params: Dict[str, Any], width: int, height: int, seed: str) -> np.ndarray:
    """Generates a map using the Cellular Automata method."""
    random.seed(seed) # Use the seed

    # Robust seed conversion for numpy
    if seed.replace('.', '', 1).isdigit():
        np_seed = int(float(seed))
    else:
        np_seed = hash(seed) % (2**32 - 1)
    np.random.seed(np_seed)

    initial_density = params.get("initial_density", 0.45)
    iterations = params.get("iterations", 4)
    wall_id = params.get("wall_tile_id", 1)
    floor_id = params.get("floor_tile_id", 0)

    # 1. Initialize random grid
    grid = np.random.choice(
        [floor_id, wall_id],
        size=(height, width),
        p=[1 - initial_density, initial_density]
    )

    # 2. Run iterations
    for _ in range(iterations):
        grid = _run_ca_iteration(grid, params)

    return grid

# --- Drunkard's Walk Implementation ---
def generate_drunkards_walk(params: Dict[str, Any], width: int, height: int, seed: str) -> np.ndarray:
    """Generates a map using the Drunkard's Walk algorithm."""
    random.seed(seed)

    wall_id = params.get("wall_tile_id", 4)
    floor_id = params.get("floor_tile_id", 3)
    walk_steps = params.get("walk_steps", 500)

    # 1. Initialize grid full of walls
    grid = np.full((height, width), wall_id, dtype=int)

    # 2. Perform the walk(s)
    x, y = width // 2, height // 2

    for _ in range(walk_steps):
        if 0 <= y < height and 0 <= x < width:
            grid[y, x] = floor_id

        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
        new_x, new_y = x + dx, y + dy

        x = max(0, min(width - 1, new_x))
        y = max(0, min(height - 1, new_y))

    return grid

# --- Post-Processing ---
def post_process_add_border(grid: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    """Adds a border of wall tiles around the map."""
    wall_id = params.get("wall_tile_id", 1)
    grid[0, :] = wall_id
    grid[-1, :] = wall_id
    grid[:, 0] = wall_id
    grid[:, -1] = wall_id
    return grid

def post_process_clear_center(grid: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    """Clears a small area in the center to be floor tiles."""
    height, width = grid.shape
    center_x, center_y = width // 2, height // 2
    clear_radius = params.get("clear_center_radius", 2)
    floor_id = params.get("floor_tile_id", 0)

    for y in range(max(0, center_y - clear_radius), min(height, center_y + clear_radius + 1)):
        for x in range(max(0, center_x - clear_radius), min(width, center_x + clear_radius + 1)):
            grid[y, x] = floor_id
    return grid

def post_process_fill_unreachable(grid: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
    """Finds the largest floor area and fills smaller disconnected areas with walls."""
    height, width = grid.shape
    floor_id = params.get("floor_tile_id", 0)
    wall_id = params.get("wall_tile_id", 1)
    visited = np.zeros_like(grid, dtype=bool)
    regions = []

    for y in range(height):
        for x in range(width):
            if grid[y, x] == floor_id and not visited[y, x]:
                region_size = 0
                region_coords = []
                q = [(x, y)]
                visited[y, x] = True
                while q:
                    cx, cy = q.pop(0)
                    region_size += 1
                    region_coords.append((cx, cy))
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < width and 0 <= ny < height and \
                           grid[ny, nx] == floor_id and not visited[ny, nx]:
                            visited[ny, nx] = True
                            q.append((nx, ny))
                regions.append({'size': region_size, 'coords': region_coords})

    if not regions: return grid

    regions.sort(key=lambda r: r['size'], reverse=True)
    largest_region_coords = set((x,y) for x,y in regions[0]['coords'])

    new_grid = grid.copy()
    for y in range(height):
        for x in range(width):
            if grid[y,x] == floor_id and (x,y) not in largest_region_coords:
                new_grid[y,x] = wall_id
    return new_grid

POST_PROCESSING_FUNCTIONS = {
    "add_border_trees": post_process_add_border,
    "add_border_walls": post_process_add_border,
    "clear_center": post_process_clear_center,
    "fill_unreachable": post_process_fill_unreachable
}

# --- Spawn Point Placement ---
def find_spawn_points(grid: np.ndarray, floor_id: int, num_player: int = 1, num_enemy: int = 3) -> Dict[str, List[List[int]]]:
    """Finds valid floor tiles for spawn points."""
    height, width = grid.shape
    valid_spawns = []
    for y in range(height):
        for x in range(width):
            if grid[y, x] == floor_id:
                valid_spawns.append([x, y])

    if not valid_spawns:
        print("Warning: No valid floor tiles found for spawn points!")
        return {"player": [[height // 2, width // 2]], "enemy": []}

    random.shuffle(valid_spawns)

    player_spawns = valid_spawns[:num_player]
    enemy_spawns = valid_spawns[num_player : num_player + num_enemy]

    while len(enemy_spawns) < num_enemy and valid_spawns:
        enemy_spawns.append(random.choice(valid_spawns))

    return {
        "player": player_spawns,
        "enemy": enemy_spawns
    }

# --- Main Generation Runner (UPDATED) ---
def run_generation(algorithm: Dict[str, Any], seed: str, width_override: Optional[int] = None, height_override: Optional[int] = None) -> models.MapGenerationResponse:
    """
    Selects and executes the chosen procedural generation algorithm and post-processing.
    INCLUDES AI FLAVOR GENERATION STEP.
    """
    algo_name = algorithm.get("name", "Unknown Algorithm")
    algo_type = algorithm.get("algorithm", "cellular_automata")
    params = algorithm.get("parameters", {})

    width = width_override or params.get("width", 20)
    height = height_override or params.get("height", 15)

    print(f"Running generation using algorithm: {algo_name} ({algo_type}) with seed: {seed}")

    # 1. Run Algorithm
    grid_np: Optional[np.ndarray] = None
    if algo_type == "cellular_automata":
        grid_np = generate_cellular_automata(params, width, height, seed)
    elif algo_type == "drunkards_walk":
        grid_np = generate_drunkards_walk(params, width, height, seed)
    else:
        raise ValueError(f"Unknown algorithm type specified: {algo_type}")

    if grid_np is None:
        raise RuntimeError(f"Map generation failed for algorithm {algo_type}")

    # 2. Apply Post-Processing
    post_steps = algorithm.get("post_processing", [])
    for step_name in post_steps:
        func = POST_PROCESSING_FUNCTIONS.get(step_name)
        if func:
            print(f"Applying post-processing step: {step_name}")
            grid_np = func(grid_np, params)
        else:
            print(f"Warning: Unknown post-processing step '{step_name}'")

    # 3. Find Spawn Points
    floor_id = params.get("floor_tile_id", 0)
    spawn_points = find_spawn_points(grid_np, floor_id)

    # 4. --- NEW: Generate AI Flavor ---
    flavor_data = None
    
    # Default fallback flavor
    fallback_flavor = models.MapFlavorContext(
        environment_description="A quiet area with no distinct features.",
        visuals=["Standard terrain", "Nothing of note"],
        sounds=["Silence", "Wind blowing"],
        smells=["Earth", "Fresh air"],
        combat_hits=["You strike true.", "The blow connects."],
        combat_misses=["You miss.", "The attack goes wide."],
        spell_casts=["Energy gathers.", "Magic flares."],
        enemy_intros=["An enemy appears.", "You are not alone."]
    )

    if ai_client:
        print("Requesting Map Flavor from AI...")
        # Use tags from algorithm definition to guide the AI (e.g., "forest", "creepy")
        map_tags = algorithm.get("required_tags", ["generic"])
        try:
            flavor_dict = ai_client.generate_map_flavor(map_tags)
            if flavor_dict:
                flavor_data = models.MapFlavorContext(**flavor_dict)
            else:
                print("AI returned empty flavor, using fallback.")
                flavor_data = fallback_flavor
        except Exception as e:
            print(f"AI generation failed: {e}. Using fallback.")
            flavor_data = fallback_flavor
    else:
        print("AI Client not available, using fallback flavor.")
        flavor_data = fallback_flavor

    # 5. Build Response
    return models.MapGenerationResponse(
        width=width,
        height=height,
        map_data=grid_np.tolist(),
        seed_used=seed,
        algorithm_used=algo_name,
        spawn_points=spawn_points,
        flavor_context=flavor_data # <--- Attached
    )
