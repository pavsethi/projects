"""orchbench: a reproducible eval harness for LLM agent orchestrators.

The public surface is intentionally small. Most users will interact with the
CLI (``orchbench``) or the :class:`~orchbench.runner.Runner`.
"""

from orchbench.types import (
    GradeResult,
    GroundTruthCall,
    LLMRequest,
    ModelResponse,
    OrchestratorOutput,
    PredictedCall,
    RunResult,
    Task,
    ToolSpec,
)

__all__ = [
    "GradeResult",
    "GroundTruthCall",
    "LLMRequest",
    "ModelResponse",
    "OrchestratorOutput",
    "PredictedCall",
    "RunResult",
    "Task",
    "ToolSpec",
]

__version__ = "0.1.0"
