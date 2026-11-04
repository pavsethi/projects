"""The sweep runner.

Runs an orchestrator over a list of tasks against a provider, grading each
result and bounding concurrency. Orchestrators and providers are async, so a
sweep of hundreds of tasks overlaps its I/O instead of blocking on each call --
the difference between a benchmark that finishes in a minute and one that takes
an hour.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from orchbench.backends import get_backend
from orchbench.episode import summarize_goal
from orchbench.grading import grade_output
from orchbench.orchestrators.base import EpisodeOrchestrator, Orchestrator
from orchbench.providers.base import LLMProvider
from orchbench.providers.retry import is_fatal_account_error
from orchbench.types import RunResult, Scenario, Task, Trajectory


class FatalProviderError(RuntimeError):
    """Raised to abort a sweep on a provider error that will recur for every call.

    An exhausted credit balance, a bad API key or revoked model access are not
    per-scenario outcomes -- once they strike, every remaining call fails the same
    way. Recording them as ``PROVIDER_ERROR`` trajectories would silently corrupt
    the headline accuracy (a dead account reads as "~20% of scenarios failed"), so
    the runner raises this instead: the sweep stops before spending more on doomed
    calls, the offending trajectory is never checkpointed, and the operator can fix
    the account and ``--resume`` the rest.
    """

    def __init__(self, orchestrator: str, scenario_id: str, error: str) -> None:
        self.orchestrator = orchestrator
        self.scenario_id = scenario_id
        self.error = error
        super().__init__(f"fatal provider error on {orchestrator}/{scenario_id}: {error}")


def _aborting_error(traj: Trajectory) -> str | None:
    """The provider-error text that ended a trajectory, if it ended on one."""
    if traj.stop_reason != "provider_error":
        return None
    for turn in reversed(traj.turns):
        if turn.error:
            return turn.error
    return None


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
        return await self.run_matrix([orchestrator], scenarios, lambda _name: provider, seed=seed)

    async def run_matrix(
        self,
        orchestrators: list[EpisodeOrchestrator],
        scenarios: list[Scenario],
        provider_for: Callable[[str], LLMProvider],
        *,
        seed: int = 0,
        skip: set[tuple[str, str]] | None = None,
        on_result: Callable[[Trajectory], None] | None = None,
    ) -> list[Trajectory]:
        """Run every orchestrator on every scenario, interleaved.

        Work is scheduled scenario-major (each scenario runs on all
        orchestrators back to back), so API load and network conditions drift
        equally across orchestrators instead of confounding their latency, and
        the starting orchestrator rotates per scenario (counterbalancing).
        ``skip`` holds (orchestrator, scenario_id) pairs already done (resume);
        ``on_result`` fires as each trajectory completes (checkpointing).
        """
        semaphore = asyncio.Semaphore(self.concurrency)
        done = skip or set()

        async def run_one(orch: EpisodeOrchestrator, scenario: Scenario) -> Trajectory:
            backend = get_backend(scenario.backend)
            async with semaphore:
                traj = await orch.run_episode(scenario, provider_for(orch.name), backend)
            traj.seed = seed
            # Attach human-readable context so the trajectory is self-describing.
            if not traj.instruction and scenario.user_turns:
                traj.instruction = scenario.user_turns[0]
            if not traj.goal_summary:
                traj.goal_summary = summarize_goal(scenario)
            # Abort the whole sweep on an account/credential fault rather than
            # checkpointing a doomed trajectory (it must stay un-done so --resume
            # retries it once the account is fixed).
            err = _aborting_error(traj)
            if err is not None and is_fatal_account_error(err):
                raise FatalProviderError(orch.name, scenario.id, err)
            if on_result is not None:
                on_result(traj)
            return traj

        # Counterbalance: rotate which orchestrator goes first on each scenario.
        # At prompt parity their first requests share a prefix, so whoever runs
        # first pays the provider prompt-cache write and the others read it
        # cheaply (and faster); rotating spreads that advantage evenly.
        n = len(orchestrators)
        pairs = [
            (orch, scenario)
            for i, scenario in enumerate(scenarios)
            for orch in orchestrators[i % n :] + orchestrators[: i % n]
            if (orch.name, scenario.id) not in done
        ]
        if not pairs:
            return []
        # Fail fast: a FatalProviderError from any episode means every remaining
        # call would fail too, so cancel the rest and re-raise instead of letting
        # asyncio.run tear down the loop with orphaned, still-billing tasks.
        tasks = [asyncio.create_task(run_one(o, s)) for o, s in pairs]
        completed, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        fatal = next((t.exception() for t in completed if t.exception() is not None), None)
        if fatal is not None:
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            raise fatal
        return [task.result() for task in tasks]
