"""Agent Arena -- head-to-head AI coding agent benchmark.

Runs 50 tasks across 5 categories for each agent, measures quality,
budget, self-healing, and caching, then ranks agents with composite scores.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from armature._internal.types import AgentArenaResult, BenchmarkTaskResult
from armature.benchmark.runner import BenchmarkRunner
from armature.benchmark.scoring import aggregate_agent_results
from armature.benchmark.tasks import ArenaSuite, BenchmarkTask, load_arena_tasks
from armature.config.schema import ArmatureConfig


class AgentArena:
    """Orchestrate arena benchmarks across multiple agents."""

    def __init__(
        self,
        config: ArmatureConfig,
        suite: ArenaSuite | None = None,
    ) -> None:
        self.config = config
        self.suite = suite or load_arena_tasks(
            Path(config.benchmark.arena_tasks_path)
        )
        self.runner = BenchmarkRunner(config)

    def run_all(
        self,
        agents: list[str] | None = None,
        categories: set[str] | None = None,
        replay_dir: Path | None = None,
    ) -> list[AgentArenaResult]:
        """Run all tasks for all specified agents, return ranked results."""
        agent_names = agents or list(self.suite.agents.keys())
        tasks = self.suite.tasks
        if categories:
            tasks = [t for t in tasks if t.category in categories]

        all_task_results: dict[str, list[BenchmarkTaskResult]] = {}
        for agent in agent_names:
            all_task_results[agent] = self.run_agent(agent, tasks, replay_dir)

        # Find minimum cost across agents for efficiency normalization
        agent_costs = {
            agent: sum(r.budget_cost_usd for r in results)
            for agent, results in all_task_results.items()
        }
        positive_costs = [c for c in agent_costs.values() if c > 0]
        min_cost = min(positive_costs) if positive_costs else 0.0

        arena_results = []
        for agent in agent_names:
            result = aggregate_agent_results(
                agent,
                all_task_results[agent],
                min_cost,
                self.suite.scoring,
                self.suite.grades,
            )
            arena_results.append(result)

        # Sort by composite score descending
        arena_results.sort(key=lambda r: -r.composite_score)
        return arena_results

    def run_agent(
        self,
        agent: str,
        tasks: list[BenchmarkTask] | None = None,
        replay_dir: Path | None = None,
    ) -> list[BenchmarkTaskResult]:
        """Run all tasks for one agent."""
        task_list = tasks or self.suite.tasks
        results: list[BenchmarkTaskResult] = []

        for task in task_list:
            result = self.runner.run_task(task, agent, replay_dir=replay_dir)
            results.append(result)

        return results

    def compare(self, results: list[AgentArenaResult]) -> dict[str, Any]:
        """Generate comparison summary as structured data."""
        from armature.benchmark.scoring import compute_per_category_rankings

        rankings = compute_per_category_rankings(results)

        return {
            "overall_ranking": [
                {
                    "rank": i + 1,
                    "agent": r.agent,
                    "composite_score": r.composite_score,
                    "grade": r.grade,
                    "quality_avg": r.quality_avg,
                    "efficiency_score": r.efficiency_score,
                    "heal_rate": r.heal_rate,
                    "cache_hit_rate": r.cache_hit_rate,
                    "tasks_completed": len(r.task_results),
                    "tasks_passed": sum(1 for t in r.task_results if t.passed),
                }
                for i, r in enumerate(results)
            ],
            "per_category": rankings,
            "total_tasks": len(results[0].task_results) if results else 0,
            "agents_evaluated": len(results),
        }
