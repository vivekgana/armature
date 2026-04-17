"""Shared fixtures for Armature tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from armature.config.schema import (
    ArchitectureConfig,
    ArmatureConfig,
    BoundaryRule,
    BudgetConfig,
    BudgetTier,
    CalibrationConfig,
    ClaudeCodeConfig,
    ConformanceRule,
    GCConfig,
    HealConfig,
    HealerConfig,
    IntegrationsConfig,
    LayerDef,
    PostWriteConfig,
    ProjectConfig,
    QualityConfig,
    SemanticCacheConfig,
    SpecConfig,
    ToolCheckConfig,
    TraceabilityConfig,
)


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    # Source files
    src = tmp_path / "src"
    src.mkdir()
    (src / "models").mkdir()
    (src / "services").mkdir()
    (src / "routes").mkdir()

    (src / "models" / "__init__.py").write_text("", encoding="utf-8")
    (src / "models" / "user.py").write_text(
        'class User:\n    name: str = ""\n    def validate(self) -> bool:\n        return True\n',
        encoding="utf-8",
    )
    (src / "services" / "__init__.py").write_text("", encoding="utf-8")
    (src / "services" / "auth.py").write_text(
        "from src.models.user import User\n\ndef authenticate(u: User) -> bool:\n    return u.validate()\n",
        encoding="utf-8",
    )
    (src / "routes" / "__init__.py").write_text("", encoding="utf-8")
    (src / "routes" / "api.py").write_text(
        "from src.services.auth import authenticate\n\ndef login() -> dict:\n    return {}\n",
        encoding="utf-8",
    )

    # Test files
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_user.py").write_text(
        'def test_user():\n    assert True\n',
        encoding="utf-8",
    )

    # Storage
    storage = tmp_path / ".armature"
    storage.mkdir()
    for subdir in ["baselines", "budget", "gc", "failures", "cache"]:
        (storage / subdir).mkdir()

    return tmp_path


@pytest.fixture
def sample_config() -> ArmatureConfig:
    """Return a fully-configured ArmatureConfig for testing."""
    return ArmatureConfig(
        project=ProjectConfig(
            name="test-project",
            language="python",
            framework="fastapi",
            src_dir="src/",
            test_dir="tests/",
        ),
        quality=QualityConfig(
            enabled=True,
            checks={
                "lint": ToolCheckConfig(tool="ruff", args=["check", "--statistics"], weight=25),
                "type_check": ToolCheckConfig(tool="mypy", args=["--no-error-summary"], weight=25),
                "test": ToolCheckConfig(tool="pytest", args=["-x", "--tb=short"], weight=20),
            },
            post_write=PostWriteConfig(enabled=True, tools=["lint", "type_check"]),
        ),
        architecture=ArchitectureConfig(
            enabled=True,
            layers=[
                LayerDef(name="models", dirs=["src/models/"]),
                LayerDef(name="services", dirs=["src/services/"]),
                LayerDef(name="routes", dirs=["src/routes/"]),
            ],
            boundaries=[
                BoundaryRule(**{"from": "models", "to": ["routes"]}),
            ],
            allowed_shared=["src/utils/"],
            conformance=[
                ConformanceRule(
                    pattern="Agent",
                    base_class="BaseAgent",
                    required_methods=["run"],
                    dirs=["src/agents/"],
                ),
            ],
        ),
        budget=BudgetConfig(
            enabled=True,
            defaults={
                "low": BudgetTier(max_tokens=100_000, max_cost_usd=2.0),
                "medium": BudgetTier(max_tokens=500_000, max_cost_usd=10.0),
                "high": BudgetTier(max_tokens=1_000_000, max_cost_usd=20.0),
            },
            cache=SemanticCacheConfig(enabled=True, storage=".armature/cache/"),
            calibration=CalibrationConfig(enabled=True),
        ),
        heal=HealConfig(
            enabled=True,
            max_attempts=3,
            healers={
                "lint": HealerConfig(auto_fix=True),
                "type_check": HealerConfig(auto_fix=False),
                "test": HealerConfig(auto_fix=False),
            },
        ),
        gc=GCConfig(enabled=True),
        specs=SpecConfig(
            enabled=True,
            traceability=TraceabilityConfig(enabled=True),
        ),
        integrations=IntegrationsConfig(
            claude_code=ClaudeCodeConfig(enabled=True),
        ),
    )


@pytest.fixture
def budget_jsonl_entries() -> list[dict]:
    """Sample JSONL entries for budget tracking tests."""
    return [
        {
            "timestamp": "2026-01-15T10:00:00+00:00",
            "spec_id": "SPEC-2026-Q1-001",
            "phase": "build",
            "tokens": 25000,
            "cost_usd": 0.50,
            "task_id": "task-1",
            "model": "claude-sonnet",
            "provider": "anthropic",
            "input_tokens": 15000,
            "output_tokens": 10000,
            "intent": "code_gen",
        },
        {
            "timestamp": "2026-01-15T10:30:00+00:00",
            "spec_id": "SPEC-2026-Q1-001",
            "phase": "build",
            "tokens": 30000,
            "cost_usd": 0.60,
            "task_id": "task-2",
            "model": "claude-sonnet",
            "provider": "anthropic",
            "input_tokens": 18000,
            "output_tokens": 12000,
            "intent": "code_gen",
        },
        {
            "timestamp": "2026-01-15T11:00:00+00:00",
            "spec_id": "SPEC-2026-Q1-001",
            "phase": "test",
            "tokens": 15000,
            "cost_usd": 0.30,
            "task_id": "task-3",
            "model": "claude-haiku",
            "provider": "anthropic",
            "input_tokens": 10000,
            "output_tokens": 5000,
            "intent": "test_gen",
        },
    ]


@pytest.fixture
def populated_tracker(tmp_project: Path, sample_config: ArmatureConfig, budget_jsonl_entries: list[dict]) -> Path:
    """Create a tracker with pre-populated JSONL data."""
    budget_dir = tmp_project / ".armature" / "budget"
    budget_dir.mkdir(parents=True, exist_ok=True)
    log_path = budget_dir / "SPEC-2026-Q1-001_cost.jsonl"
    with open(log_path, "w", encoding="utf-8") as f:
        for entry in budget_jsonl_entries:
            f.write(json.dumps(entry) + "\n")
    return tmp_project
