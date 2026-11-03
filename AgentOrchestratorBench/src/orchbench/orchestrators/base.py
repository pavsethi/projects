"""The orchestrator interface.

An orchestrator is anything that, given a task and a provider, decides which
tool(s) to call. That is deliberately the *only* thing the harness asks of it,
so a 30-line hand-rolled router and a full LangGraph state machine are graded on
exactly equal terms.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from orchbench.backends.base import ToolBackend
from orchbench.providers.base import LLMProvider
from orchbench.types import OrchestratorOutput, Scenario, Task, Trajectory


@runtime_checkable
class Orchestrator(Protocol):
    """Produce tool call(s) for a task."""

    #: Name surfaced in results (e.g. "handrolled", "langgraph").
    name: str

    #: Model id passed through to the provider and recorded with results.
    model: str

    async def route(self, task: Task, provider: LLMProvider) -> OrchestratorOutput:
        """Return the orchestrator's chosen call(s), with token/latency usage.

        Must not raise for model/provider errors: capture them in
        ``OrchestratorOutput.error`` so the sweep continues and the runner can
        classify the failure.
        """
        ...


@runtime_checkable
class EpisodeOrchestrator(Protocol):
    """Run a multi-turn scenario to completion over a shared provider + backend.

    The contract (enforced by a conformance test): same prompt/tools/backend/
    max_turns across orchestrators (prompt parity extended to the loop), one
    :class:`~orchbench.types.TurnRecord` per step, provider/backend errors
    captured in the trajectory rather than raised. Within that, each orchestrator
    uses its native loop -- which is where frameworks actually diverge.
    """

    name: str
    model: str

    async def run_episode(
        self, scenario: Scenario, provider: LLMProvider, backend: ToolBackend
    ) -> Trajectory: ...
