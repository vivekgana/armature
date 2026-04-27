"""Tests for benchmark/runner.py -- task execution and replay."""

from __future__ import annotations

import json
from pathlib import Path

from armature._internal.types import BenchmarkTaskResult, CheckResult
from armature.benchmark.runner import BenchmarkRunner, save_replay
from armature.benchmark.tasks import BenchmarkTask
from armature.config.schema import ArmatureConfig, ProjectConfig, QualityConfig


def _make_config() -> ArmatureConfig:
    return ArmatureConfig(
        project=ProjectConfig(name="test", language="python", src_dir="src/", test_dir="tests/"),
        quality=QualityConfig(enabled=False),
    )


def _make_task(task_id: str = "BUG-001") -> BenchmarkTask:
    return BenchmarkTask(
        id=task_id, category="bugfix", description="Fix bug",
        difficulty="easy", language="python", estimated_tokens=10000,
        verification="pytest",
    )


class TestRunFromReplay:
    """Tests for replay-mode execution."""

    def test_load_replay_file(self, tmp_path: Path):
        replay_dir = tmp_path / "replays"
        agent_dir = replay_dir / "claude-code"
        agent_dir.mkdir(parents=True)

        replay_data = {
            "task_id": "BUG-001",
            "agent": "claude-code",
            "quality_score": 92.5,
            "budget_tokens": 25000,
            "budget_cost_usd": 0.50,
            "heal_attempts": 1,
            "heal_fixed": 1,
            "cache_hits": 3,
            "cache_total": 5,
            "passed": True,
            "check_results": [
                {"name": "lint", "passed": True, "violations": 0, "score": 1.0, "weight": 25},
                {"name": "test", "passed": True, "violations": 0, "score": 0.9, "weight": 25},
            ],
        }
        (agent_dir / "BUG-001.json").write_text(json.dumps(replay_data), encoding="utf-8")

        runner = BenchmarkRunner(_make_config())
        result = runner.run_task(_make_task(), "claude-code", replay_dir=replay_dir)

        assert result.task_id == "BUG-001"
        assert result.agent == "claude-code"
        assert result.quality_score == 92.5
        assert result.budget_tokens == 25000
        assert result.passed is True
        assert len(result.check_results) == 2
        assert result.check_results[0].name == "lint"

    def test_missing_replay_returns_zero(self, tmp_path: Path):
        replay_dir = tmp_path / "replays"
        replay_dir.mkdir()

        runner = BenchmarkRunner(_make_config())
        result = runner.run_task(_make_task(), "unknown-agent", replay_dir=replay_dir)

        assert result.quality_score == 0.0
        assert result.passed is False

    def test_replay_uses_estimated_tokens_as_fallback(self, tmp_path: Path):
        replay_dir = tmp_path / "replays"
        agent_dir = replay_dir / "agent"
        agent_dir.mkdir(parents=True)

        (agent_dir / "BUG-001.json").write_text(json.dumps({"passed": True, "quality_score": 80.0}), encoding="utf-8")

        runner = BenchmarkRunner(_make_config())
        task = _make_task()
        result = runner.run_task(task, "agent", replay_dir=replay_dir)
        assert result.budget_tokens == task.estimated_tokens


class TestSaveReplay:
    """Tests for save_replay()."""

    def test_creates_replay_file(self, tmp_path: Path):
        result = BenchmarkTaskResult(
            task_id="BUG-001", agent="claude-code", quality_score=88.0,
            budget_tokens=20000, budget_cost_usd=0.40,
            heal_attempts=2, heal_fixed=1, cache_hits=3, cache_total=6,
            duration_seconds=5.0, passed=True,
            check_results=[CheckResult(name="lint", passed=True, score=1.0, weight=25)],
        )

        path = save_replay(result, tmp_path)

        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["task_id"] == "BUG-001"
        assert data["agent"] == "claude-code"
        assert data["quality_score"] == 88.0
        assert len(data["check_results"]) == 1

    def test_creates_agent_subdirectory(self, tmp_path: Path):
        result = BenchmarkTaskResult(
            task_id="FEAT-001", agent="copilot", quality_score=75.0,
            budget_tokens=40000, budget_cost_usd=0.80,
            heal_attempts=0, heal_fixed=0, cache_hits=0, cache_total=0,
            duration_seconds=3.0, passed=False,
        )

        path = save_replay(result, tmp_path)
        assert path.parent.name == "copilot"
        assert path.name == "FEAT-001.json"

    def test_roundtrip_through_replay(self, tmp_path: Path):
        original = BenchmarkTaskResult(
            task_id="REF-001", agent="cursor", quality_score=91.0,
            budget_tokens=35000, budget_cost_usd=0.70,
            heal_attempts=1, heal_fixed=1, cache_hits=5, cache_total=8,
            duration_seconds=7.0, passed=True,
            check_results=[
                CheckResult(name="lint", passed=True, score=1.0, weight=25),
                CheckResult(name="type_check", passed=True, score=0.95, weight=25),
            ],
        )

        save_replay(original, tmp_path)

        runner = BenchmarkRunner(_make_config())
        task = BenchmarkTask(
            id="REF-001", category="refactor", description="Extract",
            difficulty="medium", language="python", estimated_tokens=35000,
            verification="pytest",
        )
        loaded = runner.run_task(task, "cursor", replay_dir=tmp_path)

        assert loaded.quality_score == original.quality_score
        assert loaded.budget_tokens == original.budget_tokens
        assert loaded.passed == original.passed
        assert len(loaded.check_results) == 2
