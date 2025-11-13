# tools/model_migration_diff.py
"""Model vs Alembic migration diff checker.

Usage:
    python -m tools.model_migration_diff

Exits with status code 0 when no drift is found. Exits with 2 when drift is detected.
"""
from __future__ import annotations
import importlib
import importlib.util
import runpy
import os
import pkgutil
import re
import sys
from typing import Dict, List, Set

# Navigate up two levels from `tools/` to the project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONOLITH_DIR = os.path.join(ROOT, "AI-TTRPG", "monolith", "modules")

def find_services() -> List[str]:
    """Return module names (folder names) under monolith/modules that have _pkg subdirs."""
    services = []
    if not os.path.isdir(MONOLITH_DIR):
        return services
    for name in os.listdir(MONOLITH_DIR):
        path = os.path.join(MONOLITH_DIR, name)
        # A module is "stateful" if it has a `_pkg` subdir containing alembic
        pkg_dir = os.path.join(path, f"{name}_pkg")
        alembic_dir = os.path.join(pkg_dir, "alembic", "versions")

        # Check for <name>_pkg/alembic/versions
        if os.path.isdir(pkg_dir) and os.path.isdir(alembic_dir):
            services.append(name)
    return services

def load_model_tables(service_name: str) -> Dict[str, Set[str]]:
    """Import the models module for a service and return a mapping table_name -> set(column_name)."""
    result: Dict[str, Set[str]] = {}

    # Path to the models.py file, e.g., .../modules/world/world_pkg/models.py
    models_path = os.path.join(MONOLITH_DIR, f"{service_name}_pkg", 'models.py')

    if not os.path.exists(models_path):
        # Check alternate pathing in case module name != pkg name
        models_path = os.path.join(MONOLITH_DIR, service_name, f"{service_name}_pkg", 'models.py')
        if not os.path.exists(models_path):
            print(f"[WARN] models.py not found for {service_name} at {models_path}; skipping")
            return result

    try:
        text = open(models_path, 'r', encoding='utf-8').read()
    except Exception as e:
        print(f"[WARN] Could not read {models_path}: {e}")
        return result

    # Find class definitions and their bodies
    class_iter = list(re.finditer(r"^class\s+(?P<classname>\w+)\s*\([^\)]*\):", text, re.M))
    class_bounds: List[tuple[int, int, str]] = []  # (start, end, classname)
    for i, m in enumerate(class_iter):
        start = m.start()
        classname = m.group("classname")
        end = class_iter[i + 1].start() if i + 1 < len(class_iter) else len(text)
        class_bounds.append((start, end, classname))

    for start, end, classname in class_bounds:
        body = text[start:end]

        # Find __tablename__ in the class body
        tn = None
        m_tab = re.search(r"__tablename__\s*=\s*['\"](?P<table>[^'\"]+)['\"]", body)
        if m_tab:
            tn = m_tab.group("table")
            result.setdefault(tn, set())
        else:
            continue # Skip non-model classes

        # 1) Find simple attribute assignments like: name = Column(String, ...)
        for m in re.finditer(r"^\s*(?P<attr>\w+)\s*=\s*(?:sa\.)?Column\(", body, re.M):
            colname = m.group("attr")
            result.setdefault(tn, set()).add(colname)

        # 2) Find explicit Column/sa.Column calls with column name as first arg
        for m in re.finditer(r"(?:sa\.)?Column\(\s*['\"](?P<col>[^'\"]+)['\"]", body, re.S):
            result.setdefault(tn, set()).add(m.group("col"))

    return result
    
def parse_migration_columns(migration_text: str) -> Dict[str, Set[str]]:
    """Parse migration file text for created tables and added columns."""
    tables: Dict[str, Set[str]] = {}

    create_table_re = re.compile(r"op\.create_table\(\s*['\"](?P<table>[^'\"]+)['\"]\s*,(?P<body>.*?)\)\s", re.S)
    for m in create_table_re.finditer(migration_text):
        t = m.group("table")
        body = m.group("body")
        cols = set(re.findall(r"sa\.Column\(\s*['\"](?P<col>[^'\"]+)['\"]", body))
        if t not in tables:
            tables[t] = set()
        tables[t].update(cols)

    add_col_re = re.compile(r"op\.add_column\(\s*['\"](?P<table>[^'\"]+)['\"]\s*,\s*sa\.Column\(\s*['\"](?P<col>[^'\"]+)['\"]", re.S)
    for m in add_col_re.finditer(migration_text):
        t = m.group("table")
        c = m.group("col")
        tables.setdefault(t, set()).add(c)

    return tables

def load_migrations(service_name: str) -> Dict[str, Set[str]]:
    """Read all migration files under <service_name>_pkg/alembic/versions."""
    migrations_dir = os.path.join(MONOLITH_DIR, f"{service_name}_pkg", "alembic", "versions")
    if not os.path.isdir(migrations_dir):
         migrations_dir = os.path.join(MONOLITH_DIR, service_name, f"{service_name}_pkg", "alembic", "versions")

    result: Dict[str, Set[str]] = {}

    if not os.path.isdir(migrations_dir):
        print(f"[WARN] Migrations dir not found for {service_name} at {migrations_dir}")
        return result

    for fname in os.listdir(migrations_dir):
        if not fname.endswith('.py'):
            continue
        full = os.path.join(migrations_dir, fname)
        try:
            with open(full, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"[WARN] Could not read migration {full}: {e}")
            continue

        parsed = parse_migration_columns(text)
        for table, cols in parsed.items():
            result.setdefault(table, set()).update(cols)

    return result

def run_check() -> int:
    # Add project root to sys.path to allow imports
    if ROOT not in sys.path:
        sys.path.insert(0, str(ROOT))

    services = find_services()
    if not services:
        print(f"No stateful modules with <name>_pkg/alembic/ found under {MONOLITH_DIR}")
        return 0

    overall_ok = True

    for svc in services:
        print(f"\nChecking module: {svc}")

        model_tables = load_model_tables(svc)
        migration_tables = load_migrations(svc)

        # For each model table, compare columns
        for table, model_cols in sorted(model_tables.items()):
            mig_cols = migration_tables.get(table, set())
            missing = model_cols - mig_cols
            if missing:
                overall_ok = False
                print(f"[DRIFT] Module '{svc}' table '{table}' has model columns not in migrations:")
                for c in sorted(missing):
                    print(f"  - {c}")

        # Also check for tables defined in migrations but not in models (informational)
        for table in sorted(set(migration_tables) - set(model_tables)):
            print(f"[INFO] Migration for '{svc}' creates table '{table}' but no ORM model found (ok)")

    if overall_ok:
        print("\nNo model-vs-migration drift detected.")
        return 0
    else:
        print("\nModel-vs-migration drift detected. Create Alembic revisions to match models.")
        return 2

if __name__ == '__main__':
    rc = run_check()
    sys.exit(rc)
