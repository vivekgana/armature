"""Composite scoring and grading for benchmark results."""

from __future__ import annotations

import math

from armature._internal.types import AgentArenaResult, BenchmarkTaskResult
from armature.benchmark.tasks import GradeBoundaries, ScoringWeights


def compute_composite_score(
    quality_avg: float,
    efficiency_score: float,
    heal_rate: float,
    cache_hit_rate: float,
    weights: ScoringWeights | None = None,
) -> float:
    """Compute weighted composite score (0-100)."""
    w = weights or ScoringWeights()
    raw = (
        quality_avg * w.quality
        + efficiency_score * 100.0 * w.efficiency
        + heal_rate * 100.0 * w.heal
        + cache_hit_rate * 100.0 * w.cache
    )
    return round(min(100.0, max(0.0, raw)), 1)


def assign_grade(composite: float, boundaries: GradeBoundaries | None = None) -> str:
    """Assign letter grade from composite score."""
    b = boundaries or GradeBoundaries()
    if composite >= b.A:
        return "A"
    if composite >= b.B_plus:
        return "B+"
    if composite >= b.B:
        return "B"
    if composite >= b.B_minus:
        return "B-"
    if composite >= b.C:
        return "C"
    return "D"


def compute_efficiency_score(agent_cost: float, min_cost: float) -> float:
    """Normalized efficiency: cheapest agent gets 1.0, others proportionally less."""
    if agent_cost <= 0:
        return 0.0
    if min_cost <= 0:
        return 1.0
    return min(1.0, min_cost / agent_cost)


def aggregate_agent_results(
    agent: str,
    task_results: list[BenchmarkTaskResult],
    min_cost_across_agents: float,
    weights: ScoringWeights | None = None,
    boundaries: GradeBoundaries | None = None,
) -> AgentArenaResult:
    """Aggregate per-task results into an agent-level summary."""
    if not task_results:
        return AgentArenaResult(
            agent=agent, task_results=[], composite_score=0.0,
            grade="D", quality_avg=0.0, efficiency_score=0.0,
            heal_rate=0.0, cache_hit_rate=0.0,
        )

    quality_avg = sum(r.quality_score for r in task_results) / len(task_results)
    total_cost = sum(r.budget_cost_usd for r in task_results)
    efficiency = compute_efficiency_score(total_cost, min_cost_across_agents)

    total_heal_attempts = sum(r.heal_attempts for r in task_results)
    total_heal_fixed = sum(r.heal_fixed for r in task_results)
    heal_rate = total_heal_fixed / total_heal_attempts if total_heal_attempts > 0 else 0.0

    total_cache_hits = sum(r.cache_hits for r in task_results)
    total_cache_total = sum(r.cache_total for r in task_results)
    cache_hit_rate = total_cache_hits / total_cache_total if total_cache_total > 0 else 0.0

    composite = compute_composite_score(quality_avg, efficiency, heal_rate, cache_hit_rate, weights)
    grade = assign_grade(composite, boundaries)

    return AgentArenaResult(
        agent=agent,
        task_results=task_results,
        composite_score=composite,
        grade=grade,
        quality_avg=round(quality_avg, 1),
        efficiency_score=round(efficiency, 3),
        heal_rate=round(heal_rate, 3),
        cache_hit_rate=round(cache_hit_rate, 3),
    )


def compute_per_category_rankings(
    results: list[AgentArenaResult],
) -> dict[str, dict[str, str]]:
    """Find best agent per task category across multiple metrics.

    Returns: {category: {best_quality: agent, best_cost: agent, best_overall: agent}}
    """
    categories: set[str] = set()
    for r in results:
        for tr in r.task_results:
            task_category = tr.task_id.split("-")[0].lower()
            cat_map = {"bug": "bugfix", "feat": "feature", "ref": "refactor",
                       "test": "test_gen", "doc": "documentation"}
            categories.add(cat_map.get(task_category, task_category))

    rankings: dict[str, dict[str, str]] = {}
    for cat in sorted(categories):
        best_quality_agent = ""
        best_quality_score = -1.0
        best_cost_agent = ""
        best_cost_value = math.inf

        for r in results:
            cat_tasks = [
                tr for tr in r.task_results
                if _task_matches_category(tr.task_id, cat)
            ]
            if not cat_tasks:
                continue

            avg_quality = sum(t.quality_score for t in cat_tasks) / len(cat_tasks)
            total_cost = sum(t.budget_cost_usd for t in cat_tasks)

            if avg_quality > best_quality_score:
                best_quality_score = avg_quality
                best_quality_agent = r.agent
            if total_cost < best_cost_value:
                best_cost_value = total_cost
                best_cost_agent = r.agent

        rankings[cat] = {
            "best_quality": best_quality_agent,
            "best_cost": best_cost_agent,
        }

    return rankings


def _task_matches_category(task_id: str, category: str) -> bool:
    """Check if a task ID matches a category based on prefix."""
    prefix_map = {
        "bugfix": "BUG",
        "feature": "FEAT",
        "refactor": "REF",
        "test_gen": "TEST",
        "documentation": "DOC",
    }
    expected_prefix = prefix_map.get(category, "")
    return task_id.startswith(expected_prefix)
