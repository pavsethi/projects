"""Multi-turn engine tests: backend, episode loop, grading, metrics."""

import importlib.util
import pathlib

import pytest

from orchbench.backends import default_tools, get_backend, oracle_plan
from orchbench.metrics import aggregate_episodes
from orchbench.orchestrators.handrolled import HandRolledOrchestrator
from orchbench.providers.mock import MockProvider, build_episode_fixtures
from orchbench.runner import Runner
from orchbench.suites.multiturn import load_scenarios
from orchbench.types import (
    FailureMode,
    LLMRequest,
    ModelResponse,
    PredictedCall,
    Scenario,
    Trajectory,
)

SAMPLE = pathlib.Path(__file__).resolve().parents[1] / "data" / "multiturn_sample.jsonl"


def _records_scenario() -> Scenario:
    return Scenario(
        id="t",
        backend="records",
        tools=default_tools("records"),
        user_turns=["ship it"],
        initial_state={"records": {"r1": {"name": "Alice order", "status": "pending"}}},
        goal={"field_equals": [{"record": "r1", "field": "status", "value": "shipped"}]},
    )


# ----------------------------- backend --------------------------------------- #


def test_backend_search_get_update_and_goal():
    b = get_backend("records")
    b.reset({"records": {"r1": {"name": "Alice order", "status": "pending"}}})
    assert b.execute(PredictedCall(name="search_records", args={"query": "alice"})).content == [
        {"id": "r1", "name": "Alice order"}
    ]
    assert not b.goal_reached(
        {"field_equals": [{"record": "r1", "field": "status", "value": "shipped"}]}
    )
    ok = b.execute(
        PredictedCall(
            name="update_record", args={"record_id": "r1", "field": "status", "value": "shipped"}
        )
    )
    assert ok.ok
    assert b.goal_reached(
        {"field_equals": [{"record": "r1", "field": "status", "value": "shipped"}]}
    )


def test_backend_errors_do_not_raise():
    b = get_backend("records")
    b.reset({"records": {}})
    assert b.execute(PredictedCall(name="get_record", args={"record_id": "nope"})).ok is False
    assert b.execute(PredictedCall(name="made_up_tool", args={})).ok is False
    bad = b.execute(
        PredictedCall(name="update_record", args={"record_id": "x", "field": "f", "value": "v"})
    )
    assert bad.ok is False and bad.error


# ----------------------------- episode loop ---------------------------------- #


async def test_sample_episodes_all_succeed_on_oracle():
    scenarios = load_scenarios(SAMPLE)
    fixtures = {}
    for s in scenarios:
        fixtures.update(build_episode_fixtures(s.id, oracle_plan(s)))
    provider = MockProvider(fixtures)
    trajectories = await Runner().run_episodes(HandRolledOrchestrator(), scenarios, provider)
    assert len(trajectories) == len(scenarios)
    assert all(t.succeeded for t in trajectories)
    assert all(t.failure_mode == FailureMode.NONE for t in trajectories)
    # search -> update -> goal == 2 turns.
    assert all(t.turns_to_success == 2 for t in trajectories)


async def test_no_recovery_failure():
    s = _records_scenario()
    # Both turns call update on a nonexistent record -> error, never recovers.
    bad = [
        PredictedCall(
            name="update_record", args={"record_id": "zzz", "field": "status", "value": "shipped"}
        )
    ]
    provider = MockProvider(build_episode_fixtures(s.id, [bad, bad]))
    traj = await HandRolledOrchestrator().run_episode(s, provider, get_backend("records"))
    assert not traj.succeeded
    assert traj.failure_mode == FailureMode.NO_RECOVERY


async def test_gave_up_failure():
    s = _records_scenario()
    provider = MockProvider(build_episode_fixtures(s.id, [[]]))  # stops immediately
    traj = await HandRolledOrchestrator().run_episode(s, provider, get_backend("records"))
    assert not traj.succeeded
    assert traj.stop_reason == "no_call"
    assert traj.failure_mode == FailureMode.GAVE_UP


async def test_provider_error_captured():
    s = _records_scenario()

    class _Boom:
        name = "boom"

        async def complete(self, request: LLMRequest) -> ModelResponse:
            return ModelResponse(error="503 overloaded")

    traj = await HandRolledOrchestrator().run_episode(s, _Boom(), get_backend("records"))
    assert isinstance(traj, Trajectory)
    assert traj.stop_reason == "provider_error"
    assert traj.failure_mode == FailureMode.PROVIDER_ERROR


async def test_recovery_counts_as_success():
    s = _records_scenario()
    good = PredictedCall(
        name="update_record", args={"record_id": "r1", "field": "status", "value": "shipped"}
    )
    bad = PredictedCall(
        name="update_record", args={"record_id": "zzz", "field": "status", "value": "shipped"}
    )
    provider = MockProvider(build_episode_fixtures(s.id, [[bad], [good]]))  # err then recover
    trajectories = [await HandRolledOrchestrator().run_episode(s, provider, get_backend("records"))]
    assert trajectories[0].succeeded
    report = aggregate_episodes(trajectories)
    assert report.recovery_rate == 1.0
    assert report.invalid_call_rate == 0.5  # 1 of 2 calls errored


# ----------------------------- loader ---------------------------------------- #


def test_loader_fills_tools_from_backend():
    scenarios = load_scenarios(SAMPLE)
    assert len(scenarios) >= 4
    # tools omitted in the file are filled from the records backend defaults.
    assert all(any(t.name == "update_record" for t in s.tools) for s in scenarios)


# -------------------- M2: all episode orchestrators (framework loops) -------- #


def _episode_orchestrators():
    """Instantiated episode-capable orchestrators available in this env."""
    from orchbench.orchestrators.handrolled import HandRolledOrchestrator as HR

    orchs = [HR(model="mock-model")]
    if importlib.util.find_spec("langgraph"):
        from orchbench.orchestrators.langgraph_adapter import LangGraphOrchestrator as LG

        orchs.append(LG(model="mock-model"))
    if importlib.util.find_spec("agent_framework"):
        from orchbench.orchestrators.agentframework_adapter import AgentFrameworkOrchestrator as AF

        orchs.append(AF(model="mock-model"))
    return orchs


@pytest.mark.parametrize("orch", _episode_orchestrators(), ids=lambda o: o.name)
async def test_every_episode_orchestrator_succeeds_on_oracle(orch):
    scenarios = load_scenarios(SAMPLE)
    fixtures = {}
    for s in scenarios:
        fixtures.update(build_episode_fixtures(s.id, oracle_plan(s)))
    provider = MockProvider(fixtures)
    trajectories = await Runner().run_episodes(orch, scenarios, provider)
    assert all(t.succeeded for t in trajectories), orch.name
    assert all(t.orchestrator == orch.name for t in trajectories)
    # search -> update -> goal is two turns for every orchestrator (parity).
    assert all(t.turns_to_success == 2 for t in trajectories), orch.name


@pytest.mark.parametrize("orch", _episode_orchestrators(), ids=lambda o: o.name)
async def test_every_episode_orchestrator_captures_provider_error(orch):
    s = _records_scenario()

    class _Boom:
        name = "boom"

        async def complete(self, request: LLMRequest) -> ModelResponse:
            return ModelResponse(error="503 overloaded")

    traj = await orch.run_episode(s, _Boom(), get_backend("records"))
    assert isinstance(traj, Trajectory)
    assert traj.stop_reason == "provider_error"
    assert traj.failure_mode == FailureMode.PROVIDER_ERROR
