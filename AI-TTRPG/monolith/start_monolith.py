"""Small runner to start the monolith and demonstrate wiring.

Run this file to boot the orchestrator and register built-in modules.
It is intentionally minimal and synchronous-friendly for local development.
"""
import asyncio
import sys
from pathlib import Path
import traceback
from typing import Optional
try:
    # alembic is an optional dev dependency; attempt to import
    from alembic.config import Config as AlembicConfig
    from alembic import command as alembic_command
except Exception:
    AlembicConfig = None  # type: ignore
    alembic_command = None  # type: ignore
# ensure AI-TTRPG folder is in sys.path and import monolith package by local name
import os
ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from monolith.orchestrator import get_orchestrator
from monolith.modules import register_all


async def _on_response(topic: str, payload):
    """Generic response handler to print what modules publish."""
    print(f"[response] {topic}: {payload}")


async def _main():
    orch = get_orchestrator()
    bus = orch.bus
    # Ensure story_engine DB exists and migrations applied (best-effort).
    def _ensure_story_db():
        STORY_ALEMBIC = ROOT / "story_engine" / "alembic.ini"
        import os

        # Control behavior with MONOLITH_STORY_DB_INIT env var:
        #  - 'migrate' : force alembic upgrade (fail if alembic missing/failed)
        #  - 'create'  : force create_all only
        #  - 'auto'    : try alembic then fallback to create_all (default)
        #  - 'none'    : do nothing
        mode = os.environ.get("MONOLITH_STORY_DB_INIT", "auto").lower()
        print(f"story db init mode: {mode}")

        # Try Alembic when requested/available
        if mode in ("auto", "migrate") and AlembicConfig and alembic_command and STORY_ALEMBIC.exists():
            try:
                # Ensure story_engine package is importable for alembic env.py
                story_pkg_path = str(ROOT / "story_engine")
                if story_pkg_path not in sys.path:
                    sys.path.insert(0, story_pkg_path)

                cfg = AlembicConfig(str(STORY_ALEMBIC))
                cfg.set_main_option("script_location", str(ROOT / "story_engine" / "alembic"))
                try:
                    from story_engine.app import database as se_db
                    db_url = getattr(se_db, "DATABASE_URL", "")
                    if db_url.startswith("sqlite:///"):
                        db_path = db_url.replace("sqlite:///", "")
                        db_path_obj = Path(db_path)
                        if not db_path_obj.is_absolute():
                            db_path_obj = (ROOT / db_path_obj).resolve()
                        db_url = f"sqlite:///{db_path_obj}"
                    cfg.set_main_option("sqlalchemy.url", db_url)
                except Exception:
                    pass

                print("Running story_engine alembic migrations...")
                alembic_command.upgrade(cfg, "head")
                print("story_engine migrations applied.")
                return
            except Exception:
                print("Alembic migration failed, falling back to create_all:")
                traceback.print_exc()
                if mode == "migrate":
                    raise RuntimeError("MONOLITH_STORY_DB_INIT=migrate requested but alembic upgrade could not be run")

        # If explicitly disabled, skip DB initialization
        if mode == "none":
            print("MONOLITH_STORY_DB_INIT=none; skipping story DB initialization.")
            return

        # Fallback / create_all path
        try:
            from story_engine.app import database as se_db
            from sqlalchemy import create_engine

            db_url = getattr(se_db, "DATABASE_URL", "")
            if db_url.startswith("sqlite:///"):
                db_path = db_url.replace("sqlite:///", "")
                db_path_obj = Path(db_path)
                if not db_path_obj.is_absolute():
                    db_path_obj = (ROOT / db_path_obj).resolve()
                db_path_obj.parent.mkdir(parents=True, exist_ok=True)
                abs_db_url = f"sqlite:///{db_path_obj}"
            else:
                abs_db_url = db_url

            engine = create_engine(abs_db_url, connect_args={"check_same_thread": False})
            se_Base = getattr(se_db, "Base")
            print("Creating story_engine tables via SQLAlchemy create_all()")
            se_Base.metadata.create_all(bind=engine)
            print("story_engine DB initialized.")
        except Exception:
            print("Failed to initialize story_engine DB via create_all(). See traceback:")
            traceback.print_exc()

    _ensure_story_db()
    # Ensure world_engine DB exists and migrations applied (best-effort).
    def _ensure_world_db():
        from pathlib import Path as _Path
        STORY_ALEMBIC = ROOT / "world_engine" / "alembic.ini"
        mode = os.environ.get("MONOLITH_WORLD_DB_INIT", "auto").lower()
        print(f"world db init mode: {mode}")

        # Run alembic if available
        if mode in ("auto", "migrate") and AlembicConfig and alembic_command and STORY_ALEMBIC.exists():
            try:
                story_pkg_path = str(ROOT / "world_engine")
                if story_pkg_path not in sys.path:
                    sys.path.insert(0, story_pkg_path)
                cfg = AlembicConfig(str(STORY_ALEMBIC))
                cfg.set_main_option("script_location", str(ROOT / "world_engine" / "alembic"))
                try:
                    from world_engine.app import database as we_db
                    db_url = getattr(we_db, "DATABASE_URL", "")
                    if db_url.startswith("sqlite:///"):
                        db_path = db_url.replace("sqlite:///", "")
                        db_path_obj = _Path(db_path)
                        if not db_path_obj.is_absolute():
                            db_path_obj = (ROOT / db_path_obj).resolve()
                        db_url = f"sqlite:///{db_path_obj}"
                    cfg.set_main_option("sqlalchemy.url", db_url)
                except Exception:
                    pass
                print("Running world_engine alembic migrations...")
                alembic_command.upgrade(cfg, "head")
                print("world_engine migrations applied.")
                return
            except Exception:
                print("World alembic migration failed, falling back to create_all:")
                traceback.print_exc()
                if mode == "migrate":
                    raise RuntimeError("MONOLITH_WORLD_DB_INIT=migrate requested but alembic upgrade could not be run")

        if mode == "none":
            print("MONOLITH_WORLD_DB_INIT=none; skipping world DB initialization.")
            return

        try:
            from world_engine.app import database as we_db
            from sqlalchemy import create_engine as _create_engine
            db_url = getattr(we_db, "DATABASE_URL", "")
            if db_url.startswith("sqlite:///"):
                db_path = db_url.replace("sqlite:///", "")
                db_path_obj = _Path(db_path)
                if not db_path_obj.is_absolute():
                    db_path_obj = (ROOT / db_path_obj).resolve()
                db_path_obj.parent.mkdir(parents=True, exist_ok=True)
                abs_db_url = f"sqlite:///{db_path_obj}"
            else:
                abs_db_url = db_url
            engine = _create_engine(abs_db_url, connect_args={"check_same_thread": False})
            se_Base = getattr(we_db, "Base")
            print("Creating world_engine tables via SQLAlchemy create_all()")
            se_Base.metadata.create_all(bind=engine)
            print("world_engine DB initialized.")
            # world_engine DB initialized via create_all()
        except Exception:
            print("Failed to initialize world_engine DB via create_all(). See traceback:")
            traceback.print_exc()

    _ensure_world_db()
    # register modules (they subscribe to the bus)
    register_all(orch)
    # start orchestrator hook
    await orch.start()
    # give modules a moment to subscribe their handlers
    await asyncio.sleep(0.1)
    
    # subscribe to all response.* events to capture and display module outputs
    await bus.subscribe("response.rules.get_skill_for_category", _on_response)
    await bus.subscribe("response.encounter.generate", _on_response)
    await bus.subscribe("response.map.generate", _on_response)
    await bus.subscribe("combat.enemy_defeated", _on_response)
    # story events
    await bus.subscribe("story.combat_initialized", _on_response)
    await bus.subscribe("story.npc_turn_started", _on_response)
    await bus.subscribe("story.combat_concluded", _on_response)
    await bus.subscribe("story.interaction_resolved", _on_response)
    await bus.subscribe("story.narrative_advanced", _on_response)
    
    # demo: publish a command that modules will handle
    print("Monolith started; publishing demo commands:")
    print("  - start_combat")
    await orch.handle_command("start_combat", {"enemy_id": "goblin_1"})
    print("  - rules.get_skill_for_category")
    await orch.handle_command("rules.get_skill_for_category", {"category": "Plate Armor"})
    print("  - encounter.generate")
    await orch.handle_command("encounter.generate", {"tags": ["forest"]})
    print("  - map.generate")
    await orch.handle_command("map.generate", {"width": 8, "height": 6})
    print("  - story.start_combat")
    await orch.handle_command("story.start_combat", {
        "location_id": 1,
        "player_ids": ["player_1"],
        "npc_template_ids": ["goblin_scout", "goblin_warrior"],
        "map_data": [[0, 0, 3, 0], [0, 3, 3, 0], [3, 0, 0, 3], [0, 3, 0, 0]]
    })
    print("  - story.interact")
    await orch.handle_command("story.interact", {
        "actor_id": "player_1",
        "target_id": "chest_01"
    })
    print("  - story.advance_narrative")
    await orch.handle_command("story.advance_narrative", {"node_id": "chapter_2_start"})
    # keep alive briefly to allow background tasks to process
    await asyncio.sleep(2.0)


if __name__ == "__main__":
    asyncio.run(_main())
