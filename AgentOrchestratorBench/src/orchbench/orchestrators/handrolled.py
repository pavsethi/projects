"""The hand-rolled orchestrator -- the reference system under test.

This is intentionally *not* a wrapper around a framework: it is the "what does it
actually take to route tool calls yourself" baseline that the framework adapters
are measured against. It does the real work a framework hides -- render tool
schemas into a prompt, call the model, parse a function-calling response,
recover from a malformed one, and account for tokens/latency across retries.

It handles two response shapes so it works against both real function-calling
APIs (structured ``tool_calls``) and models that only emit text (a JSON block we
parse out), which is exactly the portability the harness is meant to reward.
"""

from __future__ import annotations

import json
import re

from orchbench.backends.base import ToolBackend
from orchbench.failures import classify_trajectory
from orchbench.orchestrators.prompt import (
    build_episode_messages,
    build_routing_messages,
    calls_to_text,
    results_to_text,
    tool_to_schema,
)
from orchbench.providers.base import LLMProvider
from orchbench.types import (
    LLMRequest,
    OrchestratorOutput,
    PredictedCall,
    Scenario,
    Task,
    Trajectory,
    TurnRecord,
)

# Matches the first JSON array or object in a block of text (fallback parsing).
_JSON_BLOCK = re.compile(r"(\[.*\]|\{.*\})", re.DOTALL)


def _parse_text_fallback(text: str) -> list[PredictedCall]:
    """Best-effort extraction of tool calls from a plain-text response."""
    match = _JSON_BLOCK.search(text or "")
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    calls: list[PredictedCall] = []
    for item in data:
        if not isinstance(item, dict) or "name" not in item:
            continue
        args = item.get("arguments", item.get("args", {}))
        calls.append(
            PredictedCall(name=str(item["name"]), args=args if isinstance(args, dict) else {})
        )
    return calls


class HandRolledOrchestrator:
    """A minimal, dependency-free tool router with one retry on empty output."""

    def __init__(self, model: str = "mock-model", max_retries: int = 0) -> None:
        # Default 0: one call per task is the honest measurement. A retry that
        # re-prompts an empty response would force a tool call and destroy the
        # irrelevance signal (the model must be free to abstain), so retries are
        # opt-in and the nudge below never demands a call.
        self.name = "handrolled"
        self.model = model
        self.max_retries = max_retries

    def _build_request(self, task: Task, *, nudge: bool = False) -> LLMRequest:
        return LLMRequest(
            model=self.model,
            messages=build_routing_messages(task, nudge=nudge),
            tools=[tool_to_schema(t) for t in task.tools],
            metadata={"task_id": task.id},
        )

    async def route(self, task: Task, provider: LLMProvider) -> OrchestratorOutput:
        prompt_tokens = 0
        completion_tokens = 0
        latency_ms = 0.0
        llm_calls = 0
        last_error: str | None = None

        for attempt in range(self.max_retries + 1):
            request = self._build_request(task, nudge=attempt > 0)
            response = await provider.complete(request)

            llm_calls += 1
            prompt_tokens += response.prompt_tokens
            completion_tokens += response.completion_tokens
            latency_ms += response.latency_ms

            if response.error is not None:
                last_error = response.error
                # Provider errors are not fixable by re-prompting; stop.
                break

            predicted = response.tool_calls or _parse_text_fallback(response.text)
            if predicted:
                return OrchestratorOutput(
                    predicted=predicted,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    llm_calls=llm_calls,
                    raw={"attempts": attempt + 1},
                )
            last_error = None  # empty, not an error -- retry may recover it

        return OrchestratorOutput(
            predicted=[],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            llm_calls=llm_calls,
            error=last_error,
            raw={"attempts": llm_calls},
        )

    async def run_episode(
        self, scenario: Scenario, provider: LLMProvider, backend: ToolBackend
    ) -> Trajectory:
        """The reference multi-turn loop: an explicit model -> tools -> model cycle."""
        backend.reset(scenario.initial_state)
        messages = build_episode_messages(scenario)
        tools = [tool_to_schema(t) for t in scenario.tools]
        pending_user = list(scenario.user_turns[1:])  # first turn is in the opening messages

        turns: list[TurnRecord] = []
        stop_reason = "max_turns"
        had_error = False
        recovered = False

        for turn_index in range(scenario.max_turns):
            request = LLMRequest(
                model=self.model,
                messages=messages,
                tools=tools,
                metadata={"task_id": scenario.id, "turn": turn_index},
            )
            response = await provider.complete(request)
            rec = TurnRecord(
                index=turn_index,
                text=response.text,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                latency_ms=response.latency_ms,
            )

            if response.error is not None:
                rec.error = response.error
                turns.append(rec)
                stop_reason = "provider_error"
                break

            calls = response.tool_calls or _parse_text_fallback(response.text)
            rec.predicted = calls

            if not calls:
                turns.append(rec)
                if pending_user:  # model paused; deliver the next scripted user turn
                    messages = [
                        *messages,
                        {"role": "assistant", "content": response.text},
                        {"role": "user", "content": pending_user.pop(0)},
                    ]
                    continue
                stop_reason = "no_call"
                break

            results = [backend.execute(c) for c in calls]
            rec.results = results
            rec.state_snapshot = backend.state()
            turns.append(rec)

            if any(not r.ok for r in results):
                had_error = True
            elif had_error:
                recovered = True

            messages = [
                *messages,
                {"role": "assistant", "content": calls_to_text(calls)},
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
            orchestrator=self.name,
            provider=getattr(provider, "name", "provider"),
            model=self.model,
            turns=turns,
            succeeded=succeeded,
            stop_reason="goal" if succeeded else stop_reason,
            turns_to_success=len(turns) if succeeded else None,
            final_state=backend.state(),
        )
        traj.failure_mode = classify_trajectory(traj, had_error=had_error, recovered=recovered)
        return traj
