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
from orchbench.episode import StepResult, finish_trajectory, tools_for_turn, turn_record
from orchbench.orchestrators.prompt import (
    assign_call_ids,
    assistant_message,
    build_routing_messages,
    episode_opening,
    tool_results_message,
    tool_to_schema,
    user_message,
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
    """State carried around the multi-turn graph (and across user turns)."""

    messages: list[dict]
    tools: list[dict]
    user_turn: int
    step_index: int
    calling_steps: int  # tool-calling steps within the current user turn
    turns: list[TurnRecord]
    last_calls: list[PredictedCall]
    had_error: bool
    recovered: bool
    ended: str  # "" while running; else how the current user turn ended


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
        """Run the episode as a real LangGraph graph: agent <-> tools per user turn.

        LangGraph owns the control flow within a user turn -- an ``agent`` node
        and a ``tools`` node joined by conditional edges, looping until the model
        stops calling tools, the goal is reached, or the per-turn step cap is
        hit. Each scripted user turn is one graph invocation over the carried
        state (how a LangGraph chat app handles a new user message). The agent
        node stamps ``step_index`` from graph state into the request metadata, so
        the shared provider is driven exactly as for the other orchestrators.
        """
        from langgraph.graph import END, START, StateGraph

        backend.reset(scenario.initial_state)
        base_tools = [tool_to_schema(t) for t in scenario.tools]

        async def agent(state: _EpisodeState) -> dict:
            si, ut = state["step_index"], state["user_turn"]
            response = await provider.complete(
                LLMRequest(
                    model=self.model,
                    messages=state["messages"],
                    tools=state["tools"],
                    metadata={"task_id": scenario.id, "turn": si},
                )
            )
            sr = StepResult.from_response(response, list(response.tool_calls))
            sr.predicted = assign_call_ids(sr.predicted, si)
            rec = turn_record(sr, si, ut)
            update: dict = {"turns": [*state["turns"], rec], "step_index": si + 1}
            if sr.error is not None:
                return {**update, "ended": "provider_error"}
            update["messages"] = [
                *state["messages"],
                assistant_message(sr.text, sr.predicted, sr.native),
            ]
            if not sr.predicted:
                return {**update, "ended": "no_call"}
            return {**update, "last_calls": sr.predicted}

        def tools_node(state: _EpisodeState) -> dict:
            calls = state["last_calls"]
            results = [backend.execute(c) for c in calls]
            rec = state["turns"][-1].model_copy(
                update={"results": results, "state_snapshot": backend.state()}
            )
            had_error = state["had_error"]
            recovered = state["recovered"]
            if any(not r.ok for r in results):
                had_error = True
            elif had_error:
                recovered = True
            calling_steps = state["calling_steps"] + 1
            ended = ""
            if backend.goal_reached(scenario.goal):
                ended = "goal"
            elif calling_steps >= scenario.max_turns:
                ended = "max_turns"
            return {
                "turns": [*state["turns"][:-1], rec],
                "messages": [*state["messages"], tool_results_message(calls, results)],
                "calling_steps": calling_steps,
                "had_error": had_error,
                "recovered": recovered,
                "ended": ended,
            }

        def route(state: _EpisodeState) -> str:
            return END if state["ended"] else "next"

        graph: Any = StateGraph(_EpisodeState)
        graph.add_node("agent", agent)
        graph.add_node("tools", tools_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", route, {"next": "tools", END: END})
        graph.add_conditional_edges("tools", route, {"next": "agent", END: END})
        app = graph.compile()

        state: _EpisodeState = {
            "messages": episode_opening(scenario),
            "step_index": 0,
            "turns": [],
            "last_calls": [],
            "had_error": False,
            "recovered": False,
        }
        stop_reason = "no_call"
        for user_turn, text in enumerate(scenario.user_turns):
            state = {
                **state,
                "messages": [*state["messages"], user_message(text)],
                "tools": tools_for_turn(scenario, base_tools, user_turn),
                "user_turn": user_turn,
                "calling_steps": 0,
                "ended": "",
            }
            state = await app.ainvoke(state, config={"recursion_limit": scenario.max_turns * 2 + 6})
            stop_reason = state["ended"]
            if stop_reason in ("provider_error", "max_turns"):
                break
            backend.end_user_turn(user_turn)
            if stop_reason == "goal":
                break

        return finish_trajectory(
            scenario,
            backend,
            name=self.name,
            model=self.model,
            provider_name=getattr(provider, "name", "provider"),
            turns=state["turns"],
            stop_reason=stop_reason,
            had_error=state["had_error"],
            recovered=state["recovered"],
        )
