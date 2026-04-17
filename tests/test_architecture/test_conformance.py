"""Tests for architecture/conformance.py -- class hierarchy enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature.architecture.conformance import check_conformance, run_conformance_check
from armature.config.schema import ArchitectureConfig, ConformanceRule


@pytest.fixture
def conform_config() -> ArchitectureConfig:
    return ArchitectureConfig(
        enabled=True,
        conformance=[
            ConformanceRule(
                pattern="Agent",
                base_class="BaseAgent",
                required_methods=["run", "reset"],
                required_attributes=["name"],
                dirs=["src/agents/"],
            ),
        ],
    )


class TestCheckConformance:
    """Tests for check_conformance()."""

    def test_detects_missing_base_class(self, tmp_path: Path, conform_config: ArchitectureConfig):
        agents_dir = tmp_path / "src" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "data_agent.py").write_text(
            "class DataAgent:\n    def run(self): ...\n    def reset(self): ...\n    name = 'data'\n",
            encoding="utf-8",
        )

        violations = check_conformance(conform_config, tmp_path)
        assert any("does not inherit from BaseAgent" in v.message for v in violations)

    def test_detects_missing_method(self, tmp_path: Path, conform_config: ArchitectureConfig):
        agents_dir = tmp_path / "src" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "data_agent.py").write_text(
            "class DataAgent(BaseAgent):\n    name = 'data'\n    def run(self): ...\n",
            encoding="utf-8",
        )

        violations = check_conformance(conform_config, tmp_path)
        assert any("missing required method: reset" in v.message for v in violations)

    def test_detects_missing_attribute(self, tmp_path: Path, conform_config: ArchitectureConfig):
        agents_dir = tmp_path / "src" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "data_agent.py").write_text(
            "class DataAgent(BaseAgent):\n    def run(self): ...\n    def reset(self): ...\n",
            encoding="utf-8",
        )

        violations = check_conformance(conform_config, tmp_path)
        assert any("missing required attribute: name" in v.message for v in violations)

    def test_passes_conforming_class(self, tmp_path: Path, conform_config: ArchitectureConfig):
        agents_dir = tmp_path / "src" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "data_agent.py").write_text(
            "class DataAgent(BaseAgent):\n    name = 'data'\n    def run(self): ...\n    def reset(self): ...\n",
            encoding="utf-8",
        )

        violations = check_conformance(conform_config, tmp_path)
        assert len(violations) == 0

    def test_ignores_non_matching_classes(self, tmp_path: Path, conform_config: ArchitectureConfig):
        agents_dir = tmp_path / "src" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "helper.py").write_text(
            "class Helper:\n    def do_thing(self): ...\n",
            encoding="utf-8",
        )

        violations = check_conformance(conform_config, tmp_path)
        assert len(violations) == 0


class TestRunConformanceCheck:
    """Tests for run_conformance_check() CheckResult."""

    def test_pass(self, tmp_path: Path, conform_config: ArchitectureConfig):
        result = run_conformance_check(conform_config, tmp_path)
        assert result.passed is True
        assert result.score == 1.0
