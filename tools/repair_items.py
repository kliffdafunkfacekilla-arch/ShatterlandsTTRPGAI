import json
import os

FILE_PATH = r"AI-TTRPG/monolith/modules/rules_pkg/data/item_templates.json"

def repair():
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # The corrupted chunk we identified
    bad_chunk = """    "item_fireball_scroll": {
        "name": "Scroll of Fireball",
        "type": "charm",
        "hands"
    ],
    "damage_dice": "1d4","""

    # The correct chunk
    good_chunk = """    "item_fireball_scroll": {
        "name": "Scroll of Fireball",
        "type": "charm",
        "category": "scroll",
        "weight": 0.1,
        "slots": [
            "equipped_gear"
        ],
        "effects": [
            {
                "type": "damage",
                "value": 20,
                "description": "Casts Fireball"
            }
        ],
        "icon": "icon_scroll_fire",
        "sprite_ref": "sprite_scroll_fire"
    },
    "item_brawling_gloves": {
        "name": "Brawling Gloves",
        "type": "weapon",
        "category": "Unarmed/Fist Weapons",
        "weight": 1.0,
        "slots": [
            "hands"
        ],
        "damage_dice": "1d4","""

    if bad_chunk in content:
        print("Found bad chunk. Repairing...")
        new_content = content.replace(bad_chunk, good_chunk)
        
        # Verify JSON validity
        try:
            json.loads(new_content)
            print("JSON is valid after repair.")
            
            with open(FILE_PATH, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("File saved.")
        except json.JSONDecodeError as e:
            print(f"Error: Repair resulted in invalid JSON: {e}")
    else:
        print("Bad chunk not found. File might be different than expected.")
        # Print a snippet to help debug
        start_idx = content.find('"item_fireball_scroll"')
        if start_idx != -1:
            print("Snippet around item_fireball_scroll:")
            print(content[start_idx:start_idx+300])

if __name__ == "__main__":
    repair()
