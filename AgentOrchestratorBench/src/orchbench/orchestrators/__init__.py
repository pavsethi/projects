"""Orchestrators: the systems under test.

Each implements :class:`~orchbench.orchestrators.base.Orchestrator` -- given a
:class:`~orchbench.types.Task`, produce the tool call(s) it would route to. The
hand-rolled orchestrator is the reference/centerpiece; the LangGraph and Agent
Framework adapters are optional and import-guarded.
"""

from orchbench.orchestrators.base import Orchestrator
from orchbench.orchestrators.handrolled import HandRolledOrchestrator

#: Registry of orchestrators that need no optional dependencies.
BUILTIN = {
    "handrolled": HandRolledOrchestrator,
}

__all__ = ["Orchestrator", "HandRolledOrchestrator", "BUILTIN"]
