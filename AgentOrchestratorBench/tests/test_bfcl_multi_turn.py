"""BFCL multi-turn: loader fidelity, the checker port, and safe execution.

The strongest check is the oracle replay: feeding BFCL's own ground truth back
as model output must pass the checker on every scenario of every category. The
negative tests make sure that pass isn't vacuous -- each kind of mistake fails
for the right reason.
"""

import importlib.util

import pytest

from orchbench.backends import get_backend, oracle_plan
from orchbench.backends.bfcl import BFCLBackend, invoke, method_table, parse_call
from orchbench.orchestrators.handrolled import HandRolledOrchestrator
from orchbench.providers.mock import MockProvider, build_episode_fixtures
from orchbench.runner import Runner
from orchbench.suites.bfcl_multi_turn import (
    ADDITIONAL_FUNCTION_PROMPT,
    CATEGORIES,
    MAXIMUM_STEP_LIMIT,
    load_bfcl_multi_turn,
)
from orchbench.types import FailureMode, PredictedCall


def _call(name, **args):
    return PredictedCall(name=name, args=args)


async def _run(scenario, plan, orch=None):
    orch = orch or HandRolledOrchestrator(model="mock-model")
    provider = MockProvider(build_episode_fixtures(scenario.id, plan))
    return await orch.run_episode(scenario, provider, get_backend("bfcl"))


def _base0():
    return load_bfcl_multi_turn("base", ids=["multi_turn_base_0"])[0]


# ----------------------------- loader --------------------------------------- #


def test_loader_shapes_a_scenario_like_bfcl_fc_mode():
    s = _base0()
    assert s.backend == "bfcl" and s.suite == "bfcl_multi_turn" and s.category == "base"
    assert s.system_prompt == ""  # BFCL FC mode sends no system prompt
    assert s.max_turns == MAXIMUM_STEP_LIMIT + 1
    assert len(s.user_turns) == len(s.initial_state["ground_truth"]) == 4
    assert s.user_turns[0].startswith("Move 'final_report.pdf'")
    assert {"cd", "mkdir", "mv", "post_tweet"} <= {t.name for t in s.tools}
    assert all(t.description.endswith("}") or "Python 3 syntax" in t.description for t in s.tools)


def test_miss_func_withholds_then_adds_the_function():
    s = load_bfcl_multi_turn("miss_func", ids=["multi_turn_miss_func_0"])[0]
    assert "sort" not in {t.name for t in s.tools}
    assert [t.name for t in s.tools_added[3]] == ["sort"]
    assert s.user_turns[3] == ADDITIONAL_FUNCTION_PROMPT


def test_every_category_loads_200_scenarios():
    for cat in CATEGORIES:
        assert len(load_bfcl_multi_turn(cat)) == 200


# ----------------------------- oracle replay -------------------------------- #


@pytest.mark.parametrize("category", CATEGORIES)
async def test_ground_truth_replay_passes_every_scenario(category):
    scenarios = load_bfcl_multi_turn(category)
    fixtures = {}
    for s in scenarios:
        fixtures.update(build_episode_fixtures(s.id, oracle_plan(s)))
    trajs = await Runner(concurrency=16).run_episodes(
        HandRolledOrchestrator(model="mock-model"), scenarios, MockProvider(fixtures)
    )
    failed = [(t.scenario_id, t.grade_detail) for t in trajs if not t.succeeded]
    assert not failed, failed[:3]


def _framework_orchs():
    orchs = []
    if importlib.util.find_spec("langgraph"):
        from orchbench.orchestrators.langgraph_adapter import LangGraphOrchestrator

        orchs.append(LangGraphOrchestrator(model="mock-model"))
    if importlib.util.find_spec("agent_framework"):
        from orchbench.orchestrators.agentframework_adapter import AgentFrameworkOrchestrator

        orchs.append(AgentFrameworkOrchestrator(model="mock-model"))
    return orchs


@pytest.mark.parametrize("orch", _framework_orchs(), ids=lambda o: o.name)
async def test_framework_adapters_pass_ground_truth_replay(orch):
    scenarios = load_bfcl_multi_turn("base", limit=25) + load_bfcl_multi_turn("miss_func", limit=25)
    for s in scenarios:
        traj = await _run(s, oracle_plan(s), orch)
        assert traj.succeeded, (s.id, traj.grade_detail)


def test_oracle_binds_positional_ground_truth_args():
    # Ground truth "sort('final_report.pdf')" -> keyword call (tool calls are kwargs).
    plan = oracle_plan(_base0())
    sort_calls = [c for step in plan for c in step if c.name == "sort"]
    assert sort_calls == [_call("sort", file_name="final_report.pdf")]


# ----------------------------- the checker fails correctly ------------------ #


