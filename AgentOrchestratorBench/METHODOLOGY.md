# Methodology

This document is the part a careful reader (or interviewer) will want: exactly
what is measured, how it is graded, what the numbers do and don't capture, and
how to reproduce them. The goal is that the harness is defensible even when its
conclusions are debated.

## What is measured

For each `(orchestrator, model, provider)` sweep over a task suite:

| Metric | Definition |
|--------|------------|
| **Routing accuracy** | Fraction of tasks where the orchestrator selected the correct tool(s), argument values ignored. This is the "did it route right" signal. |
| **Exact accuracy** | Routing correct **and** every argument value is acceptable. |
| **Tokens / task** | Mean prompt+completion tokens, retries included. |
| **Est. cost (USD)** | Tokens × a per-model price table (`metrics.PRICING`, editable). |
| **Latency** | p50 / p95 / mean wall-clock per task, retries included. |
| **Failure modes** | Distribution over the taxonomy below. |

Everything is also broken down by BFCL **category** (`simple`, `multiple`,
`parallel`) so you can see *where* accuracy is lost, not just the headline.

## The task suite: BFCL

We use the [Berkeley Function-Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
because its items are exactly "a query + available tools + the correct call,"
which is what routing accuracy needs, and because its ground truth is given as
**sets of acceptable values** per argument (a param can be satisfied by any of
several values, e.g. `{"unit": ["celsius", "C"]}`), which makes grading
objective without an LLM judge.

- `data/bfcl_sample.jsonl` is a small, hand-authored sample in a **portable
  one-task-per-line format** so the repo runs with no download.
- `suites/bfcl.load_bfcl_native(function_file, answer_file)` reads BFCL's own
  two-file layout. Fetch the dataset from the
  [gorilla repo](https://github.com/ShishirPatil/gorilla) (`berkeley-function-call-leaderboard`),
  which ships `BFCL_v*_<category>.json` (the `function` files) and matching
  `possible_answer/` files, and point the loader at a category pair.

Categories map directly: `simple` (one call), `multiple` (pick one of several
offered tools), `parallel` (several calls at once), and `irrelevance` (no tool
fits — the correct action is to call *nothing*; graded as correct iff no call is
emitted). Multi-turn is out of scope for v0.1 (routing is single-step here).

## Grading

Implemented in `grading.py` as a transparent re-implementation of BFCL's AST
checker:

- **Routing**: the multiset of predicted tool names equals the multiset of
  ground-truth names. Order-independent (BFCL `parallel` does not fix order).
- **Exact**: additionally, each ground-truth call is matched to a distinct
  predicted call whose every parameter value is in the acceptable set. A
  parameter whose acceptable set contains `""` is **optional** and may be
  omitted. Numeric string/number mismatches (`"5"` vs `5`) are tolerated because
  function-calling models routinely stringify numbers.

**Documented simplifications vs. the official BFCL checker** (so the numbers are
honest about scope): we do not deep-check nested object/array argument types,
enum-vs-freeform coercion beyond the numeric case, or Python-type-specific
matching; and we grade a single routing step, not multi-turn state. These make
our exact-accuracy a slightly *looser* upper bound than official BFCL — fine for
comparing orchestrators against each other under one ruleset, which is the point.

## Failure taxonomy

`failures.py` assigns each wrong result its single most-specific cause:

| Mode | Meaning |
|------|---------|
| `provider_error` | the LLM/provider call itself failed (429, timeout, 5xx) |
| `empty_response` | no tool call emitted at all |
| `parse_error` | response could not be parsed into a call |
| `hallucinated_tool` | called a tool not in the schema |
| `wrong_tool` | called a real but incorrect tool |
| `missing_call` | fewer calls than ground truth (e.g. missed a parallel call) |
| `extra_call` | more calls than ground truth |
| `wrong_args` | right tool(s), wrong argument value(s) |

This is the analytically useful output: two orchestrators at the same routing
accuracy can fail completely differently (one loses to `wrong_args`, another to
`provider_error`), and *that* is what informs a migration.

## Reproducibility

- **Seeds.** The mock provider is seeded per `(task_id, seed)`; sweeps are run
  over several seeds and we report cross-seed variance (std of routing accuracy).
  Real-provider runs should fix `temperature=0` and still run ≥3 seeds because
  function-calling is not fully deterministic.
- **Caching.** `providers/cache.py` is a content-addressed on-disk cache keyed on
  the exact request (model, messages, tools, temperature). Re-running a sweep
  after a crash, or two orchestrators that emit identical prompts, costs nothing
  the second time. Transient provider errors are never cached.
- **Cost control for real runs.** Cache aggressively; run the bulk on a cheap
  model tier and only a couple of seeds on an expensive one; the mock provider
  lets you validate the entire harness and your analysis code before spending a
  cent.

## Fairness caveats (read before trusting any cross-framework number)

1. **Same provider seam.** Every orchestrator is driven over the *same*
   `LLMProvider`, so differences reflect orchestration/control-flow, not a
   different backend. An adapter that quietly used a framework's built-in model
   client would invalidate the comparison — the adapters deliberately don't.
2. **Prompt parity.** Each orchestrator constructs its own prompt (that's part of
   what's being compared), but they see identical tools and queries. Report the
   prompts alongside results.
3. **Version pinning.** Framework behavior moves fast. Record exact versions of
   every framework and SDK with each result set.
4. **The mock demo is synthetic.** `orchbench demo` numbers come from a seeded
   error-injection model, not a real LLM. They exist to exercise the pipeline.
   Only `--provider anthropic` (or another real provider) produces real numbers.
5. **An abstention-forbidding prompt makes `irrelevance` unmeasurable.** The
   first real Sonnet-5 run scored 0% on `irrelevance` — not a model failure but a
   harness bug: the router's system prompt said "respond ONLY by calling tools",
   so it could never abstain. The prompt must *permit* not calling a tool, and a
   retry-on-empty must not re-prompt for a call (it would force one). An
   orchestrator that cannot abstain should simply not be scored on `irrelevance`
   rather than be recorded as 0%.

## Reproducing a real run

```bash
pip install -e ".[anthropic]"
export ANTHROPIC_API_KEY=...
# Convert a BFCL category to a run and grade it:
python - <<'PY'
from orchbench.suites.bfcl import load_bfcl_native
tasks = load_bfcl_native("BFCL_v3_simple.json", "possible_answer/BFCL_v3_simple.json")
# ... feed tasks to Runner with AnthropicProvider; see cli.run for the pattern.
PY
```
