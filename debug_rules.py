import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.join(os.getcwd(), 'AI-TTRPG'))

try:
    from monolith.modules import rules as rules_api
    
    print("--- Origin Choices ---")
    origins = rules_api.get_origin_choices()
    for o in origins:
        print(f"- {o['name']}")

    print("\n--- Childhood Choices ---")
    childhoods = rules_api.get_childhood_choices()
    for c in childhoods:
        print(f"- {c['name']}")

    print("\n--- Coming of Age Choices ---")
    coas = rules_api.get_coming_of_age_choices()
    for c in coas:
        print(f"- {c['name']}")

except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Error: {e}")
