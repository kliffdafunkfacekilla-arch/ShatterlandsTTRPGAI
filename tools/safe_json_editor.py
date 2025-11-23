import json
import sys
import os

def safe_edit(file_path, key_path, value_json):
    """
    Safely edits a JSON file.
    file_path: Path to the JSON file.
    key_path: Dot-separated path to the key to update (e.g., "items.sword.damage").
              Use "[]" to append to a list (e.g., "items[]").
    value_json: JSON string of the value to set.
    """
    print(f"Editing {file_path} at {key_path}...")
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON file: {e}")
        sys.exit(1)

    try:
        new_value = json.loads(value_json)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse value JSON: {e}")
        sys.exit(1)

    # Navigate to the target
    keys = key_path.split('.')
    current = data
    
    for i, key in enumerate(keys[:-1]):
        if key.endswith('[]'):
            key = key[:-2]
            if key not in current:
                current[key] = []
            current = current[key]
            # If we are appending to a list, we can't really "navigate" further 
            # unless we are targeting the last item. 
            # For simplicity, this script assumes list append is the final operation 
            # OR we are selecting an index like "items[0]".
            # Let's support "items[0]" syntax later if needed.
        else:
            if key not in current:
                current[key] = {}
            current = current[key]

    last_key = keys[-1]
    
    if last_key.endswith('[]'):
        # Append to list
        target_list_key = last_key[:-2]
        if target_list_key not in current:
            current[target_list_key] = []
        if isinstance(current[target_list_key], list):
            current[target_list_key].append(new_value)
            print(f"Appended value to {target_list_key}.")
        else:
            print(f"Error: {target_list_key} is not a list.")
            sys.exit(1)
    else:
        # Set value
        current[last_key] = new_value
        print(f"Set {last_key} to new value.")

    # Save back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print("File saved successfully.")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python safe_json_editor.py <file_path> <key_path> <value_json>")
        sys.exit(1)
    
    safe_edit(sys.argv[1], sys.argv[2], sys.argv[3])
