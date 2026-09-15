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
