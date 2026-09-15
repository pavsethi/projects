import pathlib

from orchbench.providers.mock import MockProvider, QualityProfile, build_fixtures
from orchbench.suites.bfcl import load_jsonl
from orchbench.types import LLMRequest

SAMPLE = pathlib.Path(__file__).resolve().parents[1] / "data" / "bfcl_sample.jsonl"


def test_fixtures_are_deterministic():
    tasks = load_jsonl(SAMPLE)
    a = build_fixtures(tasks, "balanced", seed=1)
    b = build_fixtures(tasks, "balanced", seed=1)
    assert {k: v.model_dump() for k, v in a.items()} == {k: v.model_dump() for k, v in b.items()}


def test_different_seeds_differ():
    tasks = load_jsonl(SAMPLE)
    a = build_fixtures(tasks, "weak", seed=1)
    b = build_fixtures(tasks, "weak", seed=2)
    assert {k: v.model_dump() for k, v in a.items()} != {k: v.model_dump() for k, v in b.items()}


async def test_mock_provider_serves_by_task_id():
    tasks = load_jsonl(SAMPLE)
    provider = MockProvider(build_fixtures(tasks, "strong", seed=0))
    req = LLMRequest(model="mock-model", messages=[], metadata={"task_id": tasks[0].id})
    resp = await provider.complete(req)
    assert resp.error is None
    assert resp.tool_calls


async def test_mock_provider_missing_fixture_is_error_not_crash():
    provider = MockProvider({})
    resp = await provider.complete(LLMRequest(model="m", messages=[], metadata={"task_id": "nope"}))
    assert resp.error is not None


def test_perfect_profile_is_all_correct():
    tasks = load_jsonl(SAMPLE)
    perfect = QualityProfile(
        name="perfect",
        p_provider_error=0.0,
        p_empty=0.0,
        p_hallucinate=0.0,
        p_wrong_tool=0.0,
        p_missing_call=0.0,
        p_extra_call=0.0,
        p_wrong_args=0.0,
    )
    fixtures = build_fixtures(tasks, perfect, seed=3)
    for task in tasks:
        resp = fixtures[task.id]
        names = sorted(c.name for c in resp.tool_calls)
        assert names == sorted(g.name for g in task.ground_truth)