async def test_wrong_argument_is_a_state_mismatch():
    s = _base0()
    plan = oracle_plan(s)
    plan[0] = [c if c.name != "mkdir" else _call("mkdir", dir_name="tmp") for c in plan[0]]
    traj = await _run(s, plan)
    assert not traj.succeeded
    assert traj.grade_detail["error_type"] == "state_mismatch"
    assert traj.grade_detail["failed_user_turn"] == 0
    assert traj.failure_mode == FailureMode.STATE_MISMATCH


async def test_missing_read_only_call_is_a_response_mismatch():
    s = _base0()
    plan = oracle_plan(s)
    # Turn 1 is cd + grep; grep changes no state, so only the response check sees it.
    turn1 = plan[2]
    assert [c.name for c in turn1] == ["cd", "grep"]
    plan[2] = [turn1[0]]
    traj = await _run(s, plan)
    assert traj.grade_detail["error_type"] == "response_mismatch"
    assert traj.grade_detail["failed_user_turn"] == 1
    assert traj.failure_mode == FailureMode.RESPONSE_MISMATCH


async def test_silent_turn_is_an_empty_turn_failure():
    s = _base0()
    plan = [[], *oracle_plan(s)[2:]]  # say nothing on turn 0, then carry on
    traj = await _run(s, plan)
    assert traj.grade_detail["error_type"] == "empty_turn"
    assert traj.grade_detail["failed_user_turn"] == 0
    assert traj.failure_mode == FailureMode.EMPTY_TURN


async def test_extra_calls_are_allowed():
    # BFCL's response check is a subset check: harmless extra reads still pass.
    s = _base0()
    plan = oracle_plan(s)
    plan[0] = [_call("ls"), *plan[0], _call("pwd")]
    traj = await _run(s, plan)
    assert traj.succeeded, traj.grade_detail


async def test_step_limit_force_quits_the_scenario():
    s = _base0()
    looping = [[_call("ls")]] * (MAXIMUM_STEP_LIMIT + 5)
    traj = await _run(s, looping)
    assert not traj.succeeded
    assert traj.stop_reason == "max_turns"
    assert len(traj.turns) == MAXIMUM_STEP_LIMIT + 1  # BFCL quits once count > 20
    assert traj.grade_detail["error_type"] == "incomplete"


async def test_calls_on_a_should_not_act_turn_are_not_penalised_directly():
    # miss_param: one turn's ground truth is empty (the model should ask). BFCL
    # skips checks there, so an extra harmless call on that turn still passes.
    s = load_bfcl_multi_turn("miss_param", ids=["multi_turn_miss_param_0"])[0]
    gt = s.initial_state["ground_truth"]
    empty_turn = next(i for i, t in enumerate(gt) if not t)
    plan = oracle_plan(s)
    # Locate the step that represents the empty turn: walk the plan per turn.
    idx = 0
    for turn in range(empty_turn):
        idx += 2 if gt[turn] else 1
    assert plan[idx] == []
    plan[idx : idx + 1] = [[_call("pwd")], []]
    traj = await _run(s, plan)
    assert traj.succeeded, traj.grade_detail


# ----------------------------- execution semantics -------------------------- #


def test_execution_errors_match_bfcl_strings():
    b = BFCLBackend()
    b.reset(_base0().initial_state)
    unknown = b.execute(_call("rm_rf", path="/"))
    assert unknown.content == "Error during execution: name 'rm_rf' is not defined"
    assert unknown.ok is False and unknown.is_error is False  # BFCL never flags is_error
    denied = b.execute(_call("exit"))
    assert denied.content == "Error during execution: Function call exit is not allowed."
    bad_args = b.execute(_call("cd", nope=1))
    assert bad_args.content.startswith("Error during execution: ")


def test_dict_results_are_json_and_strings_pass_through():
    b = BFCLBackend()
    b.reset(_base0().initial_state)
    r = b.execute(_call("pwd"))
    assert r.ok and r.content.startswith("{") and "current_working_directory" in r.content


def test_arguments_are_data_never_code():
    # Upstream eval()s a source string built from the call; here a hostile-looking
    # argument is just a string handed to the method.
    b = BFCLBackend()
    b.reset(_base0().initial_state)
    hostile = "__import__('os').system('echo pwned')"
    r = b.execute(_call("cd", folder=hostile))
    # Treated as a (nonexistent) folder name -- an ordinary API error, not executed.
    assert r.ok is False
    assert r.content == f'{{"error": "cd: \'{hostile}\': No such file or directory"}}'
    table = method_table(b._model)
    assert "system" not in table and "__import__" not in table


def test_parse_call_accepts_literals_only():
    assert parse_call("mv(source='a', destination='b')") == (
        "mv",
        (),
        {"source": "a", "destination": "b"},
    )
    assert parse_call("sort('x.txt')") == ("sort", ("x.txt",), {})
    with pytest.raises(ValueError):
        parse_call("cd(folder=__import__('os').getcwd())")
    with pytest.raises(ValueError):
        parse_call("os.system('x')")


def test_invoke_is_total():
    assert (
        invoke({}, "anything", (), {}) == "Error during execution: name 'anything' is not defined"
    )
