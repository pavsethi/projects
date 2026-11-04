"""The multi-turn run harness: interleaving, counterbalancing, resume, CLI."""

import json

from typer.testing import CliRunner

from orchbench.cli import app
from orchbench.runner import Runner
from orchbench.types import Scenario, Trajectory


class _Stub:
    """An orchestrator that records the order it was run in."""

    def __init__(self, name, log):
        self.name = name
        self.model = "mock-model"
        self.log = log

    async def run_episode(self, scenario, provider, backend):
        self.log.append((self.name, scenario.id))
        return Trajectory(scenario_id=scenario.id, orchestrator=self.name, provider="p", model="m")


def _scenarios(n):
    return [Scenario(id=f"s{i}", user_turns=["go"]) for i in range(n)]


async def test_matrix_is_scenario_major_and_counterbalanced():
    log = []
    orchs = [_Stub(n, log) for n in ("a", "b", "c")]
    await Runner(concurrency=1).run_matrix(orchs, _scenarios(3), lambda _n: None)
    assert log == [
        ("a", "s0"), ("b", "s0"), ("c", "s0"),
        ("b", "s1"), ("c", "s1"), ("a", "s1"),
        ("c", "s2"), ("a", "s2"), ("b", "s2"),
    ]  # fmt: skip
    firsts = [log[i][0] for i in (0, 3, 6)]
    assert sorted(firsts) == ["a", "b", "c"]  # each orchestrator leads once


async def test_matrix_skips_done_pairs_and_reports_each_result():
    log, seen = [], []
    orchs = [_Stub(n, log) for n in ("a", "b")]
    out = await Runner(concurrency=2).run_matrix(
        orchs, _scenarios(2), lambda _n: None, skip={("a", "s0")}, on_result=seen.append
    )
    assert ("a", "s0") not in log
    assert len(out) == len(seen) == 3


def test_estimate_needs_no_key_and_makes_no_calls(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = CliRunner().invoke(
        app,
        ["episodes", "--suite", "bfcl", "--limit", "2", "--model", "claude-sonnet-5",
         "--estimate"],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert "with prompt caching" in result.output
    assert "Multi-turn:" not in result.output  # exited before running anything


def test_bfcl_mock_run_writes_checkpoints_and_resumes(tmp_path):
    out = tmp_path / "run.json"
    args = ["episodes", "--suite", "bfcl", "--category", "base,miss_func", "--limit", "2",
            "--orchestrators", "handrolled", "--out", str(out)]  # fmt: skip
    first = CliRunner().invoke(app, args)
    assert first.exit_code == 0, first.output
    assert "ACCURACY BY CATEGORY" in first.output
    partial = out.with_suffix(".partial.jsonl")
    assert len(partial.read_text().splitlines()) == 4
    payload = json.loads(out.read_text())
    assert payload["meta"]["suite"] == "bfcl"
    assert all(t["succeeded"] for t in payload["trajectories"])

    again = CliRunner().invoke(app, [*args, "--resume"])
    assert again.exit_code == 0, again.output
    assert "Resuming: 4 trajectories" in again.output
    assert len(json.loads(out.read_text())["trajectories"]) == 4  # nothing re-run


def test_unknown_orchestrator_is_rejected():
    result = CliRunner().invoke(app, ["episodes", "--orchestrators", "nope"])
    assert result.exit_code != 0
