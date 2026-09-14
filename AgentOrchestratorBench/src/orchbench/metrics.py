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
from orchbench.types import FailureMode, RunResult

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
