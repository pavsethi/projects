"""Orchestrators: the systems under test.

Each implements :class:`~orchbench.orchestrators.base.Orchestrator` -- given a
:class:`~orchbench.types.Task`, produce the tool call(s) it would route to. The
hand-rolled orchestrator is the reference/centerpiece and needs no extra deps;
the LangGraph and Agent Framework adapters are optional and imported lazily so
their heavy dependencies aren't required to use the harness.
"""

from __future__ import annotations

import importlib

from orchbench.orchestrators.base import Orchestrator
from orchbench.orchestrators.handrolled import HandRolledOrchestrator

#: Orchestrators with no optional dependencies (always constructible).
BUILTIN = {
    "handrolled": HandRolledOrchestrator,
}

#: Optional adapters, as ``name -> (module, class)`` imported on demand. Each
#: raises a clear ImportError at construction if its extra isn't installed.
_OPTIONAL = {
    "langgraph": ("orchbench.orchestrators.langgraph_adapter", "LangGraphOrchestrator"),
    "agentframework": (
        "orchbench.orchestrators.agentframework_adapter",
        "AgentFrameworkOrchestrator",
    ),
}

#: Every orchestrator name the CLI recognises (installed or not).
ALL_NAMES = [*BUILTIN, *_OPTIONAL]


def get_orchestrator(name: str, **kwargs: object) -> Orchestrator:
    """Construct an orchestrator by name (raises ImportError if its extra is missing)."""
    if name in BUILTIN:
        return BUILTIN[name](**kwargs)  # type: ignore[arg-type]
    if name in _OPTIONAL:
        module, cls = _OPTIONAL[name]
        return getattr(importlib.import_module(module), cls)(**kwargs)
    raise ValueError(f"unknown orchestrator {name!r}; known: {ALL_NAMES}")


def available_orchestrators() -> list[str]:
    """Names that can actually be constructed right now (extras installed)."""
    names = list(BUILTIN)
    for name in _OPTIONAL:
        try:
            get_orchestrator(name)
        except ImportError:
            continue
        names.append(name)
    return names


__all__ = [
    "Orchestrator",
    "HandRolledOrchestrator",
    "BUILTIN",
    "ALL_NAMES",
    "get_orchestrator",
    "available_orchestrators",
]
