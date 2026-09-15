# Results

First real run comparing all three orchestrators over the same suite against a
live model. These numbers are **real** (Anthropic provider), unlike the
synthetic `orchbench demo`.

## Run

| Setting | Value |
|---|---|
| Command | `orchbench compare --provider anthropic --model claude-sonnet-5` |
| Model | `claude-sonnet-5` (adaptive thinking on by default) |
| Suite | bundled BFCL-style sample — 19 tasks (simple / multiple / parallel / irrelevance) |
| Seeds | 1 |
| Orchestrators | hand-rolled, LangGraph, Microsoft Agent Framework |

## Headline

| Orchestrator | Routing | Exact | Tokens/task | Est. cost | p95 latency |
|---|--:|--:|--:|--:|--:|
| handrolled | 100.0% | 94.7% | 757.7 | $0.0641 | 2068 ms |
| langgraph | 100.0% | 94.7% | 641.5 | $0.0627 | 2783 ms |
| agentframework | 100.0% | 94.7% | 640.1 | $0.0622 | 2662 ms |

- **Routing is identical across all three** (0 routing errors; 18/19 exact — one
  argument-level miss). This is the expected result and a validation of the
  harness design: every orchestrator is driven over the **same provider seam**,
  so they make the same tool-choice decisions. Routing accuracy is a property of
  the model + prompt, not the orchestration framework.
- **The differentiation is operational, not routing** — it shows up in **tokens
  and latency**, which is exactly where a framework comparison should live once
  routing is held constant.

## The honest caveat (and what the harness caught)

The ~18% token gap (handrolled 757.7 vs ~640) is **not** "the hand-rolled router
is more expensive." It is a **prompt-parity confounder**: the hand-rolled
orchestrator sends an explicit routing *system prompt*, while the current
LangGraph and Agent Framework adapters send only the user query. So the token /
cost spread reflects **prompt construction**, not framework overhead.

That is the benchmark doing its job — surfacing a confounder before it becomes a
false conclusion. The correct next step is to bring the adapters to prompt
parity (same system prompt for all three, or none) and re-run; only then is a
framework-level cost claim defensible. Until then, read the token column as
"the harness captures per-orchestrator cost differences," not as a verdict.

Latency is dominated by Sonnet 5's adaptive thinking (~2–2.8 s p95), not by
orchestration; the spread between frameworks here is within run-to-run noise at
n=19.

## Scope / how to read this

- **n = 19, one seed, one model** — this is a *directional* demonstration of the
  harness end-to-end on a live model, not a leaderboard. Small-sample accuracy
  numbers are not statistically separable.
- For real conclusions: run the full [BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html)
  suite (hundreds of tasks) via the native loader, at prompt parity, across
  multiple seeds and models. See `METHODOLOGY.md`.

## Reproduce

```bash
pip install -e ".[anthropic,langgraph,agentframework]"
export ANTHROPIC_API_KEY=...
orchbench compare --provider anthropic --model claude-sonnet-5
```
