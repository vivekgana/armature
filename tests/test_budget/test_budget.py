"""Tests for budget/budget.py -- DevBudget dataclass and phase allocation."""

from __future__ import annotations

import pytest

from armature.budget.budget import DevBudget, REQUEST_OPTIMIZATION_PATTERNS


class TestDevBudget:
    """Tests for DevBudget frozen dataclass."""

    def test_defaults(self):
        budget = DevBudget()
        assert budget.complexity == "medium"
        assert budget.max_tokens_per_spec == 500_000
        assert budget.max_cost_per_spec_usd == 10.0
        assert budget.max_requests_per_task == 15

    def test_for_complexity_low(self):
        budget = DevBudget.for_complexity("low")
        assert budget.complexity == "low"
        assert budget.max_tokens_per_spec == 100_000

    def test_for_complexity_high(self):
        budget = DevBudget.for_complexity("high")
        assert budget.complexity == "high"
        assert budget.max_tokens_per_spec == 1_000_000

    def test_for_complexity_critical(self):
        budget = DevBudget.for_complexity("critical")
        assert budget.max_tokens_per_spec == 2_000_000
        assert budget.max_cost_per_spec_usd == 40.0

    def test_for_complexity_unknown_defaults_to_medium(self):
        budget = DevBudget.for_complexity("unknown")
        assert budget.max_tokens_per_spec == 500_000

    def test_tokens_for_phase(self):
        budget = DevBudget()
        build_tokens = budget.tokens_for_phase("build")
        assert build_tokens == int(500_000 * 0.40)

    def test_tokens_for_unknown_phase(self):
        budget = DevBudget()
        assert budget.tokens_for_phase("nonexistent") == 0

    def test_cost_for_phase(self):
        budget = DevBudget()
        build_cost = budget.cost_for_phase("build")
        assert build_cost == 10.0 * 0.40

    def test_phase_allocation_sums_to_1(self):
        budget = DevBudget()
        total = sum(budget.phase_allocation.values())
        assert total == pytest.approx(1.0)

    def test_frozen(self):
        budget = DevBudget()
        with pytest.raises(AttributeError):
            budget.complexity = "high"  # type: ignore[misc]


class TestOptimizationPatterns:
    """Tests for the REQUEST_OPTIMIZATION_PATTERNS constant."""

    def test_patterns_have_required_keys(self):
        for name, pattern in REQUEST_OPTIMIZATION_PATTERNS.items():
            assert "description" in pattern
            assert "token_savings_pct" in pattern
            assert 0 < pattern["token_savings_pct"] <= 100
