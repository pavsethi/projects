"""Backend registry."""

from __future__ import annotations

from typing import Any

from orchbench.backends.base import ToolBackend
from orchbench.backends.bfcl import BFCLBackend
from orchbench.backends.bfcl import oracle_plan as _bfcl_oracle
from orchbench.backends.records import TOOLS as RECORDS_TOOLS
from orchbench.backends.records import RecordsBackend
from orchbench.backends.records import oracle_plan as _records_oracle
from orchbench.types import PredictedCall, ToolSpec

_BACKENDS: dict[str, type] = {
    "records": RecordsBackend,
    "bfcl": BFCLBackend,
}

_DEFAULT_TOOLS = {
    "records": RECORDS_TOOLS,
}

_ORACLES = {
    "records": _records_oracle,
    "bfcl": _bfcl_oracle,
}


def get_backend(name: str) -> ToolBackend:
    """Construct a fresh backend by registry name."""
    if name not in _BACKENDS:
        raise ValueError(f"unknown backend {name!r}; known: {list(_BACKENDS)}")
    return _BACKENDS[name]()


def default_tools(name: str) -> list[ToolSpec]:
    """The tool schemas a backend exposes (used when a scenario omits them)."""
    return list(_DEFAULT_TOOLS.get(name, []))


def oracle_plan(scenario: Any) -> list[list[PredictedCall]]:
    """A correct per-turn call plan for a scenario (zero-key mock path only)."""
    oracle = _ORACLES.get(scenario.backend)
    if oracle is None:
        raise ValueError(f"no oracle for backend {scenario.backend!r}")
    return oracle(scenario)


__all__ = ["ToolBackend", "get_backend", "default_tools", "oracle_plan"]
