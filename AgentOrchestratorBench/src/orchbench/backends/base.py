"""Tool backends: deterministic, in-process simulated worlds for multi-turn.

A backend is what makes multi-turn hermetic: tools return results from mutable
state with no network, clock, or randomness, so an episode is fully reproducible
and testable without API keys. See ``docs/multi-turn.md``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from orchbench.types import PredictedCall, ToolResult


@runtime_checkable
class ToolBackend(Protocol):
    """A stateful world an agent acts on over several turns."""

    #: Registry name, surfaced in trajectories.
    name: str

    def reset(self, initial_state: dict) -> None:
        """Load a scenario's starting state (called once per episode)."""
        ...

    def execute(self, call: PredictedCall) -> ToolResult:
        """Run one tool call against the state, mutating it, and return a result.

        Must never raise for bad input: return ``ToolResult(ok=False, error=...)``
        so the agent can recover (recovery is a first-class signal).
        """
        ...

    def state(self) -> dict:
        """A JSON-serialisable snapshot of current state (for the trajectory)."""
        ...

    def goal_reached(self, goal: dict) -> bool:
        """Whether the final state satisfies the scenario's goal predicate."""
        ...
