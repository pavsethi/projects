import pathlib

from orchbench.metrics import aggregate, estimate_cost_usd
from orchbench.orchestrators.handrolled import HandRolledOrchestrator
from orchbench.providers.mock import MockProvider, QualityProfile, build_fixtures
from orchbench.runner import Runner
from orchbench.suites.bfcl import load_jsonl

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


async def test_end_to_end_perfect_is_100pct():
    tasks = load_jsonl(SAMPLE)
    provider = MockProvider(build_fixtures(tasks, _PERFECT, seed=0))
    results = await Runner(concurrency=8).run_suite(HandRolledOrchestrator(), tasks, provider)
    assert len(results) == len(tasks)
    report = aggregate(results)
    assert report.routing_accuracy == 1.0
    assert report.exact_accuracy == 1.0
    assert report.failure_modes["none"] == len(tasks)


async def test_weak_profile_produces_failures():
    tasks = load_jsonl(SAMPLE)
    all_results = []
    for seed in range(8):
        provider = MockProvider(build_fixtures(tasks, "weak", seed=seed))
        all_results += await Runner().run_suite(
            HandRolledOrchestrator(), tasks, provider, seed=seed
        )
    report = aggregate(all_results)
    assert report.routing_accuracy < 1.0
    assert sum(v for k, v in report.failure_modes.items() if k != "none") > 0
    # Every result carries a category rollup.
    assert {"simple", "multiple", "parallel", "irrelevance"} <= {
        c.category for c in report.by_category
    }


def test_cost_estimate_uses_pricing_table():
    # 1M input tokens of a $3/1M model = $3.
    assert estimate_cost_usd(1_000_000, 0, "mock-model") == 3.0
    assert estimate_cost_usd(0, 1_000_000, "mock-model") == 15.0


async def test_seeds_are_recorded():
    tasks = load_jsonl(SAMPLE)
    provider = MockProvider(build_fixtures(tasks, "balanced", seed=7))
    results = await Runner().run_suite(HandRolledOrchestrator(), tasks, provider, seed=7)
    assert all(r.seed == 7 for r in results)
