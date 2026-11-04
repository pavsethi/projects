"""The sweep runner.

Runs an orchestrator over a list of tasks against a provider, grading each
result and bounding concurrency. Orchestrators and providers are async, so a
sweep of hundreds of tasks overlaps its I/O instead of blocking on each call --
the difference between a benchmark that finishes in a minute and one that takes
an hour.
"""

from __future__ import annotations

import asyncio

from orchbench.backends import get_backend
from orchbench.episode import summarize_goal
from orchbench.grading import grade_output
from orchbench.orchestrators.base import EpisodeOrchestrator, Orchestrator
from orchbench.providers.base import LLMProvider
from orchbench.types import RunResult, Scenario, Task, Trajectory


class Runner:
    """Execute a task sweep with bounded concurrency."""

    def __init__(self, concurrency: int = 8) -> None:
        self.concurrency = max(1, concurrency)

    async def run_suite(
        self,
        orchestrator: Orchestrator,
        tasks: list[Task],
        provider: LLMProvider,
        seed: int = 0,
    ) -> list[RunResult]:
        semaphore = asyncio.Semaphore(self.concurrency)

        async def run_one(task: Task) -> RunResult:
            async with semaphore:
                output = await orchestrator.route(task, provider)
            grade = grade_output(task, output)
            return RunResult(
                task_id=task.id,
                suite=task.suite,
                orchestrator=orchestrator.name,
                provider=getattr(provider, "name", "provider"),
                model=orchestrator.model,
                category=task.category,
                seed=seed,
                predicted=output.predicted,
                grade=grade,
                prompt_tokens=output.prompt_tokens,
                completion_tokens=output.completion_tokens,
                latency_ms=output.latency_ms,
                llm_calls=output.llm_calls,
            )

        return await asyncio.gather(*(run_one(task) for task in tasks))

    async def run_episodes(
        self,
        orchestrator: EpisodeOrchestrator,
        scenarios: list[Scenario],
        provider: LLMProvider,
        seed: int = 0,
    ) -> list[Trajectory]:
        """Run a multi-turn sweep. Each scenario gets a fresh backend instance."""
        semaphore = asyncio.Semaphore(self.concurrency)

        async def run_one(scenario: Scenario) -> Trajectory:
            backend = get_backend(scenario.backend)
            async with semaphore:
                traj = await orchestrator.run_episode(scenario, provider, backend)
            traj.seed = seed
            # Attach human-readable context so the trajectory is self-describing.
            if not traj.instruction and scenario.user_turns:
                traj.instruction = scenario.user_turns[0]
            if not traj.goal_summary:
                traj.goal_summary = summarize_goal(scenario)
            return traj

        return await asyncio.gather(*(run_one(s) for s in scenarios))
