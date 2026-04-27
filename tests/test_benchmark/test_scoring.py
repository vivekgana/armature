"""Tests for benchmark/scoring.py -- composite scoring and grading."""

from __future__ import annotations

from armature._internal.types import AgentArenaResult, BenchmarkTaskResult
from armature.benchmark.scoring import (
    aggregate_agent_results,
    assign_grade,
    compute_composite_score,
    compute_efficiency_score,
    compute_per_category_rankings,
)
from armature.benchmark.tasks import GradeBoundaries, ScoringWeights


def _make_task_result(
    task_id: str = "BUG-001",
    agent: str = "claude-code",
    quality_score: float = 85.0,
    budget_tokens: int = 30000,
    budget_cost_usd: float = 0.50,
    heal_attempts: int = 2,
    heal_fixed: int = 1,
    cache_hits: int = 5,
    cache_total: int = 10,
    passed: bool = True,
) -> BenchmarkTaskResult:
    return BenchmarkTaskResult(
        task_id=task_id,
        agent=agent,
        quality_score=quality_score,
        budget_tokens=budget_tokens,
        budget_cost_usd=budget_cost_usd,
        heal_attempts=heal_attempts,
        heal_fixed=heal_fixed,
        cache_hits=cache_hits,
        cache_total=cache_total,
        duration_seconds=1.0,
        passed=passed,
    )


class TestCompositeScore:
    """Tests for compute_composite_score()."""

    def test_default_weights(self):
        score = compute_composite_score(
            quality_avg=90.0, efficiency_score=0.8, heal_rate=0.5, cache_hit_rate=0.6,
        )
        expected = 90.0 * 0.40 + 0.8 * 100.0 * 0.25 + 0.5 * 100.0 * 0.20 + 0.6 * 100.0 * 0.15
        assert score == round(min(100.0, max(0.0, expected)), 1)

    def test_perfect_scores(self):
        score = compute_composite_score(
            quality_avg=100.0, efficiency_score=1.0, heal_rate=1.0, cache_hit_rate=1.0,
        )
        assert score == 100.0

    def test_zero_scores(self):
        score = compute_composite_score(
            quality_avg=0.0, efficiency_score=0.0, heal_rate=0.0, cache_hit_rate=0.0,
        )
        assert score == 0.0

    def test_custom_weights(self):
        weights = ScoringWeights(quality=1.0, efficiency=0.0, heal=0.0, cache=0.0)
        score = compute_composite_score(
            quality_avg=75.0, efficiency_score=1.0, heal_rate=1.0, cache_hit_rate=1.0,
            weights=weights,
        )
        assert score == 75.0

    def test_capped_at_100(self):
        weights = ScoringWeights(quality=0.5, efficiency=0.5, heal=0.5, cache=0.5)
        score = compute_composite_score(
            quality_avg=100.0, efficiency_score=1.0, heal_rate=1.0, cache_hit_rate=1.0,
            weights=weights,
        )
        assert score == 100.0

    def test_floored_at_zero(self):
        score = compute_composite_score(
            quality_avg=-10.0, efficiency_score=0.0, heal_rate=0.0, cache_hit_rate=0.0,
        )
        assert score == 0.0


class TestAssignGrade:
    """Tests for assign_grade()."""

    def test_grade_A(self):
        assert assign_grade(95.0) == "A"
        assert assign_grade(90.0) == "A"

    def test_grade_B_plus(self):
        assert assign_grade(89.9) == "B+"
        assert assign_grade(85.0) == "B+"

    def test_grade_B(self):
        assert assign_grade(84.9) == "B"
        assert assign_grade(80.0) == "B"

    def test_grade_B_minus(self):
        assert assign_grade(79.9) == "B-"
        assert assign_grade(75.0) == "B-"

    def test_grade_C(self):
        assert assign_grade(74.9) == "C"
        assert assign_grade(65.0) == "C"

    def test_grade_D(self):
        assert assign_grade(64.9) == "D"
        assert assign_grade(0.0) == "D"

    def test_custom_boundaries(self):
        boundaries = GradeBoundaries(A=95, B_plus=90, B=85, B_minus=80, C=70)
        assert assign_grade(92.0, boundaries) == "B+"
        assert assign_grade(96.0, boundaries) == "A"
        assert assign_grade(65.0, boundaries) == "D"


