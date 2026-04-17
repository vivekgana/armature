"""Tests for budget/calibrator.py -- auto-calibration and industry benchmarks."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from armature.budget.calibrator import (
    CalibrationProfile,
    CalibrationStore,
    EMA_ALPHA,
    IndustryComparison,
    INDUSTRY_TASK_TARGETS,
    QUALITY_BUDGET_CURVE,
    apply_calibration,
    assess_quality_budget_position,
    calibrate_from_spec,
    compare_against_industry,
    compute_efficiency_grades,
    format_industry_comparison,
    _calculate_confidence,
    _ema_update,
)
from armature.budget.benchmark import calculate_benchmark, ProjectScope
from armature.budget.tracker import SessionTracker
from armature.config.schema import BudgetConfig


# --- EMA and Confidence ---

class TestEMA:
    """Tests for exponential moving average helper."""

    def test_first_value(self):
        result = _ema_update(1.0, 2.0)
        expected = EMA_ALPHA * 2.0 + (1 - EMA_ALPHA) * 1.0
        assert result == pytest.approx(expected)

    def test_identity(self):
        result = _ema_update(1.0, 1.0)
        assert result == pytest.approx(1.0)


class TestConfidence:
    """Tests for confidence ramp function."""

    def test_zero_specs(self):
        assert _calculate_confidence(0) == 0.0

    def test_one_spec(self):
        c = _calculate_confidence(1)
        assert 0.0 < c < 0.5

    def test_ten_specs(self):
        c = _calculate_confidence(10)
        assert 0.90 <= c <= 0.95

    def test_capped_at_095(self):
        c = _calculate_confidence(100)
        assert c == 0.95

    def test_monotonically_increasing(self):
        values = [_calculate_confidence(n) for n in range(1, 15)]
        for i in range(1, len(values)):
            assert values[i] >= values[i - 1]


# --- Calibration Store ---

class TestCalibrationStore:
    """Tests for CalibrationStore persistence."""

    def test_load_default_when_empty(self, tmp_path: Path):
        store = CalibrationStore(tmp_path)
        profile = store.load()
        assert profile.specs_calibrated == 0
        assert profile.confidence == 0.0

    def test_save_and_load(self, tmp_path: Path):
        store = CalibrationStore(tmp_path)
        profile = CalibrationProfile(
            task_adjustments={"feature": 1.2},
            specs_calibrated=5,
            confidence=0.7,
        )
        store.save(profile)
        loaded = store.load()
        assert loaded.specs_calibrated == 5
        assert loaded.task_adjustments["feature"] == 1.2
        assert loaded.confidence == 0.7


# --- Apply Calibration ---

class TestApplyCalibration:
    """Tests for apply_calibration() precedence logic."""

    def test_default_values(self):
        profile = CalibrationProfile()
        result = apply_calibration(profile)
        assert result["task_adjustments"]["feature"] == 1.0
        assert result["cache_hit_rate"] == 0.0

    def test_calibrated_values_with_confidence(self):
        profile = CalibrationProfile(
            task_adjustments={"feature": 1.5},
            specs_calibrated=10,
            confidence=0.9,
        )
        result = apply_calibration(profile)
        # Should blend: 0.9 * 1.5 + 0.1 * 1.0 = 1.45
        assert result["task_adjustments"]["feature"] == pytest.approx(1.45, abs=0.01)

    def test_manual_override_wins(self):
        profile = CalibrationProfile(
            task_adjustments={"feature": 1.5},
            confidence=0.9,
        )
        overrides = {"task_overrides": {"feature": 2.0}}
        result = apply_calibration(profile, overrides)
        assert result["task_adjustments"]["feature"] == 2.0

    def test_cache_hit_rate_override(self):
        profile = CalibrationProfile(cache_hit_rate=0.3, confidence=0.9)
        overrides = {"cache_hit_rate_override": 0.5}
        result = apply_calibration(profile, overrides)
        assert result["cache_hit_rate"] == 0.5


# --- Quality-Budget Position ---

class TestQualityBudgetPosition:
    """Tests for assess_quality_budget_position()."""

    def test_zero_budget(self):
        quality, note = assess_quality_budget_position(0)
        assert quality == 0.0
        assert "no budget" in note.lower()

    def test_below_minimum(self):
        quality, note = assess_quality_budget_position(5_000)
        assert quality == QUALITY_BUDGET_CURVE[0][1]

    def test_above_maximum(self):
        quality, note = assess_quality_budget_position(10_000_000)
        assert quality == QUALITY_BUDGET_CURVE[-1][1]
        assert "ceiling" in note.lower()

    def test_interpolation_500k(self):
        quality, note = assess_quality_budget_position(500_000)
        assert 0.90 <= quality <= 0.96

    def test_monotonically_increasing(self):
        budgets = [10_000, 50_000, 100_000, 500_000, 1_000_000]
        qualities = [assess_quality_budget_position(b)[0] for b in budgets]
        for i in range(1, len(qualities)):
            assert qualities[i] >= qualities[i - 1]


# --- Industry Comparison ---

class TestComputeEfficiencyGrades:
    """Tests for compute_efficiency_grades()."""

    def test_all_a_grades(self):
        comparison = IndustryComparison(
            task_positions={
                "bugfix": {"actual": 10_000, "p25": 15_000, "median": 30_000, "p75": 60_000},
            },
            budget_tokens=500_000,
            estimated_quality_pct=0.94,
            quality_ceiling_note="",
            cost_per_loc=0.005,
            cache_hit_rate=0.50,
            routing_savings_ratio=2.5,
            calibration_drift=0.10,
            phase_comparison={},
            grades={},
        )
        grades = compute_efficiency_grades(comparison)
        assert grades["cache_efficiency"] == "A"
        assert grades["cost_per_loc"] == "A"
        assert grades["routing_savings"] == "A"
        assert grades["calibration_accuracy"] == "A"
        assert grades["task_bugfix"] == "A"

    def test_d_grades_for_poor_metrics(self):
        comparison = IndustryComparison(
            task_positions={
                "bugfix": {"actual": 100_000, "p25": 15_000, "median": 30_000, "p75": 60_000},
            },
            budget_tokens=500_000,
            estimated_quality_pct=0.94,
            quality_ceiling_note="",
            cost_per_loc=0.10,
            cache_hit_rate=0.05,
            routing_savings_ratio=0.5,
            calibration_drift=1.0,
            phase_comparison={},
            grades={},
        )
        grades = compute_efficiency_grades(comparison)
        assert grades["cache_efficiency"] == "D"
        assert grades["cost_per_loc"] == "D"
        assert grades["task_bugfix"] == "D"

    def test_none_metrics_omitted(self):
        comparison = IndustryComparison(
            task_positions={},
            budget_tokens=100_000,
            estimated_quality_pct=0.82,
            quality_ceiling_note="",
            cost_per_loc=None,
            cache_hit_rate=0.0,
            routing_savings_ratio=None,
            calibration_drift=None,
            phase_comparison={},
            grades={},
        )
        grades = compute_efficiency_grades(comparison)
        assert "cost_per_loc" not in grades
        assert "routing_savings" not in grades
        assert "calibration_accuracy" not in grades


class TestFormatIndustryComparison:
    """Tests for format_industry_comparison()."""

    def test_contains_sections(self):
        comparison = IndustryComparison(
            task_positions={
                "bugfix": {"actual": 25_000, "p25": 15_000, "median": 30_000,
                           "p75": 60_000, "percentile_label": "p25-p50 (efficient)"},
            },
            budget_tokens=500_000,
            estimated_quality_pct=0.94,
            quality_ceiling_note="Near ceiling",
            cost_per_loc=0.01,
            cache_hit_rate=0.35,
            routing_savings_ratio=None,
            calibration_drift=0.15,
            phase_comparison={
                "build": {"actual_pct": 45.0, "industry_pct": 38.5, "deviation": 6.5,
                          "source": "SWE-bench"},
            },
            grades={"cache_efficiency": "B", "task_bugfix": "B"},
        )
        output = format_industry_comparison(comparison)
        assert "INDUSTRY BENCHMARK COMPARISON" in output
        assert "bugfix" in output
        assert "Quality-Budget Position" in output
        assert "Phase Allocation" in output
        assert "Efficiency Grades" in output


# --- Calibrate from Spec ---

class TestCalibrateFromSpec:
    """Tests for calibrate_from_spec() EMA updates."""

    def test_updates_task_adjustments(self, tmp_path: Path):
        config = BudgetConfig(enabled=True, storage=".armature/budget/")
        tracker = SessionTracker(config, tmp_path)
        tracker.log("SPEC-001", "build", 50_000, 1.0, intent="code_gen")
        tracker.log("SPEC-001", "test", 20_000, 0.5, intent="test_gen")

        scope = ProjectScope(
            language="python", framework="", total_source_files=10,
            total_loc=1000, total_test_files=5, test_loc=500,
            architectural_layers=0, boundary_rules=0, conformance_rules=0,
            spec_count=1, ac_count=5,
        )
        benchmark = calculate_benchmark(scope)
        store = CalibrationStore(tmp_path / ".armature" / "budget")

        profile = calibrate_from_spec("SPEC-001", tracker, benchmark, store)
        assert profile.specs_calibrated == 1
        assert profile.confidence > 0.0
        assert profile.last_calibrated != ""

    def test_updates_model_verbosity(self, tmp_path: Path):
        config = BudgetConfig(enabled=True, storage=".armature/budget/")
        tracker = SessionTracker(config, tmp_path)
        tracker.log("SPEC-001", "build", 50_000, 1.0,
                     model="claude-opus", provider="anthropic",
                     input_tokens=20_000, output_tokens=30_000, intent="code_gen")

        scope = ProjectScope(
            language="python", framework="", total_source_files=10,
            total_loc=1000, total_test_files=5, test_loc=500,
            architectural_layers=0, boundary_rules=0, conformance_rules=0,
            spec_count=1, ac_count=5,
        )
        benchmark = calculate_benchmark(scope)
        store = CalibrationStore(tmp_path / ".armature" / "budget")

        profile = calibrate_from_spec("SPEC-001", tracker, benchmark, store)
        # Should have updated verbosity for claude-opus
        assert "claude-opus" in profile.model_verbosity

    def test_skips_empty_spec(self, tmp_path: Path):
        config = BudgetConfig(enabled=True, storage=".armature/budget/")
        tracker = SessionTracker(config, tmp_path)
        scope = ProjectScope(
            language="python", framework="", total_source_files=10,
            total_loc=1000, total_test_files=5, test_loc=500,
            architectural_layers=0, boundary_rules=0, conformance_rules=0,
            spec_count=0, ac_count=0,
        )
        benchmark = calculate_benchmark(scope)
        store = CalibrationStore(tmp_path / ".armature" / "budget")

        profile = calibrate_from_spec("NONEXISTENT", tracker, benchmark, store)
        assert profile.specs_calibrated == 0
