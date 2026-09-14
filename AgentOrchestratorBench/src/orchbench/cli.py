"""``orchbench`` command-line interface.

Commands
--------
* ``orchbench demo``   -- run the built-in orchestrator over the sample suite
  across three simulated model tiers, with no API keys. The fastest way to see
  the whole pipeline (metrics + variance + failure taxonomy) working.
* ``orchbench run``    -- run one orchestrator/provider over a dataset, write
  graded results to JSON.
* ``orchbench report`` -- aggregate one or more results files into a comparison.
* ``orchbench list``   -- show available orchestrators, providers and suites.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from statistics import mean, pstdev

import typer

from orchbench.metrics import SuiteReport, aggregate
from orchbench.orchestrators import BUILTIN
from orchbench.orchestrators.handrolled import HandRolledOrchestrator
from orchbench.providers.base import LLMProvider
from orchbench.providers.mock import PROFILES, MockProvider, build_fixtures
from orchbench.runner import Runner
from orchbench.suites.bfcl import load_jsonl
from orchbench.types import RunResult

app = typer.Typer(add_completion=False, help="A reproducible eval harness for agent orchestrators.")

_SAMPLE = Path(__file__).resolve().parents[2] / "data" / "bfcl_sample.jsonl"


def _fmt_pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def _print_report(report: SuiteReport, label: str | None = None) -> None:
    title = label or f"{report.orchestrator} / {report.model}"
    typer.echo(f"\n=== {title}  (n={report.n}, seeds={report.seeds}) ===")
    typer.echo(f"  routing accuracy : {_fmt_pct(report.routing_accuracy)}")
    typer.echo(f"  exact accuracy   : {_fmt_pct(report.exact_accuracy)}")
    typer.echo(f"  tokens/task      : {report.avg_tokens_per_task:8.1f}")
    typer.echo(f"  est. cost (USD)  : ${report.est_cost_usd:.4f}")
    typer.echo(
        f"  latency ms       : p50={report.latency_p50_ms:6.0f} "
        f"p95={report.latency_p95_ms:6.0f} mean={report.latency_mean_ms:6.0f}"
    )
    typer.echo("  by category:")
    for cat in report.by_category:
        typer.echo(
            f"    {cat.category:10s} n={cat.n:3d}  "
            f"routing={_fmt_pct(cat.routing_accuracy)}  exact={_fmt_pct(cat.exact_accuracy)}"
        )
    nonzero = {k: v for k, v in report.failure_modes.items() if v and k != "none"}
    if nonzero:
        typer.echo("  failure modes:")
        for mode, count in sorted(nonzero.items(), key=lambda kv: -kv[1]):
            typer.echo(f"    {mode:18s} {count}")


def _print_comparison(reports: list[tuple[str, SuiteReport]]) -> None:
    typer.echo("\n" + "=" * 78)
    typer.echo("COMPARISON")
    typer.echo("=" * 78)
    header = (
        f"{'config':22s} {'routing':>8s} {'exact':>8s} "
        f"{'tok/task':>9s} {'cost$':>9s} {'p95 ms':>8s}"
    )
    typer.echo(header)
    typer.echo("-" * 78)
    for label, r in reports:
        typer.echo(
            f"{label:22s} {_fmt_pct(r.routing_accuracy):>8s} {_fmt_pct(r.exact_accuracy):>8s} "
            f"{r.avg_tokens_per_task:9.1f} {r.est_cost_usd:9.4f} {r.latency_p95_ms:8.0f}"
        )


@app.command()
def demo(
    seeds: int = typer.Option(5, help="Number of seeds per tier (shows variance)."),
    data: Path = typer.Option(_SAMPLE, help="Task dataset (JSONL)."),
) -> None:
    """Run the handrolled orchestrator across simulated model tiers (no API keys)."""
    tasks = load_jsonl(data)
    runner = Runner(concurrency=16)

    typer.secho(
        "NOTE: demo uses the deterministic MOCK provider. These numbers are "
        "SYNTHETIC (they exercise the harness, they are not real model results).",
        fg=typer.colors.YELLOW,
    )
    typer.echo(f"Loaded {len(tasks)} tasks from {data}")

    async def run_tier(tier: str) -> tuple[SuiteReport, float]:
        all_results: list[RunResult] = []
        per_seed_routing: list[float] = []
        for seed in range(seeds):
            provider = MockProvider(build_fixtures(tasks, tier, seed=seed))
            orch = HandRolledOrchestrator(model="mock-model")
            results = await runner.run_suite(orch, tasks, provider, seed=seed)
            all_results.extend(results)
            per_seed_routing.append(mean(1.0 if r.grade.routing_correct else 0.0 for r in results))
        return aggregate(all_results), pstdev(per_seed_routing) if len(
            per_seed_routing
        ) > 1 else 0.0

    comparison: list[tuple[str, SuiteReport]] = []
    for tier in ("strong", "balanced", "weak"):
        report, routing_std = asyncio.run(run_tier(tier))
        label = f"handrolled/{tier}"
        _print_report(report, label=label)
        typer.echo(f"  routing accuracy std across seeds: ±{routing_std * 100:.1f}pp")
        comparison.append((label, report))

    _print_comparison(comparison)


@app.command()
def run(
    data: Path = typer.Option(_SAMPLE, help="Task dataset (JSONL)."),
    orchestrator: str = typer.Option("handrolled", help="Orchestrator name."),
    provider: str = typer.Option("mock", help="Provider: 'mock' or 'anthropic'."),
    profile: str = typer.Option("balanced", help="Mock quality profile: strong|balanced|weak."),
    model: str = typer.Option("mock-model", help="Model id (recorded and priced)."),
    seeds: int = typer.Option(1, help="Number of seeds to run (mock provider)."),
    concurrency: int = typer.Option(8, help="Max concurrent tasks."),
    out: Path | None = typer.Option(None, help="Write graded results JSON here."),
) -> None:
    """Run one orchestrator/provider over a dataset and grade it."""
    tasks = load_jsonl(data)
    if orchestrator not in BUILTIN:
        raise typer.BadParameter(f"unknown orchestrator {orchestrator!r}; try: {list(BUILTIN)}")
    if profile not in PROFILES:
        raise typer.BadParameter(f"unknown profile {profile!r}; try: {list(PROFILES)}")

    orch = BUILTIN[orchestrator](model=model)
    runner = Runner(concurrency=concurrency)

    async def go() -> list[RunResult]:
        results: list[RunResult] = []
        for seed in range(seeds):
            prov: LLMProvider
            if provider == "mock":
                prov = MockProvider(build_fixtures(tasks, profile, seed=seed))
            elif provider == "anthropic":
                from orchbench.providers.anthropic import AnthropicProvider

                prov = AnthropicProvider(model=model)
            else:
                raise typer.BadParameter(f"unknown provider {provider!r}")
            results.extend(await runner.run_suite(orch, tasks, prov, seed=seed))
        return results

    results = asyncio.run(go())
    report = aggregate(results)
    _print_report(report)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {
                "orchestrator": orchestrator,
                "provider": provider,
                "model": model,
                "profile": profile if provider == "mock" else None,
                "data": str(data),
                "seeds": seeds,
            },
            "results": [r.model_dump() for r in results],
        }
        out.write_text(json.dumps(payload, indent=2))
        typer.echo(f"\nWrote {len(results)} results to {out}")


@app.command()
def report(files: list[Path]) -> None:
    """Aggregate one or more results JSON files into a comparison table."""
    comparison: list[tuple[str, SuiteReport]] = []
    for path in files:
        payload = json.loads(path.read_text())
        results = [RunResult.model_validate(r) for r in payload["results"]]
        rep = aggregate(results)
        label = f"{rep.orchestrator}/{rep.model}"
        _print_report(rep, label=label)
        comparison.append((label, rep))
    if len(comparison) > 1:
        _print_comparison(comparison)


@app.command("list")
def list_() -> None:
    """List available orchestrators, providers and suites."""
    typer.echo("orchestrators (builtin): " + ", ".join(BUILTIN))
    typer.echo("orchestrators (optional): langgraph, agentframework")
    typer.echo("providers: mock (default), anthropic")
    typer.echo("mock profiles: " + ", ".join(PROFILES))
    typer.echo("suites: bfcl (portable JSONL + native BFCL loader)")


if __name__ == "__main__":  # pragma: no cover
    app()
