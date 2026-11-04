"""Core data model.

Everything that flows through the harness is a pydantic model so that runs are
serialisable to JSON, comparable across sessions, and validated at the seams.

The vocabulary, from the outside in:

* :class:`Task` -- one benchmark item: a query, the tools the model may call,
  and the ground-truth call(s) that count as correct.
* :class:`LLMRequest` / :class:`ModelResponse` -- the provider seam. Every
  provider (mock or real) speaks this dialect, which is what lets the whole
  harness run without API keys.
* :class:`OrchestratorOutput` -- what an orchestrator produces for one task,
  before grading.
* :class:`GradeResult` / :class:`RunResult` -- the graded outcome, ready to
  aggregate into metrics.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """A single callable tool exposed to the model (JSON-Schema parameters)."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class GroundTruthCall(BaseModel):
    """A correct call for a task.

    ``args`` maps each parameter to a *list of acceptable values*, mirroring
    BFCL's "possible answers" format: a param can be satisfied by any one of
    several values (e.g. ``{"unit": ["celsius", "C"]}``). An acceptable value of
    ``""`` marks the parameter as optional (the model may omit it).
    """

    name: str
    args: dict[str, list[Any]] = Field(default_factory=dict)


class PredictedCall(BaseModel):
    """A tool call actually emitted by an orchestrator."""

    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    # Provider-assigned call id (e.g. Anthropic ``tool_use.id``), used to pair a
    # tool result with its call in native tool-call history. None on mock/replay
    # providers; the episode driver assigns a deterministic id when absent.
    id: str | None = None


class Task(BaseModel):
    """One benchmark item."""

    id: str
    suite: str
    query: str
    tools: list[ToolSpec] = Field(default_factory=list)
    ground_truth: list[GroundTruthCall] = Field(default_factory=list)
    # BFCL-style category: "simple" (one call), "multiple" (pick one of several
    # tools), "parallel" (several calls at once). Used for per-category rollups.
    category: str = "simple"
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMRequest(BaseModel):
    """A provider-agnostic completion request."""

    model: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = Field(default_factory=list)
    temperature: float = 0.0
    # Generous default: current Claude models run adaptive thinking by default,
    # which can consume a small budget before the tool call is emitted.
    max_tokens: int = 4096
    # Carries the task id so replay/mock providers can look up a fixture. Real
    # providers ignore it.
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    """A provider-agnostic completion response."""

    tool_calls: list[PredictedCall] = Field(default_factory=list)
    text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    error: str | None = None
    # True when this response was served from cache (no billable call made).
    cached: bool = False
    # Prompt-cache accounting (subset of prompt_tokens): tokens read from /
    # written to the provider's prompt cache, billed at different rates.
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    # The provider's raw assistant content, replayed verbatim in later requests
    # (e.g. Anthropic thinking blocks must be passed back unchanged with their
    # tool_use blocks). Shape: {"provider": <name>, "content": [...]}.
    native: dict[str, Any] | None = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class OrchestratorOutput(BaseModel):
    """What an orchestrator produces for a single task, pre-grading."""

    predicted: list[PredictedCall] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    # Number of LLM round-trips the orchestrator made (retries included).
    llm_calls: int = 0
    error: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class FailureMode(str, Enum):
    """Taxonomy of ways a task can go wrong.

    The point of the harness is less the leaderboard than *why* a given
    orchestrator/model gets things wrong. These are assigned by
    :func:`orchbench.failures.classify`.
    """

    NONE = "none"
    PROVIDER_ERROR = "provider_error"  # the LLM/provider call itself failed
    EMPTY_RESPONSE = "empty_response"  # no tool call emitted at all
    PARSE_ERROR = "parse_error"  # response could not be parsed into a call
    HALLUCINATED_TOOL = "hallucinated_tool"  # called a tool not in the schema
    WRONG_TOOL = "wrong_tool"  # called a real but incorrect tool
    MISSING_CALL = "missing_call"  # fewer calls than the ground truth expects
    EXTRA_CALL = "extra_call"  # more calls than the ground truth expects
    WRONG_ARGS = "wrong_args"  # right tool(s), wrong argument value(s)

    # Multi-turn episode modes (see docs/multi-turn.md). Assigned by
    # :func:`orchbench.failures.classify_trajectory`.
    MAX_TURNS_EXCEEDED = "max_turns_exceeded"  # ran out of turns before the goal
    NO_RECOVERY = "no_recovery"  # hit a tool error and never recovered
    STALL_LOOP = "stall_loop"  # repeated a call with no state change
    WRONG_ORDER = "wrong_order"  # right calls, a dependency was violated
    GAVE_UP = "gave_up"  # stopped calling tools before reaching the goal

    # BFCL multi-turn checker verdicts (state + execution-response checks run
    # after each user turn; see orchbench.backends.bfcl).
    STATE_MISMATCH = "state_mismatch"  # world state differs from ground truth
    RESPONSE_MISMATCH = "response_mismatch"  # a ground-truth result never produced
    EMPTY_TURN = "empty_turn"  # made no call on a turn that required calls


