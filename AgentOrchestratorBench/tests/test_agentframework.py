"""End-to-end test for the Agent Framework adapter, skipped unless installed.

Runs where the ``agentframework`` extra is present (``pip install -e
'.[agentframework]'``); skipped in the default dev/CI env. Proves the adapter
honours the orchestrator contract over the shared mock provider -- a real third
orchestrator graded on equal terms, not a stub.
"""

import pathlib

import pytest

pytest.importorskip("agent_framework")

from orchbench.orchestrators.agentframework_adapter import AgentFrameworkOrchestrator  # noqa: E402
from orchbench.providers.mock import MockProvider, QualityProfile, build_fixtures  # noqa: E402
from orchbench.runner import Runner  # noqa: E402
from orchbench.suites.bfcl import load_jsonl  # noqa: E402
from orchbench.types import OrchestratorOutput  # noqa: E402

SAMPLE = pathlib.Path(__file__).resolve().parents[1] / "data" / "bfcl_sample.jsonl"

_PERFECT = QualityProfile(
    name="perfect",
    p_provider_error=0.0,
    p_empty=0.0,
    p_hallucinate=0.0,
    p_wrong_tool=0.0,
    p_missing_call=0.0,
    p_extra_call=0.0,
    p_wrong_args=0.0,
)


async def test_agentframework_runs_over_shared_provider():
    tasks = load_jsonl(SAMPLE)
    provider = MockProvider(build_fixtures(tasks, _PERFECT, seed=0))
    orch = AgentFrameworkOrchestrator(model="mock-model")
    results = await Runner().run_suite(orch, tasks, provider)
    assert len(results) == len(tasks)
    assert all(r.orchestrator == "agentframework" for r in results)
    # A perfect provider round-tripped through the framework's Content types
    # should route (and grade) everything correctly.
    assert all(r.grade.routing_correct for r in results)


async def test_agentframework_captures_provider_error():
    tasks = load_jsonl(SAMPLE)
    out = await AgentFrameworkOrchestrator(model="mock-model").route(tasks[0], MockProvider({}))
    assert isinstance(out, OrchestratorOutput)
    assert out.error is not None  # missing fixture -> captured, not raised
    assert out.predicted == []