class TestEfficiencyScore:
    """Tests for compute_efficiency_score()."""

    def test_cheapest_agent(self):
        assert compute_efficiency_score(agent_cost=5.0, min_cost=5.0) == 1.0

    def test_twice_as_expensive(self):
        assert compute_efficiency_score(agent_cost=10.0, min_cost=5.0) == 0.5

    def test_zero_agent_cost(self):
        assert compute_efficiency_score(agent_cost=0.0, min_cost=5.0) == 0.0

    def test_zero_min_cost(self):
        assert compute_efficiency_score(agent_cost=5.0, min_cost=0.0) == 1.0

    def test_proportional(self):
        score = compute_efficiency_score(agent_cost=20.0, min_cost=5.0)
        assert score == 0.25


class TestAggregateAgentResults:
    """Tests for aggregate_agent_results()."""

    def test_empty_results(self):
        result = aggregate_agent_results("test-agent", [], 1.0)
        assert result.agent == "test-agent"
        assert result.composite_score == 0.0
        assert result.grade == "D"

    def test_single_task(self):
        task = _make_task_result(
            quality_score=90.0, budget_cost_usd=1.0,
            heal_attempts=2, heal_fixed=1, cache_hits=3, cache_total=5,
        )
        result = aggregate_agent_results("claude-code", [task], 1.0)
        assert result.quality_avg == 90.0
        assert result.efficiency_score == 1.0
        assert result.heal_rate == 0.5
        assert result.cache_hit_rate == 0.6

    def test_multiple_tasks_averaged(self):
        t1 = _make_task_result(
            quality_score=80.0, budget_cost_usd=1.0,
            heal_attempts=1, heal_fixed=1, cache_hits=2, cache_total=4,
        )
        t2 = _make_task_result(
            quality_score=90.0, budget_cost_usd=1.0,
            heal_attempts=1, heal_fixed=0, cache_hits=3, cache_total=6,
        )
        result = aggregate_agent_results("claude-code", [t1, t2], 2.0)
        assert result.quality_avg == 85.0
        assert result.heal_rate == 0.5
        assert result.cache_hit_rate == 0.5

    def test_no_heal_attempts(self):
        task = _make_task_result(heal_attempts=0, heal_fixed=0)
        result = aggregate_agent_results("agent", [task], 1.0)
        assert result.heal_rate == 0.0

    def test_no_cache_requests(self):
        task = _make_task_result(cache_hits=0, cache_total=0)
        result = aggregate_agent_results("agent", [task], 1.0)
        assert result.cache_hit_rate == 0.0


class TestPerCategoryRankings:
    """Tests for compute_per_category_rankings()."""

    def test_single_agent_single_category(self):
        t = _make_task_result(task_id="BUG-001", agent="claude", quality_score=90.0, budget_cost_usd=1.0)
        r = AgentArenaResult(
            agent="claude", task_results=[t],
            composite_score=85.0, grade="B+", quality_avg=90.0,
            efficiency_score=1.0, heal_rate=0.5, cache_hit_rate=0.5,
        )
        rankings = compute_per_category_rankings([r])
        assert "bugfix" in rankings
        assert rankings["bugfix"]["best_quality"] == "claude"
        assert rankings["bugfix"]["best_cost"] == "claude"

    def test_two_agents_different_strengths(self):
        t1_bug = _make_task_result(task_id="BUG-001", agent="agent-a", quality_score=95.0, budget_cost_usd=5.0)
        t2_bug = _make_task_result(task_id="BUG-001", agent="agent-b", quality_score=80.0, budget_cost_usd=1.0)
        r1 = AgentArenaResult(
            agent="agent-a", task_results=[t1_bug],
            composite_score=85.0, grade="B+", quality_avg=95.0,
            efficiency_score=0.2, heal_rate=0.5, cache_hit_rate=0.5,
        )
        r2 = AgentArenaResult(
            agent="agent-b", task_results=[t2_bug],
            composite_score=80.0, grade="B", quality_avg=80.0,
            efficiency_score=1.0, heal_rate=0.5, cache_hit_rate=0.5,
        )
        rankings = compute_per_category_rankings([r1, r2])
        assert rankings["bugfix"]["best_quality"] == "agent-a"
        assert rankings["bugfix"]["best_cost"] == "agent-b"