class GradeResult(BaseModel):
    """Outcome of grading one orchestrator output against a task."""

    routing_correct: bool  # right tool(s) selected, argument values ignored
    exact_correct: bool  # right tool(s) AND all argument values acceptable
    failure_mode: FailureMode = FailureMode.NONE
    detail: str = ""


class RunResult(BaseModel):
    """A single graded task result -- the atom that metrics aggregate over."""

    task_id: str
    suite: str
    orchestrator: str
    provider: str
    model: str
    category: str
    seed: int = 0

    predicted: list[PredictedCall] = Field(default_factory=list)
    grade: GradeResult

    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    llm_calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


# --------------------------------------------------------------------------- #
# Multi-turn tool use (orchbench v0.2 — see docs/multi-turn.md).
# The single-step path above is unchanged; these are additive.
# --------------------------------------------------------------------------- #


class ToolResult(BaseModel):
    """The result of executing one predicted call against a tool backend."""

    call_id: str
    ok: bool
    content: Any = None  # structured result the model sees on the next turn
    error: str | None = None  # set when ok is False (bad args / unknown tool)
    # Whether the model is told the call errored (Anthropic ``is_error``).
    # None = "not ok". BFCL sets False: its runs never flag errors to the model;
    # the error text is just the result (``ok`` still drives our metrics).
    is_error: bool | None = None


class Scenario(BaseModel):
    """A multi-turn task: a stateful world plus scripted user turns and a goal."""

    id: str
    suite: str = "multiturn"
    category: str = "multi_turn"
    tools: list[ToolSpec] = Field(default_factory=list)
    user_turns: list[str] = Field(default_factory=list)  # scripted, one per user step
    backend: str = "records"  # registry key: which ToolBackend to build
    initial_state: dict[str, Any] = Field(default_factory=dict)
    # Goal is checked by the backend's predicate against final state; shape is
    # backend-specific (e.g. {"field_equals": [{"record", "field", "value"}]}).
    goal: dict[str, Any] = Field(default_factory=dict)
    # Cap on tool-calling model steps *per user turn* (exceeding it aborts the
    # episode, as BFCL's force-quit does).
    max_turns: int = 8
    # System prompt for the episode. None = orchbench's default multi-turn prompt;
    # "" = no system prompt (BFCL function-calling mode sends none).
    system_prompt: str | None = None
    # Tools that become available only from a given user turn (BFCL miss_func):
    # {user_turn_index: [ToolSpec, ...]}.
    tools_added: dict[int, list[ToolSpec]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TurnRecord(BaseModel):
    """One step of an episode: an assistant turn and the tool results it drove."""

    index: int
    user_turn: int = 0  # which scripted user turn this model step belongs to
    role: str = "assistant"
    predicted: list[PredictedCall] = Field(default_factory=list)
    results: list[ToolResult] = Field(default_factory=list)
    text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    latency_ms: float = 0.0
    error: str | None = None  # provider error on this turn, if any
    state_snapshot: dict[str, Any] = Field(default_factory=dict)


class Trajectory(BaseModel):
    """The full record of one orchestrator running one scenario.

    This is the frozen v0.2 schema the UI trajectory explorer consumes; keep it
    additive.
    """

    scenario_id: str
    suite: str = "multiturn"
    category: str = "multi_turn"
    orchestrator: str
    provider: str
    model: str
    seed: int = 0

    # Human-readable context (so a trajectory is self-describing in the UI /
    # a raw results file): the user instruction and a plain goal summary.
    instruction: str = ""
    goal_summary: str = ""

    turns: list[TurnRecord] = Field(default_factory=list)
    succeeded: bool = False
    stop_reason: str = ""  # "goal" | "no_call" | "max_turns" | "provider_error"
    failure_mode: FailureMode = FailureMode.NONE
    turns_to_success: int | None = None
    final_state: dict[str, Any] = Field(default_factory=dict)
    # Backend-specific grading detail, e.g. BFCL's failing user turn and checker
    # error type ({"failed_user_turn": 2, "error_type": "state_mismatch", ...}).
    grade_detail: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return sum(t.prompt_tokens + t.completion_tokens for t in self.turns)

    @property
    def total_latency_ms(self) -> float:
        return sum(t.latency_ms for t in self.turns)

    @property
    def n_turns(self) -> int:
        return len(self.turns)
