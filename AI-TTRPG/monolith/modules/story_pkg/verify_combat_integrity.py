import ast
import sys
import os

file_path = r"c:\Users\krazy\Documents\GitHub\ShatterlandsTTRPGAI\AI-TTRPG\monolith\modules\story_pkg\combat_handler.py"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    tree = ast.parse(source)
    print("SUCCESS: Syntax is valid (AST parsed successfully).")

    found_functions = set()
    found_vars = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            found_functions.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found_vars.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                found_vars.add(node.target.id)

    required_functions = [
        "determine_npc_action",
        "handle_npc_turn",
        "handle_player_action",
        "_get_targets_in_aoe",
        "_handle_effect_move_self"
    ]

    missing = []
    for func in required_functions:
        if func in found_functions:
            print(f"OK: Found function '{func}'")
        else:
            print(f"MISSING: Function '{func}'")
            missing.append(func)

    if "ABILITY_EFFECT_HANDLERS" in found_vars:
        print("OK: Found variable 'ABILITY_EFFECT_HANDLERS'")
    else:
        print("MISSING: Variable 'ABILITY_EFFECT_HANDLERS'")
        missing.append("ABILITY_EFFECT_HANDLERS")

    if missing:
        print(f"FAILURE: Missing items: {missing}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED. File structure is correct.")

except SyntaxError as e:
    print(f"FAILURE: Syntax Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"FAILURE: An error occurred: {e}")
    sys.exit(1)
