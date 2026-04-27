"""Tests for benchmark/reporter.py -- output formatting."""

from __future__ import annotations

from armature._internal.types import AgentArenaResult, BenchmarkTaskResult, CorrelationResult
from armature.benchmark.reporter import BenchmarkReporter


def _make_task_result(
    task_id: str = "BUG-001",
    agent: str = "claude-code",
    quality_score: float = 85.0,
    budget_tokens: int = 25000,
    budget_cost_usd: float = 0.50,
    passed: bool = True,
) -> BenchmarkTaskResult:
    return BenchmarkTaskResult(
        task_id=task_id, agent=agent, quality_score=quality_score,
        budget_tokens=budget_tokens, budget_cost_usd=budget_cost_usd,
        heal_attempts=1, heal_fixed=1, cache_hits=3, cache_total=5,
        duration_seconds=2.0, passed=passed,
    )


def _make_arena_result(agent: str, quality: float, score: float, grade: str) -> AgentArenaResult:
    return AgentArenaResult(
        agent=agent,
        task_results=[
            _make_task_result(task_id="BUG-001", agent=agent, quality_score=quality, passed=True),
            _make_task_result(task_id="FEAT-001", agent=agent, quality_score=quality - 5, passed=True),
        ],
        composite_score=score,
        grade=grade,
        quality_avg=quality,
        efficiency_score=0.8,
        heal_rate=0.5,
        cache_hit_rate=0.6,
    )


class TestFormatArenaResults:
    """Tests for format_arena_results()."""

    def test_contains_header(self):
        results = [_make_arena_result("claude", 90.0, 85.0, "B+")]
        output = BenchmarkReporter().format_arena_results(results)
        assert "AGENT ARENA" in output

    def test_contains_agent_name(self):
        results = [_make_arena_result("claude-code", 90.0, 85.0, "B+")]
        output = BenchmarkReporter().format_arena_results(results)
        assert "claude-code" in output

    def test_multiple_agents_listed(self):
        results = [
            _make_arena_result("claude-code", 92.0, 88.0, "B+"),
            _make_arena_result("copilot", 80.0, 75.0, "B-"),
        ]
        output = BenchmarkReporter().format_arena_results(results)
        assert "claude-code" in output
        assert "copilot" in output

    def test_contains_token_section(self):
        results = [_make_arena_result("claude", 90.0, 85.0, "B+")]
        output = BenchmarkReporter().format_arena_results(results)
        assert "TOKEN USAGE" in output

    def test_contains_completion_section(self):
        results = [_make_arena_result("claude", 90.0, 85.0, "B+")]
        output = BenchmarkReporter().format_arena_results(results)
        assert "TASK COMPLETION" in output


class TestFormatCorrelationReport:
    """Tests for format_correlation_report()."""

    def test_contains_statistical_measures(self):
        result = CorrelationResult(
            pearson_r=0.85, spearman_rho=0.82, p_value=0.001,
            roc_auc=0.90, optimal_threshold=80.0,
        )
        output = BenchmarkReporter().format_correlation_report(result)
        assert "Pearson" in output
        assert "Spearman" in output
        assert "0.85" in output

    def test_significance_stars(self):
        result = CorrelationResult(
            pearson_r=0.9, spearman_rho=0.9, p_value=0.0001,
            roc_auc=0.95, optimal_threshold=85.0,
        )
        output = BenchmarkReporter().format_correlation_report(result)
        assert "***" in output

    def test_quality_bands_displayed(self):
        result = CorrelationResult(
            pearson_r=0.85, spearman_rho=0.82, p_value=0.001,
            roc_auc=0.90, optimal_threshold=80.0,
            quality_bands=[
                {"band": "95-100", "pass_rate": 0.92, "n": 50},
                {"band": "85-95", "pass_rate": 0.74, "n": 80},
            ],
        )
        output = BenchmarkReporter().format_correlation_report(result)
        assert "95-100" in output
        assert "85-95" in output

    def test_check_importance_displayed(self):
        result = CorrelationResult(
            pearson_r=0.85, spearman_rho=0.82, p_value=0.001,
            roc_auc=0.90, optimal_threshold=80.0,
            per_check_importance={"lint": 0.85, "test": 0.72},
        )
        output = BenchmarkReporter().format_correlation_report(result)
        assert "lint" in output
        assert "test" in output


class TestExportJson:
    """Tests for export_json()."""

    def test_arena_export(self):
        results = [_make_arena_result("claude", 90.0, 85.0, "B+")]
        export = BenchmarkReporter().export_json(arena_results=results)
        assert "arena" in export
        assert len(export["arena"]["agents"]) == 1
        agent = export["arena"]["agents"][0]
        assert agent["agent"] == "claude"
        assert agent["composite_score"] == 85.0
        assert agent["grade"] == "B+"

    def test_correlation_export(self):
        result = CorrelationResult(
            pearson_r=0.85, spearman_rho=0.82, p_value=0.001,
            roc_auc=0.90, optimal_threshold=80.0,
        )
        export = BenchmarkReporter().export_json(correlation_result=result)
        assert "correlation" in export
        assert export["correlation"]["pearson_r"] == 0.85
        assert export["correlation"]["roc_auc"] == 0.90

    def test_combined_export(self):
        arena = [_make_arena_result("claude", 90.0, 85.0, "B+")]
        corr = CorrelationResult(
            pearson_r=0.85, spearman_rho=0.82, p_value=0.001,
            roc_auc=0.90, optimal_threshold=80.0,
        )
        export = BenchmarkReporter().export_json(arena_results=arena, correlation_result=corr)
        assert "arena" in export
        assert "correlation" in export

    def test_empty_export(self):
        export = BenchmarkReporter().export_json()
        assert export == {}

    def test_arena_token_totals(self):
        results = [_make_arena_result("claude", 90.0, 85.0, "B+")]
        export = BenchmarkReporter().export_json(arena_results=results)
        agent = export["arena"]["agents"][0]
        assert agent["total_tokens"] == 50000
        assert agent["tasks_passed"] == 2
        assert agent["tasks_total"] == 2
