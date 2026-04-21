"""Tests for budget/benchmark.py -- project scope analysis and cost estimation."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature.budget.benchmark import (
    ProjectScope,
    _count_loc,
    _is_test_file,
    calculate_benchmark,
    check_budget_fit,
    format_benchmark,
    scan_project,
)
from armature.config.schema import ArmatureConfig, BudgetConfig, BudgetTier, ProjectConfig


@pytest.fixture
def sample_scope() -> ProjectScope:
    return ProjectScope(
        language="python",
        framework="fastapi",
        total_source_files=50,
        total_loc=5000,
        total_test_files=30,
        test_loc=3000,
        architectural_layers=3,
        boundary_rules=2,
        conformance_rules=1,
        spec_count=5,
        ac_count=25,
    )


class TestScanProject:
    """Tests for scan_project() scope analysis."""

    def test_scan_counts_files(self, tmp_project: Path):
        config = ArmatureConfig(project=ProjectConfig(src_dir="src/", test_dir="tests/"))
        scope = scan_project(tmp_project, config)
        assert scope.total_source_files > 0
        assert scope.total_loc > 0
        assert scope.language == "python"

    def test_scan_empty_project(self, tmp_path: Path):
        config = ArmatureConfig()
        scope = scan_project(tmp_path, config)
        assert scope.total_source_files == 0
        assert scope.total_loc == 0


class TestCalculateBenchmark:
    """Tests for calculate_benchmark() cost estimation."""

    def test_returns_all_task_types(self, sample_scope: ProjectScope):
        benchmark = calculate_benchmark(sample_scope)
        assert "bugfix" in benchmark.estimates
        assert "feature" in benchmark.estimates
        assert "refactor" in benchmark.estimates
        assert "spike" in benchmark.estimates
        assert "test" in benchmark.estimates

    def test_feature_is_most_expensive(self, sample_scope: ProjectScope):
        benchmark = calculate_benchmark(sample_scope)
        feature_tokens = benchmark.estimates["feature"].estimated_tokens
        spike_tokens = benchmark.estimates["spike"].estimated_tokens
        assert feature_tokens > spike_tokens

    def test_recommends_a_tier(self, sample_scope: ProjectScope):
        benchmark = calculate_benchmark(sample_scope)
        assert benchmark.recommended_tier in ("low", "medium", "high", "critical")
        assert benchmark.recommended_tokens > 0
        assert benchmark.recommended_cost_usd > 0

    def test_calibration_adjusts_estimates(self, sample_scope: ProjectScope):
        baseline = calculate_benchmark(sample_scope)
        calibrated = calculate_benchmark(sample_scope, calibration={
            "task_adjustments": {"feature": 2.0},
            "model_verbosity": {},
            "cache_hit_rate": 0.0,
        })
        assert calibrated.estimates["feature"].estimated_tokens > baseline.estimates["feature"].estimated_tokens

    def test_cache_rate_reduces_cost(self, sample_scope: ProjectScope):
        no_cache = calculate_benchmark(sample_scope, calibration={"cache_hit_rate": 0.0})
        with_cache = calculate_benchmark(sample_scope, calibration={"cache_hit_rate": 0.5})
        assert with_cache.estimates["feature"].estimated_cost_usd < no_cache.estimates["feature"].estimated_cost_usd

    def test_opus_more_expensive_than_sonnet(self, sample_scope: ProjectScope):
        sonnet = calculate_benchmark(sample_scope, model="sonnet")
        opus = calculate_benchmark(sample_scope, model="opus")
        assert opus.estimates["feature"].estimated_cost_usd > sonnet.estimates["feature"].estimated_cost_usd


class TestCheckBudgetFit:
    """Tests for check_budget_fit() warnings."""

    def test_too_low_budget(self, sample_scope: ProjectScope):
        config = BudgetConfig(enabled=True, defaults={"medium": BudgetTier(max_tokens=1000, max_cost_usd=0.01)})
        warning = check_budget_fit(config, sample_scope, "medium")
        assert warning.level == "too_low"

    def test_right_sized_budget(self, sample_scope: ProjectScope):
        benchmark = calculate_benchmark(sample_scope)
        tokens = benchmark.estimates["feature"].estimated_tokens * 2
        config = BudgetConfig(enabled=True, defaults={"medium": BudgetTier(max_tokens=tokens, max_cost_usd=50.0)})
        warning = check_budget_fit(config, sample_scope, "medium")
        assert warning.level in ("right_sized", "mismatched_tier")

    def test_too_high_budget(self, sample_scope: ProjectScope):
        config = BudgetConfig(enabled=True, defaults={"medium": BudgetTier(max_tokens=100_000_000, max_cost_usd=9999)})
        warning = check_budget_fit(config, sample_scope, "medium")
        assert warning.level == "too_high"


class TestFormatBenchmark:
    """Tests for format_benchmark() output."""

    def test_contains_scope_info(self, sample_scope: ProjectScope):
        benchmark = calculate_benchmark(sample_scope)
        output = format_benchmark(benchmark)
        assert "PROJECT SCOPE ANALYSIS" in output
        assert "python" in output
        assert "5,000" in output  # LOC

    def test_contains_estimates(self, sample_scope: ProjectScope):
        benchmark = calculate_benchmark(sample_scope)
        output = format_benchmark(benchmark)
        assert "bugfix" in output
        assert "feature" in output
        assert "COST BENCHMARKS" in output


class TestHelpers:
    """Tests for helper functions."""

    def test_count_loc(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("x = 1\n\n# comment\ny = 2\n", encoding="utf-8")
        assert _count_loc(f) == 2  # blank and comment excluded

    def test_count_loc_nonexistent(self, tmp_path: Path):
        assert _count_loc(tmp_path / "nonexistent.py") == 0

    def test_is_test_file_python(self, tmp_path: Path):
        assert _is_test_file(tmp_path / "test_user.py", "python") is True
        assert _is_test_file(tmp_path / "user_test.py", "python") is True
        assert _is_test_file(tmp_path / "conftest.py", "python") is True
        assert _is_test_file(tmp_path / "user.py", "python") is False

    def test_is_test_file_typescript(self, tmp_path: Path):
        assert _is_test_file(tmp_path / "user.test.ts", "typescript") is True
        assert _is_test_file(tmp_path / "user.spec.tsx", "typescript") is True
        assert _is_test_file(tmp_path / "user.ts", "typescript") is False
