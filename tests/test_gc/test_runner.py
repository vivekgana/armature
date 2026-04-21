"""Tests for gc/runner.py -- GC orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature.config.schema import (
    ArmatureConfig,
    GCAgentConfig,
    GCConfig,
    ProjectConfig,
)
from armature.gc.runner import GCRunner


@pytest.fixture
def gc_config() -> GCConfig:
    return GCConfig(
        enabled=True,
        agents={
            "architecture": GCAgentConfig(enabled=True),
            "docs": GCAgentConfig(enabled=True, watched_files=["docs/*.md"]),
            "dead_code": GCAgentConfig(enabled=True),
            "budget": GCAgentConfig(enabled=False),  # disabled
        },
    )


class TestGCRunner:
    """Tests for GCRunner orchestration."""

    def test_runs_enabled_agents(self, tmp_path: Path, gc_config: GCConfig):
        config = ArmatureConfig(
            project=ProjectConfig(src_dir="src/", test_dir="tests/"),
            gc=gc_config,
        )
        runner = GCRunner(gc_config, config)
        # No files = no findings
        findings = runner.run()
        assert isinstance(findings, list)

    def test_filters_by_agent_name(self, tmp_path: Path, gc_config: GCConfig):
        config = ArmatureConfig(gc=gc_config)
        runner = GCRunner(gc_config, config)
        findings = runner.run(agent_name="architecture")
        # Only architecture findings (if any)
        for f in findings:
            assert f.agent == "architecture"

    def test_skips_disabled_agents(self, tmp_path: Path, gc_config: GCConfig):
        config = ArmatureConfig(gc=gc_config)
        runner = GCRunner(gc_config, config)
        findings = runner.run(agent_name="budget")
        # Budget agent is disabled
        assert len(findings) == 0
