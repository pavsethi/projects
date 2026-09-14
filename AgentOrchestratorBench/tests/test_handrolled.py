from orchbench.orchestrators.handrolled import HandRolledOrchestrator, _parse_text_fallback
from orchbench.providers.base import LLMProvider
from orchbench.types import LLMRequest, ModelResponse, PredictedCall, Task, ToolSpec


def _task() -> Task:
    return Task(
        id="t1",
        suite="bfcl",
        query="weather in SF",
        tools=[ToolSpec(name="get_weather")],
        ground_truth=[],
    )


class _StructuredProvider:
    name = "stub"

    async def complete(self, request: LLMRequest) -> ModelResponse:
        return ModelResponse(
            tool_calls=[PredictedCall(name="get_weather", args={"location": "SF"})],
            prompt_tokens=100,
            completion_tokens=20,
            latency_ms=50.0,
        )


class _TextProvider:
    name = "stub-text"

    async def complete(self, request: LLMRequest) -> ModelResponse:
        return ModelResponse(
            text='Here you go: [{"name": "get_weather", "arguments": {"location": "SF"}}]',
            prompt_tokens=90,
            completion_tokens=15,
            latency_ms=40.0,
        )


class _FlakyEmptyProvider:
    """Empty on first call, valid on retry -- exercises the retry path."""

    name = "flaky"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, request: LLMRequest) -> ModelResponse:
        self.calls += 1
        if self.calls == 1:
            return ModelResponse(
                tool_calls=[], prompt_tokens=80, completion_tokens=0, latency_ms=30.0
            )
        return ModelResponse(
            tool_calls=[PredictedCall(name="get_weather", args={"location": "SF"})],
            prompt_tokens=85,
            completion_tokens=18,
            latency_ms=35.0,
        )


class _ErrorProvider:
    name = "err"

    async def complete(self, request: LLMRequest) -> ModelResponse:
        return ModelResponse(error="503 overloaded", latency_ms=10.0)


def test_isinstance_of_protocol():
    assert isinstance(_StructuredProvider(), LLMProvider)


async def test_structured_tool_calls():
    out = await HandRolledOrchestrator().route(_task(), _StructuredProvider())
    assert out.error is None
    assert out.predicted[0].name == "get_weather"
    assert out.total_tokens == 120
    assert out.llm_calls == 1


async def test_text_fallback_parsing():
    out = await HandRolledOrchestrator().route(_task(), _TextProvider())
    assert out.predicted[0].name == "get_weather"
    assert out.predicted[0].args == {"location": "SF"}


async def test_retry_recovers_empty_response():
    provider = _FlakyEmptyProvider()
    out = await HandRolledOrchestrator(max_retries=1).route(_task(), provider)
    assert out.predicted  # recovered on the retry
    assert out.llm_calls == 2
    assert out.total_tokens == 80 + 85 + 18  # tokens accrue across attempts


async def test_provider_error_is_captured_not_raised():
    out = await HandRolledOrchestrator().route(_task(), _ErrorProvider())
    assert out.error == "503 overloaded"
    assert out.predicted == []


def test_parse_fallback_handles_garbage():
    assert _parse_text_fallback("no json here") == []
    assert _parse_text_fallback('{"name": "x", "args": {"a": 1}}')[0].name == "x"
