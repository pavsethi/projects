"""Shared episode driver.

The multi-turn loop is identical for every orchestrator that doesn't bring its
own control flow. For each scripted user turn: deliver the user message, then
model -> tools -> model until the model stops calling tools (that ends the user
turn), the goal is reached, a provider error occurs, or the per-turn step cap is
hit (which aborts the episode, like BFCL's force-quit). Each orchestrator
supplies only the per-step *model call* (a :class:`StepResult`); the driver owns
the loop, tool execution, history, turn records, and grading -- so hand-rolled
and framework adapters stay at prompt+loop parity. LangGraph brings its own
graph and does not use this driver (that is the point of comparing it).

History uses native tool-call structure (assistant ``tool_calls`` + a ``tool``
results message, see ``orchestrators/prompt.py``); providers map it to their
own format (Anthropic ``tool_use`` / ``tool_result`` blocks).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from orchbench.backends.base import ToolBackend
from orchbench.failures import classify_trajectory
from orchbench.orchestrators.prompt import (
    assign_call_ids,
    assistant_message,
    episode_opening,
    tool_results_message,
    tool_to_schema,
    user_message,
)
from orchbench.types import ModelResponse, PredictedCall, Scenario, Trajectory, TurnRecord


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
    """One model step's output, produced by an orchestrator's native call path."""

    predicted: list[PredictedCall] = field(default_factory=list)
    text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    latency_ms: float = 0.0
    error: str | None = None
    native: dict | None = None

    @classmethod
    def from_response(cls, response: ModelResponse, predicted: list[PredictedCall]) -> StepResult:
        return cls(
            predicted=predicted,
            text=response.text,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cache_read_tokens=response.cache_read_tokens,
            cache_write_tokens=response.cache_write_tokens,
            latency_ms=response.latency_ms,
            error=response.error,
            native=response.native,
        )


#: A per-step model call: (messages, tools, step_index) -> StepResult.
StepFn = Callable[[list[dict], list[dict], int], Awaitable[StepResult]]


def tools_for_turn(scenario: Scenario, base: list[dict], user_turn: int) -> list[dict]:
    """The tool list in force at ``user_turn`` (BFCL miss_func adds tools later)."""
    tools = list(base)
    for turn in sorted(scenario.tools_added):
        if turn <= user_turn:
            tools.extend(tool_to_schema(t) for t in scenario.tools_added[turn])
    return tools


def turn_record(sr: StepResult, step_index: int, user_turn: int) -> TurnRecord:
    return TurnRecord(
        index=step_index,
        user_turn=user_turn,
        text=sr.text,
        predicted=sr.predicted,
        prompt_tokens=sr.prompt_tokens,
        completion_tokens=sr.completion_tokens,
        cache_read_tokens=sr.cache_read_tokens,
        cache_write_tokens=sr.cache_write_tokens,
        latency_ms=sr.latency_ms,
        error=sr.error,
    )


def finish_trajectory(
    scenario: Scenario,
    backend: ToolBackend,
    *,
    name: str,
    model: str,
    provider_name: str,
    turns: list[TurnRecord],
    stop_reason: str,
    had_error: bool,
    recovered: bool,
) -> Trajectory:
    """Grade and package an episode (shared by the driver and LangGraph)."""
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
        grade_detail=backend.grade_detail(),
    )
    traj.failure_mode = classify_trajectory(traj, had_error=had_error, recovered=recovered)
    return traj


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
    """Run every user turn's model->tools loop, delegating model steps to ``step``."""
    backend.reset(scenario.initial_state)
    messages = episode_opening(scenario)
    turns: list[TurnRecord] = []
    stop_reason = "no_call"
    had_error = recovered = False
    step_index = 0

    for user_turn, text in enumerate(scenario.user_turns):
        turn_tools = tools_for_turn(scenario, tools, user_turn)
        messages = [*messages, user_message(text)]
        calling_steps = 0
        ended = "no_call"  # how this user turn ended
        while True:
            sr = await step(messages, turn_tools, step_index)
            sr.predicted = assign_call_ids(sr.predicted, step_index)
            rec = turn_record(sr, step_index, user_turn)
            step_index += 1
            turns.append(rec)
            if sr.error is not None:
                ended = "provider_error"
                break
            messages = [*messages, assistant_message(sr.text, sr.predicted, sr.native)]
            if not sr.predicted:
                break  # the model is done with this user turn

            results = [backend.execute(c) for c in sr.predicted]
            rec.results = results
            rec.state_snapshot = backend.state()
            if any(not r.ok for r in results):
                had_error = True
            elif had_error:
                recovered = True
            messages = [*messages, tool_results_message(sr.predicted, results)]

            if backend.goal_reached(scenario.goal):
                ended = "goal"
                break
            calling_steps += 1
            if calling_steps >= scenario.max_turns:
                ended = "max_turns"
                break

        stop_reason = ended
        if ended in ("provider_error", "max_turns"):
            break  # abort: remaining user turns never run (BFCL force-quit)
        backend.end_user_turn(user_turn)
        if ended == "goal":
            break

    return finish_trajectory(
        scenario,
        backend,
        name=name,
        model=model,
        provider_name=provider_name,
        turns=turns,
        stop_reason=stop_reason,
        had_error=had_error,
        recovered=recovered,
    )
