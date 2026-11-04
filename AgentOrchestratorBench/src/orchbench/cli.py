"""``orchbench`` command-line interface.

Commands
--------
* ``orchbench demo``   -- run the built-in orchestrator over the sample suite
  across three simulated model tiers, with no API keys. The fastest way to see
  the whole pipeline (metrics + variance + failure taxonomy) working.
* ``orchbench run``     -- run one orchestrator/provider over a dataset, write
  graded results to JSON.
* ``orchbench compare`` -- run *every available* orchestrator over one dataset
  and print the comparison (the multi-orchestrator money shot).
* ``orchbench report``  -- aggregate one or more results files into a comparison.
* ``orchbench list``    -- show available orchestrators, providers and suites.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from statistics import mean, pstdev
from typing import TYPE_CHECKING, cast

import typer

from orchbench.backends import oracle_plan
from orchbench.env import load_dotenv, missing_key
from orchbench.metrics import EpisodeReport, SuiteReport, aggregate, aggregate_episodes
from orchbench.orchestrators import (
    ALL_NAMES,
    available_orchestrators,
    get_orchestrator,
)
from orchbench.orchestrators.handrolled import HandRolledOrchestrator
from orchbench.providers.base import LLMProvider
from orchbench.providers.cache import CachingProvider
from orchbench.providers.mock import PROFILES, MockProvider, build_episode_fixtures, build_fixtures
from orchbench.providers.retry import RetryProvider
from orchbench.runner import Runner
from orchbench.suites.bfcl import load_bfcl_native, load_jsonl
from orchbench.suites.multiturn import load_scenarios
from orchbench.types import RunResult, Trajectory

if TYPE_CHECKING:
    from orchbench.orchestrators.base import EpisodeOrchestrator

app = typer.Typer(add_completion=False, help="A reproducible eval harness for agent orchestrators.")

_SAMPLE = Path(__file__).resolve().parents[2] / "data" / "bfcl_sample.jsonl"
_MT_SAMPLE = Path(__file__).resolve().parents[2] / "data" / "multiturn_sample.jsonl"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@app.callback()
def _load_env() -> None:
    """Load a gitignored ``.env`` (cwd, then project root); exported vars win."""
    for path in dict.fromkeys([Path.cwd() / ".env", _PROJECT_ROOT / ".env"]):
        load_dotenv(path)


def _require_key(provider: str) -> None:
    """Refuse to start a real-provider run with no credentials."""
    var = missing_key(provider)
    if var is None:
        return
    typer.echo(
        f"error: {var} is not set, so every call would fail authentication.\n"
        f"  Set it in this shell:   export {var}=...   "
        f'(PowerShell: $env:{var} = "...")\n'
        f"  or put  {var}=...  in a .env file in {Path.cwd()}",
        err=True,
    )
    raise typer.Exit(code=2)


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


def _build_provider(
    provider: str,
    *,
    tasks: list,
    profile: str,
    seed: int,
    model: str,
    cache_dir: Path | None,
    retries: int,
    thinking: bool,
    effort: str | None,
) -> LLMProvider:
    """Construct the provider for one seed.

    Real providers are wrapped ``CachingProvider(RetryProvider(real))`` so a
    sweep is resumable and survives transient 429/5xx. The mock provider is left
    bare: its per-seed fixtures share a request signature, so caching would
    collapse distinct seeds onto one cached response.
    """
    if provider == "mock":
        return MockProvider(build_fixtures(tasks, profile, seed=seed))
    if provider == "anthropic":
        _require_key(provider)
        from orchbench.providers.anthropic import AnthropicProvider

        base: LLMProvider = AnthropicProvider(model=model, thinking=thinking, effort=effort)
        base = RetryProvider(base, max_retries=retries)
        if cache_dir is not None:
            base = CachingProvider(base, cache_dir)
        return base
    raise typer.BadParameter(f"unknown provider {provider!r}")


@app.command()
def run(
    data: Path = typer.Option(_SAMPLE, help="Task dataset (JSONL)."),
    orchestrator: str = typer.Option("handrolled", help="Orchestrator name."),
    provider: str = typer.Option("mock", help="Provider: 'mock' or 'anthropic'."),
    profile: str = typer.Option("balanced", help="Mock quality profile: strong|balanced|weak."),
    model: str = typer.Option("mock-model", help="Model id (recorded and priced)."),
    seeds: int = typer.Option(1, help="Number of seeds to run."),
    concurrency: int = typer.Option(8, help="Max concurrent tasks."),
    cache_dir: Path = typer.Option(
        Path(".orchbench_cache"), help="Cache dir for real-provider responses."
    ),
    no_cache: bool = typer.Option(False, help="Disable the response cache."),
    retries: int = typer.Option(3, help="Transient-error retries (real providers)."),
    thinking: bool = typer.Option(True, help="Adaptive thinking (real providers)."),
    effort: str | None = typer.Option(None, help="Effort: low|medium|high|xhigh|max."),
    out: Path | None = typer.Option(None, help="Write graded results JSON here."),
) -> None:
    """Run one orchestrator/provider over a dataset and grade it."""
    tasks = load_jsonl(data)
    if orchestrator not in ALL_NAMES:
        raise typer.BadParameter(f"unknown orchestrator {orchestrator!r}; try: {ALL_NAMES}")
    if provider == "mock" and profile not in PROFILES:
        raise typer.BadParameter(f"unknown profile {profile!r}; try: {list(PROFILES)}")

    try:
        orch = get_orchestrator(orchestrator, model=model)
    except ImportError as exc:
        raise typer.BadParameter(str(exc)) from exc
    runner = Runner(concurrency=concurrency)
    # Caching collapses distinct seeds onto one cached response (the request is
    # identical across seeds), so disable it for multi-seed variance runs.
    cache = None if (no_cache or seeds > 1) else cache_dir
    if seeds > 1 and not no_cache and provider != "mock":
        typer.echo("note: caching disabled for multi-seed run (independent samples).")

    async def go() -> list[RunResult]:
        results: list[RunResult] = []
        for seed in range(seeds):
            prov = _build_provider(
                provider,
                tasks=tasks,
                profile=profile,
                seed=seed,
                model=model,
                cache_dir=cache,
                retries=retries,
                thinking=thinking,
                effort=effort,
            )
            results.extend(await runner.run_suite(orch, tasks, prov, seed=seed))
        return results

    results = asyncio.run(go())
    _print_report(aggregate(results))

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {
                "orchestrator": orchestrator,
                "provider": provider,
                "model": model,
                "profile": profile if provider == "mock" else None,
                "thinking": thinking if provider == "anthropic" else None,
                "effort": effort if provider == "anthropic" else None,
                "data": str(data),
                "seeds": seeds,
            },
            "results": [r.model_dump() for r in results],
        }
        out.write_text(json.dumps(payload, indent=2))
        typer.echo(f"\nWrote {len(results)} results to {out}")


@app.command()
def compare(
    data: Path = typer.Option(_SAMPLE, help="Task dataset (JSONL)."),
    provider: str = typer.Option("mock", help="Provider: 'mock' or 'anthropic'."),
    profile: str = typer.Option("balanced", help="Mock quality profile (mock provider)."),
    model: str = typer.Option("mock-model", help="Model id (recorded and priced)."),
    seeds: int = typer.Option(1, help="Seeds per orchestrator."),
    concurrency: int = typer.Option(8, help="Max concurrent tasks."),
    thinking: bool = typer.Option(True, help="Adaptive thinking (real providers)."),
    effort: str | None = typer.Option(None, help="Effort: low|medium|high|xhigh|max."),
    cache_dir: Path = typer.Option(Path(".orchbench_cache"), help="Cache dir (real providers)."),
    no_cache: bool = typer.Option(False, help="Disable the response cache."),
    out: Path | None = typer.Option(None, help="Write all graded results JSON here."),
) -> None:
    """Run every *available* orchestrator over one dataset and compare them."""
    tasks = load_jsonl(data)
    names = available_orchestrators()
    typer.echo(f"Comparing orchestrators: {', '.join(names)}  (provider={provider})")
    runner = Runner(concurrency=concurrency)
    cache = None if (no_cache or seeds > 1) else cache_dir
    comparison: list[tuple[str, SuiteReport]] = []
    all_results: list[RunResult] = []

    async def go() -> None:
        for name in names:
            orch = get_orchestrator(name, model=model)
            per_orch: list[RunResult] = []
            # Namespace the cache PER ORCHESTRATOR. At prompt parity every
            # orchestrator issues identical requests, so a shared cache would
            # serve the 2nd/3rd orchestrator from the 1st's responses -- making
            # them free but also inheriting its latency, which destroys the
            # cross-orchestrator latency comparison. Per-orchestrator caches keep
            # re-runs resumable while keeping each orchestrator's calls its own.
            orch_cache = (cache / name) if cache is not None else None
            for seed in range(seeds):
                prov = _build_provider(
                    provider,
                    tasks=tasks,
                    profile=profile,
                    seed=seed,
                    model=model,
                    cache_dir=orch_cache,
                    retries=3,
                    thinking=thinking,
                    effort=effort,
                )
                per_orch.extend(await runner.run_suite(orch, tasks, prov, seed=seed))
            report = aggregate(per_orch)
            _print_report(report, label=f"{name}/{model}")
            comparison.append((name, report))
            all_results.extend(per_orch)

    asyncio.run(go())
    _print_comparison(comparison)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {
                "command": "compare",
                "provider": provider,
                "model": model,
                "orchestrators": names,
                "profile": profile if provider == "mock" else None,
                "thinking": thinking if provider == "anthropic" else None,
                "effort": effort if provider == "anthropic" else None,
                "data": str(data),
                "seeds": seeds,
            },
            "results": [r.model_dump() for r in all_results],
        }
        out.write_text(json.dumps(payload, indent=2))
        typer.echo(f"\nWrote {len(all_results)} results to {out}")


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


def _print_episode_report(report: EpisodeReport, label: str) -> None:
    tts = f"{report.avg_turns_to_success:.1f}" if report.avg_turns_to_success is not None else "n/a"
    typer.echo(f"\n=== {label}  (n={report.n}) ===")
    typer.echo(f"  success rate      : {_fmt_pct(report.success_rate)}")
    typer.echo(f"  avg turns→success : {tts}")
    typer.echo(f"  recovery rate     : {_fmt_pct(report.recovery_rate)}")
    typer.echo(f"  invalid-call rate : {_fmt_pct(report.invalid_call_rate)}")
    typer.echo(f"  tokens/episode    : {report.avg_tokens_per_episode:8.1f}")
    typer.echo(f"  est. cost (USD)   : ${report.est_cost_usd:.4f}")
    typer.echo(
        f"  latency ms        : p50={report.latency_p50_ms:6.0f} p95={report.latency_p95_ms:6.0f}"
    )
    nonzero = {k: v for k, v in report.failure_modes.items() if v and k != "none"}
    if nonzero:
        typer.echo("  failure modes:")
        for mode, count in sorted(nonzero.items(), key=lambda kv: -kv[1]):
            typer.echo(f"    {mode:20s} {count}")


@app.command()
def episodes(
    data: Path = typer.Option(_MT_SAMPLE, help="Scenario dataset (JSONL)."),
    provider: str = typer.Option("mock", help="Provider: 'mock' or 'anthropic'."),
    model: str = typer.Option("mock-model", help="Model id (recorded and priced)."),
    concurrency: int = typer.Option(8, help="Max concurrent episodes."),
    thinking: bool = typer.Option(True, help="Adaptive thinking (real providers)."),
    effort: str | None = typer.Option(None, help="Effort: low|medium|high|xhigh|max."),
    out: Path | None = typer.Option(None, help="Write all trajectories JSON here."),
) -> None:
    """Run multi-turn scenarios through every episode-capable orchestrator.

    On the mock provider this uses each backend's oracle plan to drive a correct
    episode end-to-end with no API keys.
    """
    _require_key(provider)
    scenarios = load_scenarios(data)
    names = [n for n in available_orchestrators() if hasattr(get_orchestrator(n), "run_episode")]
    typer.echo(f"Multi-turn: {', '.join(names)}  (provider={provider}, {len(scenarios)} scenarios)")
    runner = Runner(concurrency=concurrency)
    comparison: list[tuple[str, EpisodeReport]] = []
    all_trajectories: list[Trajectory] = []

    def make_provider() -> LLMProvider:
        if provider == "mock":
            fixtures = {}
            for scenario in scenarios:
                fixtures.update(build_episode_fixtures(scenario.id, oracle_plan(scenario)))
            return MockProvider(fixtures)
        if provider == "anthropic":
            from orchbench.providers.anthropic import AnthropicProvider

            base: LLMProvider = AnthropicProvider(model=model, thinking=thinking, effort=effort)
            return RetryProvider(base, max_retries=3)
        raise typer.BadParameter(f"unknown provider {provider!r}")

    async def go() -> None:
        for name in names:
            orch = cast("EpisodeOrchestrator", get_orchestrator(name, model=model))
            trajectories = await runner.run_episodes(orch, scenarios, make_provider())
            report = aggregate_episodes(trajectories)
            _print_episode_report(report, label=f"{name}/{model}")
            comparison.append((name, report))
            all_trajectories.extend(trajectories)

    asyncio.run(go())

    if len(comparison) > 1:
        typer.echo("\n" + "=" * 78)
        typer.echo("MULTI-TURN COMPARISON")
        typer.echo("=" * 78)
        header = f"{'config':22s} {'success':>8s} {'recover':>8s} {'tok/ep':>9s} {'p95 ms':>8s}"
        typer.echo(header)
        typer.echo("-" * 78)
        for label, r in comparison:
            typer.echo(
                f"{label:22s} {_fmt_pct(r.success_rate):>8s} {_fmt_pct(r.recovery_rate):>8s} "
                f"{r.avg_tokens_per_episode:9.1f} {r.latency_p95_ms:8.0f}"
            )

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {
                "command": "episodes",
                "provider": provider,
                "model": model,
                "data": str(data),
            },
            "trajectories": [t.model_dump() for t in all_trajectories],
        }
        out.write_text(json.dumps(payload, indent=2))
        typer.echo(f"\nWrote {len(all_trajectories)} trajectories to {out}")


@app.command("convert-bfcl")
def convert_bfcl(
    function_file: Path = typer.Argument(..., help="BFCL function file (questions + tools)."),
    answer_file: Path = typer.Argument(..., help="BFCL possible_answer file (ground truth)."),
    out: Path = typer.Option(..., help="Write portable JSONL here."),
    category: str = typer.Option("simple", help="Category label for these tasks."),
) -> None:
    """Convert native BFCL files into orchbench's portable JSONL format."""
    tasks = load_bfcl_native(function_file, answer_file, category=category)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(t.model_dump_json() + "\n" for t in tasks))
    typer.echo(f"Wrote {len(tasks)} tasks to {out}  (then: orchbench compare --data {out} ...)")


@app.command("list")
def list_() -> None:
    """List available orchestrators, providers and suites."""
    installed = set(available_orchestrators())
    rows = [f"{n} (installed)" if n in installed else f"{n} (needs extra)" for n in ALL_NAMES]
    typer.echo("orchestrators: " + ", ".join(rows))
    typer.echo("providers: mock (default), anthropic")
    typer.echo("mock profiles: " + ", ".join(PROFILES))
    typer.echo("suites: bfcl (portable JSONL + native BFCL loader)")


if __name__ == "__main__":  # pragma: no cover
    app()
