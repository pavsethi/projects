# Design: multi-turn tool use

Status: **proposed** · Owner: main dev (Claude) · Reviewers: team · Target: `orchbench` v0.2

## 1. Why

The v0.1 single-step result is honest but anti-climactic: over the shared
provider seam, all three orchestrators route **identically** (same model + prompt
⇒ same tool choice). Single-step routing is a *model* property.

**Multi-turn is where orchestration frameworks actually diverge** — the agentic
loop. Who owns conversation state, how tool results feed back into the next
turn, how context grows, how errors are recovered, when the loop stops. A
hand-rolled `while` loop, a LangGraph state graph, and Microsoft Agent
Framework's function-invocation loop make genuinely different choices here. This
is the extension that makes the comparison *mean* something.

### Goals
- Scenarios where tools **return results** and the agent must act over several
  turns to reach a goal.
- Each orchestrator runs its **native** agentic loop over the shared provider +
  a shared, deterministic tool backend.
- **Goal-state grading** (did the world end in the right state?) plus process
  metrics that only exist multi-turn (turns-to-success, recovery rate, …).
- A **trajectory record** per task — the turn-by-turn log the UI workstream
  will render.
- Preserve every v0.1 virtue: **runs with zero API keys** (mock provider +
  in-process backends), hermetic tests, prompt parity, honest methodology.

### Non-goals (v0.2)
- An LLM **user simulator** (τ-bench style). v0.2 uses *scripted* user turns to
  stay deterministic/testable; the simulator is a documented v0.3 extension
  (§11).
- Real external side effects. Backends are in-process simulations only.
- Changing the single-step path. Multi-turn is additive; `route()` stays.

## 2. Vocabulary

- **Scenario** — a multi-turn task: an initial backend state, the available
  tools, one or more scripted user turns, and a success predicate.
- **ToolBackend** — a deterministic, in-process simulated world. Executes a
  predicted call against mutable state and returns a `ToolResult`.
- **Episode** — one orchestrator running one scenario to completion (goal
  reached, no tool call emitted, or max turns hit).
- **Trajectory** — the full record of an episode: every turn's calls, results,
  and a state snapshot. Consumed by grading, metrics, and the UI.

## 3. Data model (sketch)

New types in `orchbench/types.py` (pydantic, like the rest):

```python
class ToolResult(BaseModel):
    call_id: str
    ok: bool
    content: Any = None  # structured result the model sees
    error: str | None = None  # set when ok is False (e.g. bad args)


class Scenario(BaseModel):
    id: str
    suite: str = "multiturn"
    category: str = "multi_turn"
    tools: list[ToolSpec]
    user_turns: list[str]  # scripted; delivered one per "user" step
    backend: str  # registry key: which ToolBackend to build
    initial_state: dict[str, Any] = {}
    # success is checked by the backend's goal predicate against final state;
    # `goal` is backend-specific config (e.g. expected rows, required calls).
    goal: dict[str, Any] = {}
    max_turns: int = 8


class TurnRecord(BaseModel):
    index: int
    role: str  # "user" | "assistant"
    predicted: list[PredictedCall] = []
    results: list[ToolResult] = []
    text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    state_snapshot: dict[str, Any] = {}


class Trajectory(BaseModel):
    scenario_id: str
    orchestrator: str
    turns: list[TurnRecord]
    succeeded: bool  # goal predicate on final state
    stop_reason: str  # "goal" | "no_call" | "max_turns" | "error"
    failure_mode: FailureMode  # taxonomy, §8
    total_tokens: int
    total_latency_ms: float
    turns_to_success: int | None
```

## 4. Tool backend

```python
class ToolBackend(Protocol):
    name: str

    def reset(self, initial_state: dict) -> None: ...
    def execute(self, call: PredictedCall) -> ToolResult: ...  # mutates state
    def state(self) -> dict: ...  # snapshot
    def goal_reached(self, goal: dict) -> bool: ...  # success predicate
```

- **Deterministic and in-process** — no network, no clock, no randomness
  unless seeded. This is what keeps multi-turn hermetic.
- v0.2 ships **one reference backend**: a tiny stateful domain (proposal: a
  `kv_store`/`retail`-style world — create/update/query rows) rich enough to
  require ordered, dependent calls (e.g. "look up X, then update it"). Backends
  live in `orchbench/backends/` behind a registry so the team can add more.
- `execute` validates args against the tool schema and returns
  `ok=False, error=...` on bad input — the agent must *recover*, which is a
  first-class signal.

## 5. The agentic loop (where frameworks diverge)

A new capability on orchestrators, parallel to `route()`:

```python
async def run_episode(self, scenario, provider, backend) -> Trajectory: ...
```

The **shared contract** every implementation obeys (enforced by a conformance
test): same system prompt (prompt parity extended to multi-turn, via
`orchestrators/prompt.py`), same tools, same backend, same `max_turns`; capture
errors, never raise; one `TurnRecord` per step. Within that, each uses its
**native** machinery — the point of the comparison:

- **hand-rolled** — explicit `for turn in range(max_turns)` loop: build messages
  (system + user + prior turns + tool results) → `provider.complete` → parse
  calls → `backend.execute` each → append `tool` results → check
  `goal_reached` → repeat. The transparent baseline.
- **LangGraph** — a real graph: a model node and a `ToolNode` that calls the
  backend, with a conditional edge looping model→tools→model until no tool call
  or `max_turns`. Exercises LangGraph state + routing, not just one node.
- **Agent Framework** — register the backend's tools as framework functions and
  run its built-in function-invocation loop; our `BaseChatClient` (over the
  shared provider) drives the model turns. Exercises its native loop.

