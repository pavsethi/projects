# Methodology

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
2. **Prompt parity (enforced).** All orchestrators build the *same* messages from
   one shared module (`orchestrators/prompt.py`) — identical system prompt, user
   query, and tool schemas — so the token/latency comparison isolates
   orchestration overhead, not prompt construction. (The first real run exposed
   why: before this, the hand-rolled router sent a system prompt while the
   framework adapters sent only the query, inflating the hand-rolled token count
   ~18%. `tests/test_prompt_parity.py` pins parity so it can't regress.)
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

6. **Native tool-call history.** Multi-turn history is structured (assistant
   tool calls with ids, then a tool-results message) and each provider maps it to
   its native format: for Anthropic, `tool_use` / `tool_result` blocks, with the
   model's raw content (including thinking blocks) replayed unchanged. An earlier
   version serialised calls and results as JSON text in ordinary messages, which
   is not how real agents talk to the API. `tests/test_multi_user_turn.py` pins
   that all three orchestrators send byte-identical request sequences.
7. **Run order is counterbalanced.** At prompt parity, orchestrators' first
   requests share a long prefix (BFCL's tool list), so whichever runs first pays
   the provider prompt-cache write and the others read it at 0.1x and faster.
   `episodes` runs each scenario on every orchestrator back to back (so API load
   drifts equally) and rotates which one goes first. Cross-orchestrator cost is
   compared **uncached** (`$ uncached`); billed cost is reported separately.

## BFCL multi-turn

`orchbench episodes --suite bfcl` runs BFCL v4's four multi-turn categories
(`base`, `miss_func`, `miss_param`, `long_context`; 200 scenarios each) through
every orchestrator. The data and the stateful APIs it runs against are vendored
from `bfcl-eval` 2026.3.23 under Apache-2.0 (`data/bfcl_multi_turn/`,
`src/orchbench/vendor/bfcl_multi_turn/`, with LICENSE and NOTICE).

**Faithful to BFCL's Claude function-calling path:**

- Same scenarios, user turns, initial API state and ground truth (unmodified).
- Same tools: docs converted exactly as BFCL's `convert_to_tool` does for Claude
  (type mapping, float hints, language hint, response schema folded into the
  description). Verified identical to upstream's output for all 128 tools.
- No system prompt (BFCL FC mode sends none); results returned as plain
  `tool_result` blocks without `is_error`, as BFCL does; consecutive user
  messages combined; `miss_func` functions withheld until their turn, which
  gets BFCL's "I have updated some more functions" prompt.
- Same loop: within a user turn the model calls tools until it stops; more than
  20 tool-calling steps in one turn force-quits the scenario (a failure).
- Same checker, ported: after each user turn with a non-empty ground truth, the
  model must have called something (empty-turn check), every public attribute of
  every API instance must equal the ground-truth replay's (state check), and
  every ground-truth result must appear among the model's results so far,
  unordered (response check). The first failing turn fails the scenario.
  Empty-ground-truth turns are not checked (BFCL's irrelevance checker exists
  upstream but is never called). Overall accuracy is the unweighted mean of the
  category accuracies.
- **Validation:** replaying the ground truth as the model's output passes all
  800 scenarios on every orchestrator, and targeted mutations (a wrong argument,
  a dropped read-only call, a silent turn, a runaway loop) each fail for the
  right reason (`tests/test_bfcl_multi_turn.py`).

**Deliberate divergences:**

- **No `eval()`.** BFCL builds a Python source string from each model call and
  `eval()`s it, guarded by a short name denylist. orchbench dispatches the
  structured call to a public method of an involved API instance
  (`method(**args)`), so argument strings are always data. Result and error
  strings are formatted exactly as BFCL's. Side effect: BFCL's regex that
  prefixes method names also rewrites look-alike text inside string arguments
  (e.g. `"echo(x)"`); orchbench passes such strings through unchanged.
- **Model settings are ours.** Leaderboard entries use their own per-model
  settings; orchbench uses `--effort` and adaptive thinking as configured, with
  prompt caching on. Scores share BFCL's protocol and grading, not necessarily
  the leaderboard's exact model configuration.
- **Prompt caching is automatic** (top-level `cache_control`) rather than
  BFCL's explicit breakpoints; this changes cost, not what the model sees.



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
