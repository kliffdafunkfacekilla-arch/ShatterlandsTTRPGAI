import os
import sys
import subprocess


def test_monolith_startup_runs_and_exits():
    """Run the monolith startup as a subprocess and assert it exits with code 0.

    This is a lightweight integration test that exercises the programmatic Alembic
    upgrade path and the registered demo commands. It helps catch schema drift
    and startup errors in CI.
    """
    env = os.environ.copy()
    env["MONOLITH_STORY_DB_INIT"] = "auto"
    env["MONOLITH_WORLD_DB_INIT"] = "auto"
    env["MONOLITH_RUN_ONCE"] = "true"

    cmd = [sys.executable, "-m", "AI-TTRPG.monolith.start_monolith"]

    # Run the monolith runner; capture output for diagnostics if it fails.
    proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90, text=True)

    # Print output to pytest logs for debugging on failure
    print(proc.stdout)

    assert proc.returncode == 0, f"Monolith exited with code {proc.returncode}"
