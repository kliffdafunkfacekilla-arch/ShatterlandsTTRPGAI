
import sys
import os

# Add the monolith root to sys.path so we can import modules
sys.path.append(os.path.abspath("AI-TTRPG"))

try:
    print("Importing monolith.modules.map_pkg.models...")
    from monolith.modules.map_pkg import models
    print("Success.")

    print("Importing monolith.modules.ai_dm_pkg.llm_service...")
    from monolith.modules.ai_dm_pkg import llm_service
    print("Success.")

    print("Importing monolith.modules.map_pkg.core...")
    from monolith.modules.map_pkg import core
    print("Success.")

    print("Checking MapGenerationResponse fields...")
    if 'flavor_context' in models.MapGenerationResponse.model_fields:
        print("flavor_context found in MapGenerationResponse.")
    else:
        print("ERROR: flavor_context NOT found in MapGenerationResponse.")
        sys.exit(1)

    print("Running mock map generation (expecting fallback flavor due to no API key)...")
    req_dict = {
        "name": "Test Algo",
        "algorithm": "cellular_automata",
        "parameters": {
            "width": 10,
            "height": 10,
            "floor_tile_id": 0,
            "wall_tile_id": 1
        },
        "required_tags": ["test"]
    }

    # Mock finding spawn points if needed, but core.py handles it.

    response = core.run_generation(req_dict, seed="12345")

    print("Map generated.")
    print(f"Flavor Context: {response.flavor_context}")

    if response.flavor_context:
        print("Flavor context present.")
    else:
        print("Flavor context missing (unexpected even with fallback).")

except Exception as e:
    print(f"Verification failed: {e}")
    sys.exit(1)
