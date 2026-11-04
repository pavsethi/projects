"""Shared episode driver.

The multi-turn loop is identical for every orchestrator that doesn't bring its
own control flow: reset the backend, deliver the instruction, then
model -> tools -> model until the goal is reached, no tool is called, a provider
error occurs, or ``max_turns`` is hit. Each orchestrator supplies only the
per-turn *model call* (a :class:`StepResult`); the driver owns the loop, tool
execution, turn records, and grading -- so hand-rolled and framework adapters
stay at prompt+loop parity. LangGraph brings its own graph and does not use this
driver (that is the point of comparing it).

v0.2 scope: one user instruction then an autonomous tool loop (multi-turn *tool
use*). Multi-turn user conversations (a user simulator) are v0.3 -- see
docs/multi-turn.md.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from orchbench.backends.base import ToolBackend
from orchbench.failures import classify_trajectory
from orchbench.orchestrators.prompt import build_episode_messages, calls_to_text, results_to_text
from orchbench.types import PredictedCall, Scenario, Trajectory, TurnRecord


def summarize_goal(scenario: Scenario) -> str:
    """A plain-language one-liner for a scenario's goal (best-effort, backend-aware).

    Handles the ``records`` backend's ``field_equals`` shape (naming records by
    their human name when present); falls back to the raw goal for others.
    """
    clauses = scenario.goal.get("field_equals")
    if not clauses:
        return str(scenario.goal) if scenario.goal else ""
    records = scenario.initial_state.get("records", {})
    parts = []
    for c in clauses:
        name = records.get(c["record"], {}).get("name", c["record"])
        parts.append(f'"{name}" → {c["field"]} = {c["value"]}')
    return "; ".join(parts)


@dataclass
class StepResult:
    """One model turn's output, produced by an orchestrator's native call path."""

    predicted: list[PredictedCall] = field(default_factory=list)
    text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    error: str | None = None


#: A per-turn model call: (messages, tools, turn_index) -> StepResult.
StepFn = Callable[[list[dict], list[dict], int], Awaitable[StepResult]]


async def drive_episode(
    scenario: Scenario,
    backend: ToolBackend,
    *,
    name: str,
    model: str,
    provider_name: str,
    step: StepFn,
    tools: list[dict],
) -> Trajectory:
    """Run the canonical model->tools loop, delegating each model turn to ``step``."""
    backend.reset(scenario.initial_state)
    messages = build_episode_messages(scenario)
    turns: list[TurnRecord] = []
    stop_reason = "max_turns"
    had_error = False
    recovered = False

    for turn_index in range(scenario.max_turns):
        sr = await step(messages, tools, turn_index)
        rec = TurnRecord(
            index=turn_index,
            text=sr.text,
            predicted=sr.predicted,
            prompt_tokens=sr.prompt_tokens,
            completion_tokens=sr.completion_tokens,
            latency_ms=sr.latency_ms,
        )
        if sr.error is not None:
            rec.error = sr.error
            turns.append(rec)
            stop_reason = "provider_error"
            break
        if not sr.predicted:
            turns.append(rec)
            stop_reason = "no_call"
            break

        results = [backend.execute(c) for c in sr.predicted]
        rec.results = results
        rec.state_snapshot = backend.state()
        turns.append(rec)

        if any(not r.ok for r in results):
            had_error = True
        elif had_error:
            recovered = True

        messages = [
            *messages,
            {"role": "assistant", "content": calls_to_text(sr.predicted)},
            {"role": "user", "content": results_to_text(results)},
        ]
        if backend.goal_reached(scenario.goal):
            stop_reason = "goal"
            break

    succeeded = backend.goal_reached(scenario.goal)
    traj = Trajectory(
        scenario_id=scenario.id,
        suite=scenario.suite,
        category=scenario.category,
        orchestrator=name,
        provider=provider_name,
        model=model,
        turns=turns,
        succeeded=succeeded,
        stop_reason="goal" if succeeded else stop_reason,
        turns_to_success=len(turns) if succeeded else None,
        final_state=backend.state(),
    )
    traj.failure_mode = classify_trajectory(traj, had_error=had_error, recovered=recovered)
    return traj
