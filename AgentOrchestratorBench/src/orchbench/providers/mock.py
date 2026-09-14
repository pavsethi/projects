"""Deterministic mock / replay provider.

This is what makes the repo runnable with zero API keys and makes the test suite
hermetic. Two ways to use it:

* **Replay** -- construct with an explicit ``{task_id: ModelResponse}`` map. This
  is what tests use, and what a real "record real API responses once, replay
  forever" workflow would use.
* **Simulated** -- :func:`build_fixtures` generates responses for a whole suite
  from a quality *profile* (per-failure-mode probabilities), seeded so results
  are byte-for-byte reproducible.

The simulated path produces **synthetic** numbers: it is for exercising and
demonstrating the metrics + failure-taxonomy pipeline, not for drawing
conclusions about real frameworks. Real numbers require a real provider. Every
surface that prints simulated results says so.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from orchbench.grading import OPTIONAL
from orchbench.types import GroundTruthCall, LLMRequest, ModelResponse, PredictedCall, Task


@dataclass
class QualityProfile:
    """Per-task probabilities of each failure mode, plus cost/latency shape.

    Probabilities are applied in priority order; the first that fires decides the
    outcome, so they need not sum to 1. Whatever is left over is a correct call.
    """

    name: str = "balanced"
    p_provider_error: float = 0.01
    p_empty: float = 0.01
    p_hallucinate: float = 0.01
    p_wrong_tool: float = 0.04
    p_missing_call: float = 0.02
    p_extra_call: float = 0.02
    p_wrong_args: float = 0.06
    # Latency (ms) modelled as a clipped normal; tokens as a base + per-tool cost.
    latency_mean_ms: float = 650.0
    latency_std_ms: float = 180.0
    prompt_tokens_base: int = 320
    prompt_tokens_per_tool: int = 45
    completion_tokens_mean: int = 60


# A few illustrative profiles so `orchbench demo` shows a spread of behaviour.
PROFILES: dict[str, QualityProfile] = {
    "strong": QualityProfile(
        name="strong",
        p_provider_error=0.005,
        p_empty=0.005,
        p_hallucinate=0.005,
        p_wrong_tool=0.02,
        p_missing_call=0.01,
        p_extra_call=0.01,
        p_wrong_args=0.03,
        latency_mean_ms=520.0,
        completion_tokens_mean=52,
    ),
    "balanced": QualityProfile(name="balanced"),
    "weak": QualityProfile(
        name="weak",
        p_provider_error=0.02,
        p_empty=0.03,
        p_hallucinate=0.03,
        p_wrong_tool=0.09,
        p_missing_call=0.05,
        p_extra_call=0.04,
        p_wrong_args=0.11,
        latency_mean_ms=900.0,
        latency_std_ms=300.0,
        completion_tokens_mean=78,
    ),
}


def _rng_for(task_id: str, seed: int) -> random.Random:
    """A per-(task, seed) RNG so fixtures are deterministic and independent."""
    digest = hashlib.sha256(f"{task_id}:{seed}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _concrete_call(truth: GroundTruthCall) -> PredictedCall:
    """Turn a ground-truth spec into one concrete, correct call."""
    args: dict[str, object] = {}
    for param, acceptable in truth.args.items():
        chosen = next((v for v in acceptable if v != OPTIONAL), None)
        if chosen is not None:
            args[param] = chosen
    return PredictedCall(name=truth.name, args=args)


def _perturb_args(call: PredictedCall, rng: random.Random) -> PredictedCall:
    if not call.args:
        # No args to break -- fall back to dropping into a bogus arg.
        return PredictedCall(name=call.name, args={"__bad__": "x"})
    param = rng.choice(list(call.args))
    bad = dict(call.args)
    original = bad[param]
    bad[param] = f"{original}_wrong" if isinstance(original, str) else "wrong"
    return PredictedCall(name=call.name, args=bad)


def _simulate(task: Task, profile: QualityProfile, seed: int) -> ModelResponse:
    rng = _rng_for(task.id, seed)
    correct = [_concrete_call(t) for t in task.ground_truth]
    other_tools = [t.name for t in task.tools if t.name not in {c.name for c in correct}]

    latency = max(1.0, rng.gauss(profile.latency_mean_ms, profile.latency_std_ms))
    prompt_tokens = profile.prompt_tokens_base + profile.prompt_tokens_per_tool * len(task.tools)
    completion_tokens = max(1, int(rng.gauss(profile.completion_tokens_mean, 12)))

    def resp(tool_calls: list[PredictedCall], *, error: str | None = None) -> ModelResponse:
        return ModelResponse(
            tool_calls=tool_calls,
            text="",
            prompt_tokens=0 if error else prompt_tokens,
            completion_tokens=0 if error else completion_tokens,
            latency_ms=latency,
            error=error,
        )

    # Irrelevance tasks (no ground-truth call): the correct action is to call
    # nothing; the model "fails" by making a spurious call.
    if not correct:
        spurious = profile.p_wrong_tool + profile.p_extra_call + profile.p_hallucinate
        if rng.random() < spurious and task.tools:
            return resp([PredictedCall(name=rng.choice([t.name for t in task.tools]), args={})])
        return resp([])

    roll = rng.random()
    cumulative = 0.0

    cumulative += profile.p_provider_error
    if roll < cumulative:
        return resp([], error="simulated provider error (429/timeout)")

    cumulative += profile.p_empty
    if roll < cumulative:
        return resp([])

    cumulative += profile.p_hallucinate
    if roll < cumulative:
        bad = list(correct)
        if bad:
            bad[0] = PredictedCall(name=f"{bad[0].name}_v2", args=bad[0].args)
        else:
            bad = [PredictedCall(name="nonexistent_tool", args={})]
        return resp(bad)

    cumulative += profile.p_wrong_tool
    if roll < cumulative and other_tools:
        bad = list(correct)
        bad[0] = PredictedCall(name=rng.choice(other_tools), args=bad[0].args if bad else {})
        return resp(bad)

    cumulative += profile.p_missing_call
    if roll < cumulative and len(correct) > 1:
        return resp(correct[:-1])

    cumulative += profile.p_extra_call
    if roll < cumulative:
        extra = PredictedCall(
            name=rng.choice(other_tools) if other_tools else correct[0].name,
            args={},
        )
        return resp([*correct, extra])

    cumulative += profile.p_wrong_args
    if roll < cumulative and correct:
        idx = rng.randrange(len(correct))
        bad = list(correct)
        bad[idx] = _perturb_args(bad[idx], rng)
        return resp(bad)

    return resp(correct)


def build_fixtures(
    tasks: list[Task],
    profile: QualityProfile | str = "balanced",
    seed: int = 0,
) -> dict[str, ModelResponse]:
    """Generate a deterministic ``{task_id: ModelResponse}`` map for a suite."""
    prof = PROFILES[profile] if isinstance(profile, str) else profile
    return {task.id: _simulate(task, prof, seed) for task in tasks}


class MockProvider:
    """Serves pre-computed responses keyed by ``request.metadata['task_id']``."""

    def __init__(self, fixtures: dict[str, ModelResponse], name: str = "mock") -> None:
        self._fixtures = fixtures
        self.name = name

    async def complete(self, request: LLMRequest) -> ModelResponse:
        task_id = request.metadata.get("task_id")
        if task_id is None or task_id not in self._fixtures:
            return ModelResponse(error=f"no mock fixture for task_id={task_id!r}")
        # Return a copy so callers can annotate (e.g. cached=True) safely.
        return self._fixtures[task_id].model_copy(deep=True)
