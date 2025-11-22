# Development Standards & Guardrails

This document establishes strict guidelines for all AI agents and developers working on the Shatterlands TTRPG project. These rules are designed to prevent code destruction, data loss, and architectural regression.

## 1. Non-Destructive Editing Policy
*   **NEVER delete databases** (e.g., `*.db` files) to "fix" schema errors unless explicitly instructed by the user. Instead, create migration scripts (Alembic) or update the schema safely.
*   **NEVER rewrite entire files** when a small edit will suffice. Use targeted replacement tools to modify only the necessary lines.
*   **Preserve Comments and Formatting**: Do not strip comments or reformat code unrelated to your specific task.

## 2. Architectural Integrity
*   **Respect Module Boundaries**: Do not bypass established APIs (e.g., `rules_api`) to import internal modules directly unless necessary.
*   **Follow Existing Patterns**: If the project uses a specific pattern for data loading (e.g., `data_loader.py`), use it. Do not invent new ways to load data that duplicate existing logic.
*   **No "Lazy" Fixes**: Do not hardcode values or comment out erroring code just to make a quick fix. Investigate the root cause.

## 3. Verification & Safety
*   **Verify Before Committing**: Always run the application or relevant tests to verify a fix before marking a task as complete.
*   **Check for Side Effects**: When modifying a shared component (like `rules.py`), check if other parts of the system (e.g., `services.py`) rely on the old behavior.
*   **Ask for Help**: If a requested change seems risky or if you are unsure about the architecture, **STOP** and ask the user for clarification.

## 4. Error Handling
*   **Investigate First**: When encountering an error (e.g., `AttributeError`, `ImportError`), read the file first to understand the context. Do not blindly assume the code is wrong and delete it.
*   **Fix Forward**: Attempt to fix the code structure rather than reverting to a blank slate.

## 5. User Communication
*   **Be Honest**: If a fix requires a destructive action (like a DB reset), explain WHY and ask for permission first.
*   **Document Changes**: Keep the `walkthrough.md` or similar documentation updated with what was changed and why.
