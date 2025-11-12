Modular Monolith scaffold
=========================

This folder contains a minimal scaffold for a modular-monolith architecture
for the TTRPG engine. It demonstrates:

- an in-process async event bus (`event_bus.py`)
- an orchestrator (`orchestrator.py`) which retains global state and publishes events
- a shared kernel (`shared.py`) containing canonical dataclasses
- small stub modules (`modules/narrative.py`, `modules/combat.py`) and a registrar
- a `start_monolith.py` runner to exercise wiring

Next steps:

- expand the `shared` datamodels to match project DTOs
- migrate existing services (rules_engine, story_engine, world_engine) into modules
- implement robust event routing, filtering, and prioritized handlers
- add unit/integration tests for each module and orchestrator
