# Results

Real runs (Anthropic provider) comparing all three orchestrators at **prompt
parity**, against a live model. These are real numbers, unlike the synthetic
`orchbench demo`. Two runs so far:

> **Cost correction (2026-11):** earlier versions of this page priced Sonnet 5 at
> $3/$15 per million tokens; the current list price is **$2/$10**, so every cost
> figure here was ~50% too high. Costs below are recomputed at current prices.

1. [Single-step routing](#part-1--single-step-routing-bfcl) — BFCL, 100 tasks.
2. [Multi-turn tool use](#part-2--multi-turn-tool-use-v02) — 4 scenarios × 3
   orchestrators, full trajectories committed.

# Part 1 — Single-step routing (BFCL)

## Run

| Setting | Value |
|---|---|
| Command | `orchbench compare --provider anthropic --model claude-sonnet-5 --effort low` |
| Model | `claude-sonnet-5` |
| Suite | BFCL `simple` prompts (executable-category subset) — **100 tasks** |
| Seeds | 1 |
| Orchestrators | hand-rolled, LangGraph, Microsoft Agent Framework (prompt parity enforced) |

## Headline

| Orchestrator | Routing | Exact | Tokens/task | Est. cost | p95 latency* |
|---|--:|--:|--:|--:|--:|
| handrolled | 99.0% | 95.0% | 826.5 | $0.235 | 1999 ms |
| langgraph | 99.0% | 95.0% | 826.5 | $0.235 | 1999 ms* |
| agentframework | 99.0% | 95.0% | 826.5 | $0.235 | 1999 ms* |

Failure modes (identical across all three): **4 `wrong_args`, 1
`empty_response`** — i.e. 0 routing errors, and every miss was an argument-level
slip, not a wrong tool.

## What this shows

- **Orchestration does not change routing.** At prompt parity over the same
  model, all three orchestrators produce identical routing accuracy (99%),
  exact accuracy (95%), and token cost. This is the expected result and the
  central validation of the harness design: routing is a property of the
  *model + prompt*, driven over the shared provider seam — the framework wrapped
  around it doesn't move it. A framework comparison therefore has to live in the
  *operational* metrics (latency, overhead, failure handling), not accuracy.
- **Sonnet 5 is strong at single-tool routing** — 99% routing on 100 tasks, with
  the only exact-match losses being argument formatting (`wrong_args`).

## Honest caveat (\*the latency column)

This run **shared one response cache across the three orchestrators.** Because
prompt parity makes every orchestrator issue byte-identical requests, LangGraph
and Agent Framework were served entirely from the hand-rolled run's cache — so
they cost ≈$0 (the ~$0.24 is one orchestrator's real calls, not three) and
**inherited its latency**. The latency column is therefore *not* an independent
per-framework measurement here.

This was a harness bug, now fixed: `compare` namespaces the cache **per
orchestrator** (`cache_dir/<name>`), so each orchestrator makes its own calls
while re-runs stay resumable. Isolating genuine framework latency overhead needs
a re-run on the fixed version (or `--no-cache`); the accuracy and token findings
above are unaffected (they're identical by parity regardless of caching).

## Scope

- **n = 100, one seed, one model, one category** — real and directional, not a
  full leaderboard. For publishable cross-model conclusions: run the full BFCL
  AST categories (`simple` + `multiple` + `parallel`) across multiple seeds and
  models, on the cache-namespaced version, and report latency then.

## Reproduce

```bash
pip install -e ".[anthropic,langgraph,agentframework]"
export ANTHROPIC_API_KEY=...
orchbench convert-bfcl BFCL_v4_simple.jsonl BFCL_v4_simple_answer.jsonl \
          --out data/bfcl_simple.jsonl
orchbench compare --provider anthropic --model claude-sonnet-5 \
          --data data/bfcl_simple.jsonl --effort low --out results/bfcl_simple.json
```

# Part 2 — Multi-turn tool use (v0.2)

Each agent gets one instruction (*"Close the ticket about the payment page."*)
and must reach a goal state in a small records system by chaining tool calls —
typically `search_records` → `update_record`. Grading is **goal-state**: did the
backend end up in the required state, not did the transcript match a script.
See [`docs/multi-turn.md`](docs/multi-turn.md).

> **Not BFCL multi-turn.** These are 4 small hand-written scenarios that check the
> multi-turn harness works end to end. They are **not comparable** to the BFCL
> leaderboard's Multi Turn column (~60–68% for top models), which uses hundreds
> of scenarios over large stateful APIs, missing-parameter and missing-function
> cases, and long multi-step chains. BFCL's own multi-turn categories are now
> supported (`orchbench episodes --suite bfcl`, see `METHODOLOGY.md` → BFCL
> multi-turn); that real run is the next result.

## Run

| Setting | Value |
|---|---|
| Command | `orchbench episodes --provider anthropic --model claude-sonnet-5 --effort low` |
| Scenarios | `data/multiturn_sample.jsonl` — 4 (ship order, bump priority, cancel subscription, close ticket) |
| Seeds | 1 |
| Raw data | [`docs/runs/multiturn-sonnet-5.json`](docs/runs/multiturn-sonnet-5.json) — all 12 trajectories, every turn |
| Total spend | ≈ $0.06 |

## Headline

| Orchestrator | Success | Avg turns | Invalid calls | Recovery | Tokens/run | Cost | Mean model-turn latency |
|---|--:|--:|--:|--:|--:|--:|--:|
| handrolled | 4/4 | 2.25 | 0% | n/a | 1,943 | $0.021 | 1,504 ms |
| langgraph | 4/4 | 2.00 | 0% | n/a | 1,706 | $0.019 | 1,545 ms |
| agentframework | 4/4 | 2.25 | 0% | n/a | 1,936 | $0.021 | 1,319 ms |

Recovery is **n/a**, not 0%: no run hit a tool error, so there was nothing to
recover from. (The harness used to report 0% here; that was fixed for this
write-up because it reads as "never recovers".)

## What this shows

- **No framework difference on this suite.** All 12 runs reached the goal with
  zero rejected tool calls. Sonnet 5 saturates these scenarios: each is an
  unambiguous two-step lookup-then-write, so there is nothing for the
  orchestration layer to get right or wrong.
- **The one divergence is model sampling, not the framework.** On
  `close_ticket`, hand-rolled and Agent Framework inserted a harmless
  `get_record` check before the update (3 turns); LangGraph went straight to
  the update (2 turns). That explains the 2.25 vs 2.00 average and LangGraph's
  ~12% lower token count. It is not a framework effect: at the decision point
  all three sent the model an **identical 809-token prompt** (visible in the raw
  trajectories), so the different choice came from sampling the same input.
  With one seed, it would be wrong to attribute it to LangGraph.
- **Latency isn't separable yet.** Agent Framework's model turns averaged
  ~200 ms faster, but the orchestrators ran one after another, so this is
  confounded with API load over time. The adapters' own in-process overhead is
  sub-millisecond next to ~1.3–1.6 s model calls. Separating genuine framework
  overhead needs interleaved runs across multiple seeds.

## Scope and next step

**n = 4 scenarios, one seed, one model.** Treat this as an end-to-end
validation that the multi-turn harness works against a live model, not a
framework ranking. The scenarios are too easy to discriminate. The next
iteration needs scenarios that can actually fail: ambiguous names
(two matching records), injected tool errors that force recovery, longer
chains, and a goal that requires reading before writing. Plus several seeds,
interleaved, to put error bars on turns and latency.

## Reproduce

```bash
pip install -e ".[anthropic,langgraph,agentframework]"
echo "ANTHROPIC_API_KEY=..." > .env   # gitignored; or export it
orchbench episodes --provider anthropic --model claude-sonnet-5 --effort low \
          --out results/multiturn.json
```
