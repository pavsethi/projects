"""Failure-mode classification.

Given a task and an orchestrator's (graded) output, decide *why* it was wrong.
This taxonomy is the analytical heart of the harness: a leaderboard tells you
which orchestrator scored higher, but the failure-mode breakdown tells you
whether it lost to bad routing, mangled arguments, or provider flakiness --
which is what actually informs a migration decision.
"""

from __future__ import annotations

from collections import Counter

from orchbench.types import FailureMode, OrchestratorOutput, Task


def classify(
    task: Task,
    output: OrchestratorOutput,
    *,
    routing_correct: bool,
    exact_correct: bool,
    valid_tool_names: set[str] | None = None,
) -> FailureMode:
    """Assign a single, most-specific failure mode to one result."""
    if exact_correct:
        return FailureMode.NONE

    if output.error is not None:
        return FailureMode.PROVIDER_ERROR

    if not output.predicted:
        return FailureMode.EMPTY_RESPONSE

    valid = valid_tool_names if valid_tool_names is not None else {t.name for t in task.tools}
    if any(call.name not in valid for call in output.predicted):
        return FailureMode.HALLUCINATED_TOOL

    if routing_correct:
        # Right tools, so the only thing left is argument values.
        return FailureMode.WRONG_ARGS

    expected = Counter(c.name for c in task.ground_truth)
    got = Counter(c.name for c in output.predicted)

    if len(output.predicted) < len(task.ground_truth):
        return FailureMode.MISSING_CALL
    if len(output.predicted) > len(task.ground_truth):
        return FailureMode.EXTRA_CALL
    # Same count, valid tools, but the set is wrong.
    if got != expected:
        return FailureMode.WRONG_TOOL
    # Fallback: counts and names line up but grade() disagreed -- treat as args.
    return FailureMode.WRONG_ARGS


def summarize(modes: list[FailureMode]) -> dict[str, int]:
    """Count occurrences of each failure mode (stable, all keys present)."""
    counts = Counter(m.value for m in modes)
    return {mode.value: counts.get(mode.value, 0) for mode in FailureMode}
