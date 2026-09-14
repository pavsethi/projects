"""Grading: compare predicted tool calls against a task's ground truth.

We report two levels, deliberately kept separate because they answer different
questions:

* **routing accuracy** -- did the orchestrator select the right tool(s)?
  This is the headline "does it route correctly" metric and ignores argument
  values entirely.
* **exact accuracy** -- right tool(s) *and* every argument value is acceptable.

This is a simplified, transparent re-implementation of BFCL's AST checker. The
real checker has more machinery for nested types, enums and type coercion; the
simplifications we make are documented in ``METHODOLOGY.md`` so the numbers are
honest about what they do and don't capture.
"""

from __future__ import annotations

from orchbench.failures import classify
from orchbench.types import GradeResult, GroundTruthCall, OrchestratorOutput, PredictedCall, Task

# Sentinel used in ground-truth arg lists to mark a parameter as optional: if
# "" is an acceptable value, the model is allowed to omit the parameter.
OPTIONAL = ""


def _arg_matches(predicted_value: object, acceptable: list[object]) -> bool:
    """A predicted value is acceptable if it equals any allowed value.

    Comparison is intentionally lenient about numeric string-vs-number
    mismatches (``"5"`` vs ``5``) because function-calling models routinely
    stringify numbers; everything else must match by value.
    """
    for allowed in acceptable:
        if predicted_value == allowed:
            return True
        # Tolerate str/number coercion in both directions.
        if isinstance(allowed, (int, float)) and not isinstance(allowed, bool):
            try:
                if float(predicted_value) == float(allowed):  # type: ignore[arg-type]
                    return True
            except (TypeError, ValueError):
                pass
    return False


def _one_call_matches(pred: PredictedCall, truth: GroundTruthCall) -> bool:
    """Exact match for a single call: names equal and every param satisfied."""
    if pred.name != truth.name:
        return False
    for param, acceptable in truth.args.items():
        if param not in pred.args:
            # Omission is fine only if the parameter is optional.
            if OPTIONAL in acceptable:
                continue
            return False
        if not _arg_matches(pred.args[param], acceptable):
            return False
    # Reject arguments the ground truth never mentions (hallucinated params),
    # unless the model merely re-supplied an optional default.
    for param in pred.args:
        if param not in truth.args:
            return False
    return True


def _names(calls: list) -> list[str]:
    return sorted(c.name for c in calls)


def grade(predicted: list[PredictedCall], truth: list[GroundTruthCall]) -> tuple[bool, bool]:
    """Return ``(routing_correct, exact_correct)`` for a set of calls.

    Order-independent: BFCL's ``parallel`` category does not fix call order, so
    we match as multisets. Exact grading greedily pairs each ground-truth call
    with an as-yet-unused predicted call that satisfies it.
    """
    routing_correct = _names(predicted) == _names(truth)

    if not routing_correct:
        return False, False

    remaining = list(predicted)
    for t in truth:
        match_idx = next(
            (i for i, p in enumerate(remaining) if _one_call_matches(p, t)),
            None,
        )
        if match_idx is None:
            return True, False
        remaining.pop(match_idx)
    exact_correct = not remaining
    return routing_correct, exact_correct


def grade_output(task: Task, output: OrchestratorOutput) -> GradeResult:
    """Grade a full orchestrator output and attach a failure-mode label."""
    valid_tool_names = {tool.name for tool in task.tools}

    if output.error is not None:
        return GradeResult(
            routing_correct=False,
            exact_correct=False,
            failure_mode=classify(task, output, routing_correct=False, exact_correct=False),
            detail=output.error,
        )

    routing_correct, exact_correct = grade(output.predicted, task.ground_truth)
    failure_mode = classify(
        task,
        output,
        routing_correct=routing_correct,
        exact_correct=exact_correct,
        valid_tool_names=valid_tool_names,
    )
    detail = ""
    if not exact_correct:
        detail = (
            f"expected {[(c.name, c.args) for c in task.ground_truth]}, "
            f"got {[(c.name, c.args) for c in output.predicted]}"
        )
    return GradeResult(
        routing_correct=routing_correct,
        exact_correct=exact_correct,
        failure_mode=failure_mode,
        detail=detail,
    )
