"""Monolith package entry for the TTRPG engine.

Small collection of modules that compose a modular monolith. This is a
starting scaffold: an event bus, orchestrator, shared kernel, and sample
modules. Expand iteratively—each module should expose clear interfaces
and register itself with the orchestrator/event bus.
"""

from . import event_bus, orchestrator, shared, modules

__all__ = ["event_bus", "orchestrator", "shared", "modules"]
