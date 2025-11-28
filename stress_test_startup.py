import sys
import os
import logging
import asyncio
import time
from pathlib import Path

# Setup paths
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
MONOLITH_PATH = APP_ROOT / "AI-TTRPG"
if str(MONOLITH_PATH) not in sys.path:
    sys.path.insert(0, str(MONOLITH_PATH))

# Configure logging to file only to keep console clean
logging.basicConfig(
    filename='stress_test.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

async def run_initialization_test(iteration):
    print(f"Iteration {iteration}: Starting...", end="\r")
    try:
        # Import fresh to simulate startup (limited effect in same process, but helps)
        from monolith.orchestrator import Orchestrator
        from monolith.event_bus import get_event_bus
        
        # Reset singleton if possible (hacky but needed for repeated tests in one process)
        import monolith.orchestrator
        monolith.orchestrator._orchestrator_instance = None
        
        orchestrator = Orchestrator()
        await orchestrator.initialize_engine()
        
        # Start a dummy new game to populate state
        # We need a dummy character file or mock the load
        # Since we can't easily mock file IO here without more code, let's just check if orchestrator is initialized
        # and skip the state check for this simple startup test, OR mock the state manager.
        
        # Better: Just check if components are loaded
        if not orchestrator.world_sim or not orchestrator.campaign_director:
             raise Exception("Components not initialized")
             
        print(f"Iteration {iteration}: Success    ")
        return True, None
    except Exception as e:
        print(f"Iteration {iteration}: FAILED - {e}")
        logging.exception(f"Iteration {iteration} Failed")
        return False, str(e)

async def main():
    iterations = 20 # 20 is enough to catch race conditions usually
    failures = 0
    
    print(f"Starting Stress Test ({iterations} iterations)...")
    
    for i in range(1, iterations + 1):
        success, error = await run_initialization_test(i)
        if not success:
            failures += 1
            
        # Small delay to let resources cleanup
        await asyncio.sleep(0.1)
        
    print("\n" + "="*30)
    print(f"Test Complete.")
    print(f"Total Iterations: {iterations}")
    print(f"Successes: {iterations - failures}")
    print(f"Failures: {failures}")
    print("="*30)
    
    if failures > 0:
        print("Check stress_test.log for details.")
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest Cancelled.")
