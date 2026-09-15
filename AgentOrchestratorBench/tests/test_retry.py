from orchbench.providers.retry import RetryProvider, is_transient
from orchbench.types import LLMRequest, ModelResponse, PredictedCall


async def _noop_sleep(_seconds: float) -> None:
    return None


class _FlakyProvider:
    """Fails transiently N times, then succeeds."""

    name = "flaky"

    def __init__(self, fail_times: int, error: str = "429 rate limit") -> None:
        self.fail_times = fail_times
        self.error = error
        self.calls = 0

    async def complete(self, request: LLMRequest) -> ModelResponse:
        self.calls += 1
        if self.calls <= self.fail_times:
            return ModelResponse(error=self.error)
        return ModelResponse(tool_calls=[PredictedCall(name="ok")])


def test_is_transient():
    assert is_transient("429 Too Many Requests")
    assert is_transient("Connection reset")
    assert is_transient("503 Service Unavailable")
    assert not is_transient("400 invalid_request: bad tool schema")
    assert not is_transient("authentication_error")


async def test_retries_then_succeeds():
    inner = _FlakyProvider(fail_times=2)
    provider = RetryProvider(inner, max_retries=3, sleep=_noop_sleep)
    resp = await provider.complete(LLMRequest(model="m", messages=[]))
    assert resp.error is None
    assert inner.calls == 3  # 2 failures + 1 success


async def test_gives_up_after_max_retries():
    inner = _FlakyProvider(fail_times=99)
    provider = RetryProvider(inner, max_retries=2, sleep=_noop_sleep)
    resp = await provider.complete(LLMRequest(model="m", messages=[]))
    assert resp.error is not None
    assert inner.calls == 3  # initial + 2 retries


async def test_non_transient_is_not_retried():
    inner = _FlakyProvider(fail_times=99, error="400 invalid_request")
    provider = RetryProvider(inner, max_retries=5, sleep=_noop_sleep)
    resp = await provider.complete(LLMRequest(model="m", messages=[]))
    assert resp.error is not None
    assert inner.calls == 1  # not retried
