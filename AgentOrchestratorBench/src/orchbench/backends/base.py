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
        """Whether the state satisfies the scenario's goal predicate.

        Checked after every tool step (a True stops the episode early) and once
        at the end. A backend graded per user turn (BFCL) returns False until
        the final user turn has been checked.
        """
        ...

    def end_user_turn(self, turn: int) -> None:
        """Called when the model finishes a scripted user turn (stops calling).

        Per-turn checkers grade here (BFCL replays that turn's ground truth and
        compares state and responses). Single-check backends do nothing.
        """
        ...

    def grade_detail(self) -> dict:
        """Backend-specific grading detail for the trajectory ({} if none)."""
        ...
