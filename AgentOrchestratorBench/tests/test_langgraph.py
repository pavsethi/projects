"""End-to-end test for the LangGraph adapter, skipped unless langgraph is installed.

Runs in environments with the ``langgraph`` extra (``pip install -e '.[langgraph]'``);
skipped in the default dev/CI env. Proves the adapter honours the orchestrator
contract over the *shared* mock provider -- i.e. it's a real second orchestrator
graded on equal terms, not a stub.
"""

import pathlib

import pytest

pytest.importorskip("langgraph")

from orchbench.orchestrators.langgraph_adapter import LangGraphOrchestrator  # noqa: E402
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


async def test_langgraph_runs_over_shared_provider():
    tasks = load_jsonl(SAMPLE)
    provider = MockProvider(build_fixtures(tasks, _PERFECT, seed=0))
    results = await Runner().run_suite(LangGraphOrchestrator(model="mock-model"), tasks, provider)
    assert len(results) == len(tasks)
    assert all(r.orchestrator == "langgraph" for r in results)
    # With a perfect provider the one-node graph should route everything.
    assert all(r.grade.routing_correct for r in results)


async def test_langgraph_captures_provider_error():
    tasks = load_jsonl(SAMPLE)
    out = await LangGraphOrchestrator(model="mock-model").route(tasks[0], MockProvider({}))
    assert isinstance(out, OrchestratorOutput)
    assert out.error is not None  # missing fixture -> captured, not raised
