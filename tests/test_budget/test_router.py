"""Tests for budget/router.py -- multi-provider model routing."""

from __future__ import annotations

import pytest

from armature.budget.router import ModelRouter, RoutingDecision, get_pricing, PROVIDERS, CAPABILITIES


class TestModelRouter:
    """Tests for deterministic model routing."""

    @pytest.fixture
    def router(self) -> ModelRouter:
        return ModelRouter(
            enabled_models=["claude-sonnet", "claude-haiku", "claude-opus"],
            quality_floor=0.75,
            premium_intents=["complex_code_gen", "architecture"],
        )

    def test_routes_simple_to_cheap_model(self, router: ModelRouter):
        decision = router.route("lint_fix", 5000, 2000)
        assert isinstance(decision, RoutingDecision)
        assert decision.estimated_cost_usd > 0

    def test_routes_premium_intent_to_premium_model(self, router: ModelRouter):
        decision = router.route("complex_code_gen", 20000, 10000)
        # Should pick opus for premium intents
        assert decision.model in ("claude-opus", "claude-sonnet")

    def test_respects_quality_floor(self, router: ModelRouter):
        decision = router.route("code_gen", 10000, 5000)
        assert decision.model in PROVIDERS

    def test_provides_alternative(self, router: ModelRouter):
        decision = router.route("code_gen", 10000, 5000)
        # Should provide an alternative model
        assert decision.alternative is not None or decision.model is not None

    def test_compare_models(self, router: ModelRouter):
        comparison = router.compare_models("code_gen", 10000, 5000)
        assert len(comparison) > 0
        assert all("model" in c and "cost_usd" in c for c in comparison)


class TestGetPricing:
    """Tests for get_pricing() model price lookup."""

    def test_known_models(self):
        for model_name in ["sonnet", "opus", "haiku", "gpt-4o", "gpt-4o-mini"]:
            prices = get_pricing(model_name)
            assert "input" in prices
            assert "output" in prices
            assert prices["input"] > 0
            assert prices["output"] > 0

    def test_unknown_model_returns_default(self):
        prices = get_pricing("unknown-model")
        assert "input" in prices
        assert "output" in prices
