"""Multi-user-turn episodes: turn flow, per-turn tools, step caps, and parity.

The driver (hand-rolled, Agent Framework) and LangGraph's own graph must agree
step for step: same requests to the provider, same trajectory shape.
"""

import importlib.util

import pytest

from orchbench.backends import default_tools, get_backend
from orchbench.backends.records import RecordsBackend
from orchbench.providers.mock import MockProvider, build_episode_fixtures
from orchbench.types import FailureMode, LLMRequest, ModelResponse, PredictedCall, Scenario


def _orchestrators():
    from orchbench.orchestrators.handrolled import HandRolledOrchestrator

    orchs = [HandRolledOrchestrator(model="mock-model")]
    if importlib.util.find_spec("langgraph"):
        from orchbench.orchestrators.langgraph_adapter import LangGraphOrchestrator

        orchs.append(LangGraphOrchestrator(model="mock-model"))
    if importlib.util.find_spec("agent_framework"):
        from orchbench.orchestrators.agentframework_adapter import AgentFrameworkOrchestrator

        orchs.append(AgentFrameworkOrchestrator(model="mock-model"))
    return orchs


ORCHS = _orchestrators()


def _update(rid, value):
    return PredictedCall(
        name="update_record", args={"record_id": rid, "field": "status", "value": value}
    )


SEARCH = PredictedCall(name="search_records", args={"query": "alice"})


def _two_turn_scenario(**kw) -> Scenario:
    kw.setdefault("tools", default_tools("records"))
    return Scenario(
        id="two_turns",
        backend="records",
        user_turns=["Ship Alice's order.", "Now ship Bob's order too."],
        initial_state={
            "records": {
                "r1": {"name": "Alice order", "status": "pending"},
                "r2": {"name": "Bob order", "status": "pending"},
            }
        },
        goal={
            "field_equals": [
                {"record": "r1", "field": "status", "value": "shipped"},
                {"record": "r2", "field": "status", "value": "shipped"},
            ]
        },
        **kw,
    )


# Step plan: turn 0 = search, update r1, then stop (no call); turn 1 = update r2.
PLAN = [[SEARCH], [_update("r1", "shipped")], [], [_update("r2", "shipped")]]


class _Recording:
    """Wraps a provider and records every request it receives."""

    name = "recording"

    def __init__(self, inner):
        self.inner = inner
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> ModelResponse:
        self.requests.append(request)
        return await self.inner.complete(request)


class _SpyBackend(RecordsBackend):
    def __init__(self):
        super().__init__()
        self.ended_turns: list[int] = []

    def end_user_turn(self, turn: int) -> None:
        self.ended_turns.append(turn)


@pytest.mark.parametrize("orch", ORCHS, ids=lambda o: o.name)
async def test_two_user_turns_run_in_order(orch):
    s = _two_turn_scenario()
    backend = _SpyBackend()
    provider = MockProvider(build_episode_fixtures(s.id, PLAN))
    traj = await orch.run_episode(s, provider, backend)
    assert traj.succeeded and traj.stop_reason == "goal"
    assert [t.user_turn for t in traj.turns] == [0, 0, 0, 1]
    # Turn 0 ended normally (model stopped); turn 1 ended on the goal.
    assert backend.ended_turns == [0, 1]
    # Every call got a stable id (the mock provider assigns none).
    assert traj.turns[0].predicted[0].id == "call_0_0"


@pytest.mark.parametrize("orch", ORCHS, ids=lambda o: o.name)
async def test_second_instruction_follows_tool_results(orch):
    s = _two_turn_scenario()
    rec = _Recording(MockProvider(build_episode_fixtures(s.id, PLAN)))
    await orch.run_episode(s, rec, get_backend("records"))
    roles = [m["role"] for m in rec.requests[3].messages]
    # system, user, assistant(call), tool, assistant(call), tool, assistant(stop), user
    assert roles == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
        "tool",
        "assistant",
        "user",
    ]
    assert rec.requests[3].messages[-1]["content"] == "Now ship Bob's order too."
    tool_msg = rec.requests[3].messages[3]
    assert tool_msg["results"][0]["id"] == "call_0_0"


async def test_all_orchestrators_send_identical_episode_requests():
    """Episode-path prompt parity: byte-identical request sequences."""
    if len(ORCHS) < 2:
        pytest.skip("needs at least one framework adapter installed")
    s = _two_turn_scenario()
    seen = []
    for orch in ORCHS:
        rec = _Recording(MockProvider(build_episode_fixtures(s.id, PLAN)))
        await orch.run_episode(s, rec, get_backend("records"))
        seen.append([r.model_dump() for r in rec.requests])
    assert all(x == seen[0] for x in seen[1:])


@pytest.mark.parametrize("orch", ORCHS, ids=lambda o: o.name)
async def test_tools_added_at_a_later_user_turn(orch):
    tools = default_tools("records")
    update = next(t for t in tools if t.name == "update_record")
    s = _two_turn_scenario(
        tools=[t for t in tools if t.name != "update_record"], tools_added={1: [update]}
    )
    plan = [[SEARCH], [], [_update("r1", "shipped")], [_update("r2", "shipped")]]
    rec = _Recording(MockProvider(build_episode_fixtures(s.id, plan)))
    await orch.run_episode(s, rec, get_backend("records"))
    names = [{t["name"] for t in r.tools} for r in rec.requests]
    assert "update_record" not in names[0] and "update_record" not in names[1]
    assert "update_record" in names[2]


@pytest.mark.parametrize("orch", ORCHS, ids=lambda o: o.name)
async def test_per_turn_step_cap_aborts_remaining_turns(orch):
    s = _two_turn_scenario(max_turns=2)
    plan = [[SEARCH], [SEARCH], [SEARCH]]  # never stops calling in turn 0
    backend = _SpyBackend()
    traj = await orch.run_episode(s, MockProvider(build_episode_fixtures(s.id, plan)), backend)
    assert not traj.succeeded
    assert traj.stop_reason == "max_turns"
    assert len(traj.turns) == 2  # capped at 2 calling steps
    assert backend.ended_turns == []  # turn 0 never completed; turn 1 never ran
    assert all(t.user_turn == 0 for t in traj.turns)


@pytest.mark.parametrize("orch", ORCHS, ids=lambda o: o.name)
async def test_provider_error_mid_episode_stops_it(orch):
    s = _two_turn_scenario()

    class _FailSecond:
        name = "flaky"

        def __init__(self):
            self.n = 0

        async def complete(self, request: LLMRequest) -> ModelResponse:
            self.n += 1
            if self.n == 2:
                return ModelResponse(error="529 overloaded")
            return ModelResponse(tool_calls=[SEARCH])

    traj = await orch.run_episode(s, _FailSecond(), get_backend("records"))
    assert traj.stop_reason == "provider_error"
    assert traj.failure_mode == FailureMode.PROVIDER_ERROR
    assert traj.turns[-1].error == "529 overloaded"
