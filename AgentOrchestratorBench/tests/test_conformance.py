"""Contract tests every orchestrator must satisfy.

The harness grades a hand-rolled router and heavyweight framework graphs on
equal terms, which only works if they all honour the same contract:
``route()`` returns an :class:`OrchestratorOutput` and *captures* provider
errors rather than raising. These tests pin that contract for the built-ins and
check that the optional adapters fail loudly (clean ImportError) when their
extra isn't installed, instead of half-importing.
"""

import pathlib

import pytest

from orchbench.orchestrators import BUILTIN
from orchbench.providers.mock import MockProvider, build_fixtures
from orchbench.suites.bfcl import load_jsonl
from orchbench.types import LLMRequest, ModelResponse, OrchestratorOutput

SAMPLE = pathlib.Path(__file__).resolve().parents[1] / "data" / "bfcl_sample.jsonl"


@pytest.fixture
def task():
    return load_jsonl(SAMPLE)[0]


@pytest.mark.parametrize("name", sorted(BUILTIN))
async def test_builtin_returns_output_on_success(name, task):
    orch = BUILTIN[name]()
    provider = MockProvider(build_fixtures([task], "strong", seed=0))
    out = await orch.route(task, provider)
    assert isinstance(out, OrchestratorOutput)
    assert out.error is None


@pytest.mark.parametrize("name", sorted(BUILTIN))
async def test_builtin_captures_provider_error(name, task):
    orch = BUILTIN[name]()

    class _Boom:
        name = "boom"

        async def complete(self, request: LLMRequest) -> ModelResponse:
            return ModelResponse(error="503 overloaded")

    out = await orch.route(task, _Boom())
    assert isinstance(out, OrchestratorOutput)
    assert out.error is not None
    assert out.predicted == []


@pytest.mark.parametrize(
    "factory_path",
    [
        "orchbench.orchestrators.langgraph_adapter:LangGraphOrchestrator",
        "orchbench.orchestrators.agentframework_adapter:AgentFrameworkOrchestrator",
    ],
)
def test_optional_adapters_require_their_extra(factory_path):
    import importlib

    module_name, cls_name = factory_path.split(":")
    cls = getattr(importlib.import_module(module_name), cls_name)
    # Neither langgraph nor agent_framework is installed in the dev env, so the
    # import guard must raise a clear ImportError at construction time.
    with pytest.raises(ImportError):
        cls()
