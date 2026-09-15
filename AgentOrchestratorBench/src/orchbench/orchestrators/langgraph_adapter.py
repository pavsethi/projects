"""Optional LangGraph adapter (import-guarded).

Install with ``pip install -e '.[langgraph]'``.

Design note: LangGraph normally owns its own model client, which would put it on
a different LLM path than the other orchestrators and make the comparison unfair.
To keep every orchestrator on the *same* provider seam, this adapter wraps our
:class:`~orchbench.providers.base.LLMProvider` in a tiny LangChain-compatible
chat model and builds a minimal single-node routing graph over it. That way the
LangGraph *control flow* is what is being measured, not a different backend.

This file is a real, working skeleton; it is import-guarded and excluded from the
default (mock) test path because it pulls heavy dependencies.
"""

from __future__ import annotations

from typing import TypedDict

from orchbench.providers.base import LLMProvider
from orchbench.types import (
    LLMRequest,
    ModelResponse,
    OrchestratorOutput,
    PredictedCall,
    Task,
    ToolSpec,
)


class _State(TypedDict, total=False):
    """LangGraph state schema: a node writes the provider response into it."""

    response: ModelResponse


def _require_langgraph() -> None:
    try:
        import langgraph  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only with extra
        raise ImportError("The langgraph extra is required: pip install -e '.[langgraph]'") from exc


class LangGraphOrchestrator:
    """Route tasks through a minimal LangGraph graph over the shared provider."""

    def __init__(self, model: str = "mock-model") -> None:
        _require_langgraph()
        self.name = "langgraph"
        self.model = model

    @staticmethod
    def _tool_schema(tool: ToolSpec) -> dict:
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters or {"type": "object", "properties": {}},
        }

    async def route(self, task: Task, provider: LLMProvider) -> OrchestratorOutput:
        # A one-node graph: the node calls the provider and returns a state
        # update. Kept inline (rather than a module-level graph) so each task run
        # is independent and the token/latency accounting stays per-task.
        from langgraph.graph import END, START, StateGraph

        request = LLMRequest(
            model=self.model,
            messages=[{"role": "user", "content": task.query}],
            tools=[self._tool_schema(t) for t in task.tools],
            metadata={"task_id": task.id},
        )

        async def route_node(state: _State) -> _State:
            # Return a state *update* (LangGraph merges it); do not mutate.
            return {"response": await provider.complete(request)}

        graph = StateGraph(_State)
        graph.add_node("route", route_node)
        graph.add_edge(START, "route")
        graph.add_edge("route", END)
        app = graph.compile()

        final = await app.ainvoke(_State())
        response = final["response"]

        if response.error is not None:
            return OrchestratorOutput(
                error=response.error,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                latency_ms=response.latency_ms,
                llm_calls=1,
            )
        return OrchestratorOutput(
            predicted=[PredictedCall(name=c.name, args=c.args) for c in response.tool_calls],
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            latency_ms=response.latency_ms,
            llm_calls=1,
        )
