# orchbench — a reproducible eval harness for agent orchestrators

[![orchbench CI](https://github.com/pavsethi/projects/actions/workflows/orchbench-ci.yml/badge.svg)](https://github.com/pavsethi/projects/actions/workflows/orchbench-ci.yml)

`orchbench` runs the **same task suite** through different agent orchestrators
(a hand-rolled router, LangGraph, Microsoft Agent Framework) and measures the
four things a real migration decision turns on:

- **routing accuracy** — does it call the right tool? (graded against BFCL)
- **token cost**
- **latency** (p50 / p95)
- **failure modes** — *why* it got things wrong, as a typed taxonomy

The headline isn't a leaderboard — framework leaderboards are the most-nitpicked
repos on GitHub, because someone can always say you "held framework X wrong." The
headline is the **harness**: a clean, typed seam that any orchestrator plugs
into, an objective grader, a failure-mode taxonomy, and enough reproducibility
plumbing (deterministic seeds, response caching, a zero-key mock provider) that
anyone can re-run it. The three-way comparison is a *demonstration* of the
harness, not the point of it.

> **Why this exists.** I spent three years building agentic AI apps in C# on
> Microsoft Semantic Kernel / Agent Framework. This is the eval infrastructure
> I wish I'd had when weighing one orchestration approach against another —
> rebuilt in Python, framework-agnostic, and honest about its own limits.

**Real run** (Sonnet 5, 100 BFCL tasks, all three orchestrators at prompt
parity): routing is **identical** across frameworks (99% / 95% exact) — as the
shared-provider design predicts, orchestration doesn't change the model's tool
choice. Full numbers, interpretation, and the honest caveats (including a
caching artifact the harness surfaced): **[`RESULTS.md`](RESULTS.md)**.

## Runs in 30 seconds, no API keys

```bash
pip install -e ".[dev]"
pytest -q                 # hermetic: everything runs on the mock provider
orchbench demo            # full pipeline over the sample suite, synthetic numbers
```

`orchbench demo` runs the hand-rolled orchestrator over the bundled BFCL-style
sample across three **simulated model tiers**, printing routing/exact accuracy,
cost, latency, cross-seed variance, and the failure-mode breakdown:

```
=== handrolled/strong  (n=55, seeds=5) ===
  routing accuracy :  94.5%
  exact accuracy   :  90.9%
  tokens/task      :    ...
  est. cost (USD)  : $...
  latency ms       : p50=... p95=... mean=...
  by category:
    simple     n=25  routing= 96.0%  exact= 96.0%
    multiple   n=15  routing= ...     exact= ...
    parallel   n=15  routing= ...     exact= ...
  routing accuracy std across seeds: ±...pp
```

> The demo uses the deterministic **mock** provider. Its numbers are **synthetic**
> — they exercise the harness end-to-end; they are *not* real model results. Real
> numbers come from a real provider (below).

## Real runs

```bash
pip install -e ".[anthropic]"
export ANTHROPIC_API_KEY=...
orchbench run --provider anthropic --model claude-sonnet-5 \
              --data data/bfcl_sample.jsonl --out results/sonnet.json
orchbench report results/sonnet.json
```

Point `--data` at the real [BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html)
dataset via the native loader (see `METHODOLOGY.md`) for a full run. Real-provider
runs are wrapped in `RetryProvider` (transient 429/5xx) + `CachingProvider`
(resumable, free re-runs); tune model behaviour with `--thinking/--no-thinking`
and `--effort`.

## Comparing orchestrators

```bash
pip install -e ".[langgraph,agentframework]"   # make both adapters available
orchbench compare                              # every installed orchestrator, same suite
orchbench compare --provider anthropic --model claude-sonnet-5 --out results/real.json
```

`orchbench compare` runs each available orchestrator over one dataset and prints
the comparison. Every orchestrator is driven over the **same provider seam** and
sends the **same prompt** (enforced — see `METHODOLOGY.md`), so differences
reflect orchestration, not the backend or prompt construction. `--out` saves all
graded results; `--seeds N` runs N seeds (caching auto-disables so samples stay
independent). `orchbench list` shows which adapters are installed.

**Full BFCL run:** convert the native dataset once, then point `--data` at it:

```bash
orchbench convert-bfcl BFCL_v3_simple.json possible_answer/BFCL_v3_simple.json \
          --out data/bfcl_simple.jsonl
orchbench compare --provider anthropic --model claude-sonnet-5 \
          --data data/bfcl_simple.jsonl --out results/bfcl_simple.json
```

## Architecture

```
             ┌──────────────┐     one async seam every backend speaks
 Task ──────▶│ Orchestrator │────────────────┐
 (BFCL item) └──────────────┘                 ▼
   │          handrolled / langgraph /   ┌───────────┐   mock (no keys) │
   │          agentframework             │ LLMProvider│──▶ anthropic     │
   │                                     └───────────┘   caching wrapper │
   │                                          │
   ▼                                          ▼
 ground truth ─────────▶  grading  ◀────  predicted calls
 (possible-answer sets)   (routing + exact)      │
                              │                   ▼
                              ▼            failure taxonomy
                          RunResult ──▶ metrics (accuracy/cost/latency/failures)
```

Key seams:

| Piece | File | What it is |
|-------|------|------------|
| Provider interface | `providers/base.py` | one async `complete()` every backend implements |
| Mock/replay provider | `providers/mock.py` | deterministic, seeded — the zero-key path |
| Caching | `providers/cache.py` | content-addressed, so re-runs are free |
| Retry/backoff | `providers/retry.py` | exponential backoff + jitter on transient 429/5xx |
| Orchestrator interface | `orchestrators/base.py` | `route(task, provider) → output` |
| Hand-rolled router | `orchestrators/handrolled.py` | the reference system under test |
| BFCL suite | `suites/bfcl.py` | portable JSONL + native BFCL loader |
| Grader | `grading.py` | routing vs. exact, BFCL possible-answer sets |
| Failure taxonomy | `failures.py` | why a task was wrong |
| Metrics | `metrics.py` | accuracy, token cost, latency percentiles |

## Adding an orchestrator

Implement the `Orchestrator` protocol — `name`, `model`, and an async
`route(task, provider)` that returns an `OrchestratorOutput`. Drive it over the
shared `provider` seam so it's graded on equal terms with the others, register
it in `orchestrators/__init__.py`, and it's in the comparison. The LangGraph and
Agent Framework adapters are worked examples.

## Status

All three orchestrators are implemented and tested end-to-end over the shared
provider: **hand-rolled**, **LangGraph** (`.[langgraph]`), and **Microsoft Agent
Framework** (`.[agentframework]`). Each framework adapter drives the framework's
own request/response machinery over our `LLMProvider`, so a comparison isolates
orchestration rather than the backend. The Anthropic provider is complete behind
its extra. See `METHODOLOGY.md` for grading details, fairness caveats, and how to
run against real BFCL.

## License

MIT.
