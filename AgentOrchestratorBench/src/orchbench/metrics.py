"""Aggregation: turn a list of graded results into a report.

Reports the four things a migration decision actually turns on -- routing
accuracy, token cost, latency, and the failure-mode breakdown -- with a
per-category split so you can see *where* accuracy is lost (e.g. parallel calls),
not just the headline number.
"""

from __future__ import annotations

from statistics import mean

from pydantic import BaseModel, Field

from orchbench.failures import summarize
from orchbench.types import FailureMode, RunResult, Trajectory

# Illustrative pricing, USD per 1M tokens (input, output). Edit for real models;
# "mock-model" is priced so the demo shows a non-zero, comparable cost column.
PRICING: dict[str, tuple[float, float]] = {
    "mock-model": (3.0, 15.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-opus-5": (15.0, 75.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    in_price, out_price = PRICING.get(model, (0.0, 0.0))
    return (prompt_tokens / 1_000_000) * in_price + (completion_tokens / 1_000_000) * out_price


class CategoryMetrics(BaseModel):
    category: str
    n: int
    routing_accuracy: float
    exact_accuracy: float


class SuiteReport(BaseModel):
    """Aggregate metrics for one (orchestrator, model, provider) sweep."""

    orchestrator: str
    model: str
    provider: str
    n: int
    seeds: list[int] = Field(default_factory=list)

    routing_accuracy: float
    exact_accuracy: float

    total_tokens: int
    avg_tokens_per_task: float
    est_cost_usd: float

    latency_p50_ms: float
    latency_p95_ms: float
    latency_mean_ms: float

    failure_modes: dict[str, int]
    by_category: list[CategoryMetrics]


def aggregate(results: list[RunResult]) -> SuiteReport:
    """Collapse graded results (possibly across seeds) into one report."""
    if not results:
        raise ValueError("cannot aggregate an empty result set")

    n = len(results)
    routing = mean(1.0 if r.grade.routing_correct else 0.0 for r in results)
    exact = mean(1.0 if r.grade.exact_correct else 0.0 for r in results)

    total_tokens = sum(r.total_tokens for r in results)
    latencies = [r.latency_ms for r in results]
    model = results[0].model
    est_cost = sum(
        estimate_cost_usd(r.prompt_tokens, r.completion_tokens, r.model) for r in results
    )

    categories = sorted({r.category for r in results})
    by_category = []
    for cat in categories:
        rows = [r for r in results if r.category == cat]
        by_category.append(
            CategoryMetrics(
                category=cat,
                n=len(rows),
                routing_accuracy=mean(1.0 if r.grade.routing_correct else 0.0 for r in rows),
                exact_accuracy=mean(1.0 if r.grade.exact_correct else 0.0 for r in rows),
            )
        )

    return SuiteReport(
        orchestrator=results[0].orchestrator,
        model=model,
        provider=results[0].provider,
        n=n,
        seeds=sorted({r.seed for r in results}),
        routing_accuracy=routing,
        exact_accuracy=exact,
        total_tokens=total_tokens,
        avg_tokens_per_task=total_tokens / n,
        est_cost_usd=est_cost,
        latency_p50_ms=_percentile(latencies, 0.50),
        latency_p95_ms=_percentile(latencies, 0.95),
        latency_mean_ms=mean(latencies),
        failure_modes=summarize([FailureMode(r.grade.failure_mode) for r in results]),
        by_category=by_category,
    )


class EpisodeReport(BaseModel):
    """Aggregate metrics for one orchestrator's multi-turn sweep."""

    orchestrator: str
    model: str
    provider: str
    n: int

    success_rate: float
    avg_turns_to_success: float | None  # mean turns among successes
    recovery_rate: float  # of episodes that hit a tool error, fraction that still succeeded
    invalid_call_rate: float  # fraction of all calls the backend rejected

    total_tokens: int
    avg_tokens_per_episode: float
    est_cost_usd: float

    latency_p50_ms: float
    latency_p95_ms: float

    failure_modes: dict[str, int]


def aggregate_episodes(trajectories: list[Trajectory]) -> EpisodeReport:
    """Collapse trajectories into a multi-turn report."""
    if not trajectories:
        raise ValueError("cannot aggregate an empty trajectory set")

    n = len(trajectories)
    successes = [t for t in trajectories if t.succeeded]
    success_rate = len(successes) / n
    _tts = [t.turns_to_success for t in successes if t.turns_to_success]
    avg_tts = mean(_tts) if _tts else None

    # Recovery: among episodes that hit at least one tool error, how many succeeded.
    def hit_error(t: Trajectory) -> bool:
        return any(not r.ok for turn in t.turns for r in turn.results)

    errored = [t for t in trajectories if hit_error(t)]
    recovery_rate = sum(1 for t in errored if t.succeeded) / len(errored) if errored else 0.0

    total_calls = sum(len(turn.results) for t in trajectories for turn in t.turns)
    bad_calls = sum(1 for t in trajectories for turn in t.turns for r in turn.results if not r.ok)
    invalid_call_rate = (bad_calls / total_calls) if total_calls else 0.0

    total_tokens = sum(t.total_tokens for t in trajectories)
    latencies = [t.total_latency_ms for t in trajectories]
    model = trajectories[0].model
    # Approximate input/output split per episode as prompt vs completion sums.
    prompt_tokens = sum(turn.prompt_tokens for t in trajectories for turn in t.turns)
    completion_tokens = sum(turn.completion_tokens for t in trajectories for turn in t.turns)
    est_cost = estimate_cost_usd(prompt_tokens, completion_tokens, model)

    return EpisodeReport(
        orchestrator=trajectories[0].orchestrator,
        model=model,
        provider=trajectories[0].provider,
        n=n,
        success_rate=success_rate,
        avg_turns_to_success=avg_tts,
        recovery_rate=recovery_rate,
        invalid_call_rate=invalid_call_rate,
        total_tokens=total_tokens,
        avg_tokens_per_episode=total_tokens / n,
        est_cost_usd=est_cost,
        latency_p50_ms=_percentile(latencies, 0.50),
        latency_p95_ms=_percentile(latencies, 0.95),
        failure_modes=summarize([FailureMode(t.failure_mode) for t in trajectories]),
    )
