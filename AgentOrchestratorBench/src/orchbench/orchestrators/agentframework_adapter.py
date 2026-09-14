"""Optional Microsoft Agent Framework adapter (import-guarded).

Install with ``pip install -e '.[agentframework]'``.

Microsoft Agent Framework is the unified successor to Semantic Kernel and
AutoGen. Its Python SDK is newer than the .NET side, so treat this adapter as a
skeleton to validate against the SDK version you install: the tool-registration
and result-extraction calls are the parts most likely to shift between betas,
and they are isolated in :meth:`_extract_calls` for exactly that reason.

Like the LangGraph adapter, this drives the framework over the harness's shared
provider seam so the *orchestration* is what is compared, not the backend.
"""

from __future__ import annotations

from orchbench.providers.base import LLMProvider
from orchbench.types import OrchestratorOutput, PredictedCall, Task


def _require_agent_framework() -> None:
    try:
        import agent_framework  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only with extra
        raise ImportError(
            "The agentframework extra is required: pip install -e '.[agentframework]'"
        ) from exc


class AgentFrameworkOrchestrator:
    """Route tasks through Microsoft Agent Framework over the shared provider."""

    def __init__(self, model: str = "mock-model") -> None:
        _require_agent_framework()
        self.name = "agentframework"
        self.model = model

    @staticmethod
    def _extract_calls(result: object) -> list[PredictedCall]:  # pragma: no cover
        """Pull tool calls out of an Agent Framework run result.

        Isolated here because this is the shape most likely to change across
        SDK betas. Adjust to match the ``agent-framework`` version you pin.
        """
        calls: list[PredictedCall] = []
        for message in getattr(result, "messages", []) or []:
            for item in getattr(message, "contents", []) or []:
                name = getattr(item, "name", None)
                if name is not None and hasattr(item, "arguments"):
                    args = item.arguments
                    calls.append(
                        PredictedCall(name=name, args=args if isinstance(args, dict) else {})
                    )
        return calls

    async def route(
        self, task: Task, provider: LLMProvider
    ) -> OrchestratorOutput:  # pragma: no cover
        # The concrete wiring (ChatAgent construction, tool registration from
        # task.tools, running with provider-backed chat client) is intentionally
        # left to be filled against your pinned SDK version. The contract this
        # must satisfy -- return an OrchestratorOutput, capture errors rather than
        # raising -- is fixed and exercised by the shared conformance test.
        raise NotImplementedError(
            "Wire AgentFrameworkOrchestrator.route to your pinned agent-framework "
            "version; see the module docstring and _extract_calls()."
        )