All three write the uniform `Trajectory`, so they're graded on equal terms.

## 6. Grading

- **Primary: goal-state.** `backend.goal_reached(scenario.goal)` on the final
  state → `succeeded`. This is the τ-bench-style end-state check and is the
  headline metric for multi-turn.
- **Secondary: required-calls** (optional per scenario) — did the trajectory
  contain the necessary calls, order-sensitive where the goal demands it.
- Argument-level grading reuses the existing `grading.py` matcher per call where
  a scenario specifies expected calls.

## 7. Metrics (new, in `metrics.py`)

Multi-turn unlocks metrics single-step can't express:

| Metric | Meaning |
|---|---|
| success rate | fraction of scenarios whose goal state was reached |
| turns-to-success | mean turns among successes (efficiency) |
| recovery rate | fraction of episodes that hit a tool error and still succeeded |
| invalid-call rate | tool calls rejected by the backend (bad args / unknown tool) |
| context growth | prompt-token growth per turn (how each framework manages history) |
| stall/loop rate | episodes that repeated a call with no state change |
| cost / latency per **completed** scenario | the honest efficiency number |

## 8. Failure taxonomy additions

Extend `FailureMode` for trajectories: `MAX_TURNS_EXCEEDED`, `NO_RECOVERY`
(errored and never recovered), `STALL_LOOP` (repeated no-op call),
`WRONG_ORDER` (right calls, dependency violated), `GAVE_UP` (stopped calling
before the goal). The single-step modes still apply per turn.

## 9. How it plugs into the existing harness

- **Loader:** `suites/multiturn.py` loads scenarios (portable JSONL, same spirit
  as the BFCL loader). A small hand-authored `data/multiturn_sample.jsonl`
  ships so it runs with no download.
- **Runner:** `Runner.run_episodes(orchestrator, scenarios, provider, backend)`
  mirrors `run_suite`; grading + metrics operate on `Trajectory`.
- **Results JSON** gains a `trajectories` array (full turn logs) → this is the
  contract the **UI / trajectory explorer** consumes. Freeze this schema early
  (§12) so the UI workstream can start in parallel.
- **CLI:** `orchbench compare --mode multiturn [--out results.json]`. Single-step
  stays the default mode.

## 10. Mock provider for multi-turn

`MockProvider` must now return *different* calls across turns. Extend fixtures to
key on `(task_id, turn_index)`, and add a **scripted-episode** profile that
walks a correct (or deliberately-flawed) trajectory so the whole loop, grader,
metrics, and taxonomy are exercised with **zero API keys**. The simulated
profiles (strong/balanced/weak) gain multi-turn variants that inject the new
failure modes (stall, no-recovery, wrong-order).

## 11. v0.3+ extensions (out of scope now, noted so the design leaves room)

- **LLM user simulator** — an LLM (via the provider seam) plays the user for
  open-ended follow-ups; gate behind a flag, keep scripted as the default so CI
  stays hermetic.
- **BFCL `multi_turn` category** ingestion once the backend abstraction is
  proven.
- **Second provider** (OpenAI/Gemini) — the loop is provider-agnostic by design,
  so this validates the seam under multi-turn too.

## 12. Milestones & team split

Dependency that gates everything: **freeze the `Trajectory` / results schema in
M1** so UI and metrics parallelize.

- **M1 — engine (main dev). ✅ done.** Types, `ToolBackend` + `records` backend,
  `run_episode` contract, hand-rolled loop (now the shared `episode.drive_episode`
  driver), goal-state grader, scripted mock profile, sample scenarios, tests.
  *Output: frozen trajectory schema.*
- **M2 — framework loops (main dev). ✅ done.** LangGraph runs a **real graph**
  (agent/tools nodes + conditional edge; the node reads `turn_index` from graph
  state and stamps it into the request, so the shared provider is driven exactly
  as elsewhere). Agent Framework reuses its native per-turn chat-client machinery
  inside the shared driver — its *own* multi-step loop builds requests internally,
  which would bypass the per-turn provider instrumentation (and the mock's turn
  keying), so, as for the single-step router, we drive the turn loop. `orchbench
  episodes` compares all three; v0.2 is one instruction + autonomous tool loop
  (multi-turn *tool use*), user-simulator conversations remain v0.3.
- **M3 — metrics & taxonomy (eng).** New metrics + failure modes + per-category
  rollups; depends on M1 schema.
- **M4 — UI / trajectory explorer (eng, parallel after M1).** Static report from
  results JSON: leaderboard + per-task turn-by-turn drill-down, color-coded by
  failure mode; GitHub Pages via CI.
- **M5 — real run + write-up (main dev).** Multi-turn `compare` on real Claude,
  update `RESULTS.md` with the first result where frameworks genuinely differ.

## 13. Risks

- **Scope creep** — the backend can balloon. Keep v0.2 to one small, sharp
  domain; resist realism for its own sake.
- **Grader strictness** — goal predicates must be unambiguous; document
  simplifications in `METHODOLOGY.md` as we did for the AST checker.
- **Context explosion / cost** — multi-turn real runs cost more; cap `max_turns`,
  keep `--effort low` available, and lean on the cache for re-runs.
- **Fairness regressions** — every framework must get identical prompt, tools,
  backend, and `max_turns`; extend `test_prompt_parity.py` to the episode path.

## 14. Definition of done (v0.2)

`orchbench compare --mode multiturn` runs all three orchestrators over the sample
scenarios on the mock provider with `pytest` green and no keys; the results JSON
carries full trajectories; `RESULTS.md` has a real multi-turn run showing where
the frameworks diverge; the trajectory explorer renders it.
