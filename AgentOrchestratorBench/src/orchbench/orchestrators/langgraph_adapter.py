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

from typing import Any, TypedDict

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
    ModelResponse,
    OrchestratorOutput,
    PredictedCall,
    Scenario,
    Task,
    Trajectory,
    TurnRecord,
)


class _State(TypedDict, total=False):
    """LangGraph state schema: a node writes the provider response into it."""

    response: ModelResponse


class _EpisodeState(TypedDict, total=False):
    """State carried around the multi-turn graph loop."""

    messages: list[dict]
    turn_index: int
    turns: list[TurnRecord]
    last_calls: list[PredictedCall]
    stop_reason: str
    had_error: bool
    recovered: bool
    done: bool


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

    def _build_request(self, task: Task) -> LLMRequest:
        # Identical prompt to every other orchestrator (prompt parity).
        return LLMRequest(
            model=self.model,
            messages=build_routing_messages(task),
            tools=[tool_to_schema(t) for t in task.tools],
            metadata={"task_id": task.id},
        )

    async def route(self, task: Task, provider: LLMProvider) -> OrchestratorOutput:
        # A one-node graph: the node calls the provider and returns a state
        # update. Kept inline (rather than a module-level graph) so each task run
        # is independent and the token/latency accounting stays per-task.
        from langgraph.graph import END, START, StateGraph

        request = self._build_request(task)

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

    async def run_episode(
        self, scenario: Scenario, provider: LLMProvider, backend: ToolBackend
    ) -> Trajectory:
        """Run the episode as a real LangGraph graph: agent <-> tools until done.

        Unlike the shared driver, LangGraph owns the control flow here -- an
        ``agent`` node and a ``tools`` node with a conditional edge that loops
        until the model stops calling tools, the goal is reached, or ``max_turns``
        is hit. The agent node reads ``turn_index`` from graph state and stamps it
        into the request metadata, so the shared (mock or real) provider is driven
        exactly as for every other orchestrator -- the loop is what differs.
        """
        from langgraph.graph import END, START, StateGraph

        backend.reset(scenario.initial_state)
        tools = [tool_to_schema(t) for t in scenario.tools]
        opening = build_episode_messages(scenario)

        async def agent(state: _EpisodeState) -> dict:
            ti = state["turn_index"]
            response = await provider.complete(
                LLMRequest(
                    model=self.model,
                    messages=state["messages"],
                    tools=tools,
                    metadata={"task_id": scenario.id, "turn": ti},
                )
            )
            rec = TurnRecord(
                index=ti,
                text=response.text,
                predicted=list(response.tool_calls),
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                latency_ms=response.latency_ms,
            )
            if response.error is not None:
                rec.error = response.error
                return {
                    "turns": [*state["turns"], rec],
                    "done": True,
                    "stop_reason": "provider_error",
                }
            if not response.tool_calls:
                return {"turns": [*state["turns"], rec], "done": True, "stop_reason": "no_call"}
            return {"turns": [*state["turns"], rec], "last_calls": list(response.tool_calls)}

        def tools_node(state: _EpisodeState) -> dict:
            calls = state["last_calls"]
            results = [backend.execute(c) for c in calls]
            rec = state["turns"][-1].model_copy(
                update={"results": results, "state_snapshot": backend.state()}
            )
            turns = [*state["turns"][:-1], rec]
            had_error = state.get("had_error", False)
            recovered = state.get("recovered", False)
            if any(not r.ok for r in results):
                had_error = True
            elif had_error:
                recovered = True
            messages = [
                *state["messages"],
                {"role": "assistant", "content": calls_to_text(calls)},
                {"role": "user", "content": results_to_text(results)},
            ]
            ti = state["turn_index"] + 1
            done = backend.goal_reached(scenario.goal) or ti >= scenario.max_turns
            stop = "goal" if backend.goal_reached(scenario.goal) else "max_turns"
            return {
                "turns": turns,
                "messages": messages,
                "turn_index": ti,
                "had_error": had_error,
                "recovered": recovered,
                "done": done,
                "stop_reason": stop if done else "",
            }

        def after_agent(state: _EpisodeState) -> str:
            return END if state.get("done") else "tools"

        def after_tools(state: _EpisodeState) -> str:
            return END if state.get("done") else "agent"

        graph: Any = StateGraph(_EpisodeState)
        graph.add_node("agent", agent)
        graph.add_node("tools", tools_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", after_agent, {"tools": "tools", END: END})
        graph.add_conditional_edges("tools", after_tools, {"agent": "agent", END: END})
        app = graph.compile()

        init: _EpisodeState = {
            "messages": opening,
            "turn_index": 0,
            "turns": [],
            "last_calls": [],
            "had_error": False,
            "recovered": False,
            "done": False,
            "stop_reason": "max_turns",
        }
        final = await app.ainvoke(init, config={"recursion_limit": scenario.max_turns * 2 + 4})

        succeeded = backend.goal_reached(scenario.goal)
        turns = final["turns"]
        traj = Trajectory(
            scenario_id=scenario.id,
            suite=scenario.suite,
            category=scenario.category,
            orchestrator=self.name,
            provider=getattr(provider, "name", "provider"),
            model=self.model,
            turns=turns,
            succeeded=succeeded,
            stop_reason="goal" if succeeded else final.get("stop_reason", "max_turns"),
            turns_to_success=len(turns) if succeeded else None,
            final_state=backend.state(),
        )
        traj.failure_mode = classify_trajectory(
            traj, had_error=final.get("had_error", False), recovered=final.get("recovered", False)
        )
        return traj
