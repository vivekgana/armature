"""Tests for config/schema.py -- Pydantic configuration models."""

from __future__ import annotations

from armature.config.schema import (
    ArmatureConfig,
    BoundaryRule,
    BudgetConfig,
    BudgetTier,
    ConformanceRule,
    LayerDef,
    QualityConfig,
)


class TestArmatureConfig:
    """Tests for the root ArmatureConfig model."""

    def test_defaults(self):
        config = ArmatureConfig()
        assert config.project.language == "python"
        assert config.quality.enabled is True
        assert config.budget.enabled is False
        assert config.architecture.enabled is False
        assert config.gc.enabled is False
        assert config.heal.enabled is True

    def test_model_validate_from_dict(self):
        data = {
            "project": {"name": "test", "language": "typescript", "src_dir": "src/"},
            "quality": {"enabled": True},
            "budget": {"enabled": True, "defaults": {"low": {"max_tokens": 50000, "max_cost_usd": 1.0}}},
        }
        config = ArmatureConfig.model_validate(data)
        assert config.project.name == "test"
        assert config.project.language == "typescript"
        assert config.budget.enabled is True
        assert config.budget.defaults["low"].max_tokens == 50000

    def test_empty_dict_returns_defaults(self):
        config = ArmatureConfig.model_validate({})
        assert config.project.language == "python"
        assert config.quality.enabled is True


class TestBudgetConfig:
    """Tests for BudgetConfig and related models."""

    def test_default_tiers(self):
        config = BudgetConfig()
        assert "low" in config.defaults
        assert "medium" in config.defaults
        assert "high" in config.defaults
        assert "critical" in config.defaults
        assert config.defaults["medium"].max_tokens == 500_000

    def test_phase_allocation_sums_to_100(self):
        config = BudgetConfig()
        total = sum(config.phase_allocation.values())
        assert total == 100

    def test_custom_tier(self):
        tier = BudgetTier(max_tokens=1_000_000, max_cost_usd=25.0)
        assert tier.max_tokens == 1_000_000
        assert tier.max_cost_usd == 25.0


class TestArchitectureConfig:
    """Tests for ArchitectureConfig and boundary rules."""

    def test_boundary_rule_alias(self):
        rule = BoundaryRule(**{"from": "models", "to": ["routes"]})
        assert rule.from_layer == "models"
        assert rule.to_layers == ["routes"]

    def test_conformance_rule(self):
        rule = ConformanceRule(
            pattern="Agent",
            base_class="BaseAgent",
            required_methods=["run", "reset"],
            dirs=["src/agents/"],
        )
        assert rule.pattern == "Agent"
        assert len(rule.required_methods) == 2

    def test_layer_def(self):
        layer = LayerDef(name="models", dirs=["src/models/", "src/schemas/"])
        assert layer.name == "models"
        assert len(layer.dirs) == 2


class TestQualityConfig:
    """Tests for QualityConfig defaults."""

    def test_default_gates(self):
        config = QualityConfig()
        assert config.gates["draft"] == 0.70
        assert config.gates["review_ready"] == 0.85
        assert config.gates["merge_ready"] == 0.95

    def test_default_checks(self):
        config = QualityConfig()
        assert "lint" in config.checks
        assert "type_check" in config.checks
        assert "test" in config.checks
        assert config.checks["lint"].tool == "ruff"

    def test_post_write_defaults(self):
        config = QualityConfig()
        assert config.post_write.enabled is True
        assert "lint" in config.post_write.tools
