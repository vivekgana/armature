"""Tests for benchmark/arena.py -- Agent Arena orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from armature._internal.types import AgentArenaResult
from armature.benchmark.arena import AgentArena
from armature.benchmark.tasks import (
    AgentConfig,
    ArenaSuite,
    BenchmarkTask,
    GradeBoundaries,
    ScoringWeights,
)
from armature.config.schema import (
    ArmatureConfig,
    BenchmarkConfig,
    ProjectConfig,
    QualityConfig,
)


def _make_config(arena_path: str = "data/arena_tasks.yaml") -> ArmatureConfig:
    return ArmatureConfig(
        project=ProjectConfig(
            name="test", language="python", src_dir="src/", test_dir="tests/",
        ),
        quality=QualityConfig(enabled=False),
        benchmark=BenchmarkConfig(enabled=True, arena_tasks_path=arena_path),
    )


def _make_suite() -> ArenaSuite:
    tasks = [
        BenchmarkTask(
            id="BUG-001", category="bugfix", description="Fix bug",
            difficulty="easy", language="python",
            estimated_tokens=10000, verification="pytest",
        ),
        BenchmarkTask(
            id="FEAT-001", category="feature", description="Add feature",
            difficulty="medium", language="python",
            estimated_tokens=20000, verification="pytest",
        ),
    ]
    agents = {
        "agent-a": AgentConfig(name="agent-a", model="model-a", provider="prov-a"),
        "agent-b": AgentConfig(name="agent-b", model="model-b", provider="prov-b"),
    }
    return ArenaSuite(
        tasks=tasks, agents=agents,
        scoring=ScoringWeights(), grades=GradeBoundaries(),
    )


def _write_replay(
    replay_dir: Path, agent: str, task_id: str,
    quality: float, cost: float, passed: bool,
) -> None:
    agent_dir = replay_dir / agent
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / f"{task_id}.json").write_text(json.dumps({
        "quality_score": quality,
        "budget_tokens": 20000,
        "budget_cost_usd": cost,
        "heal_attempts": 1,
        "heal_fixed": 1 if passed else 0,
        "cache_hits": 3,
        "cache_total": 5,
        "passed": passed,
        "check_results": [],
    }), encoding="utf-8")


class TestAgentArena:
    """Tests for AgentArena run and comparison."""

    def test_run_all_with_replay(self, tmp_path: Path):
        replay_dir = tmp_path / "replays"
        _write_replay(replay_dir, "agent-a", "BUG-001", 90.0, 1.0, True)
        _write_replay(replay_dir, "agent-a", "FEAT-001", 85.0, 1.5, True)
        _write_replay(replay_dir, "agent-b", "BUG-001", 80.0, 0.5, True)
        _write_replay(replay_dir, "agent-b", "FEAT-001", 75.0, 0.8, False)

        arena = AgentArena(_make_config(), suite=_make_suite())
        results = arena.run_all(replay_dir=replay_dir)

        assert len(results) == 2
        assert results[0].composite_score >= results[1].composite_score
        assert all(isinstance(r, AgentArenaResult) for r in results)

    def test_run_single_agent(self, tmp_path: Path):
        replay_dir = tmp_path / "replays"
        _write_replay(replay_dir, "agent-a", "BUG-001", 90.0, 1.0, True)
        _write_replay(replay_dir, "agent-a", "FEAT-001", 85.0, 1.5, True)

        arena = AgentArena(_make_config(), suite=_make_suite())
        results = arena.run_agent("agent-a", replay_dir=replay_dir)

        assert len(results) == 2
        assert all(r.agent == "agent-a" for r in results)

    def test_filter_by_category(self, tmp_path: Path):
        replay_dir = tmp_path / "replays"
        _write_replay(replay_dir, "agent-a", "BUG-001", 90.0, 1.0, True)
        _write_replay(replay_dir, "agent-b", "BUG-001", 80.0, 0.5, True)

        arena = AgentArena(_make_config(), suite=_make_suite())
        results = arena.run_all(categories={"bugfix"}, replay_dir=replay_dir)

        for r in results:
            assert len(r.task_results) == 1
            assert r.task_results[0].task_id == "BUG-001"

    def test_filter_specific_agents(self, tmp_path: Path):
        replay_dir = tmp_path / "replays"
        _write_replay(replay_dir, "agent-a", "BUG-001", 90.0, 1.0, True)
        _write_replay(replay_dir, "agent-a", "FEAT-001", 85.0, 1.0, True)

        arena = AgentArena(_make_config(), suite=_make_suite())
        results = arena.run_all(agents=["agent-a"], replay_dir=replay_dir)

        assert len(results) == 1
        assert results[0].agent == "agent-a"

    def test_compare_output_structure(self, tmp_path: Path):
        replay_dir = tmp_path / "replays"
        _write_replay(replay_dir, "agent-a", "BUG-001", 90.0, 1.0, True)
        _write_replay(replay_dir, "agent-a", "FEAT-001", 85.0, 1.5, True)
        _write_replay(replay_dir, "agent-b", "BUG-001", 80.0, 0.5, True)
        _write_replay(replay_dir, "agent-b", "FEAT-001", 75.0, 0.8, True)

        arena = AgentArena(_make_config(), suite=_make_suite())
        results = arena.run_all(replay_dir=replay_dir)
        comparison = arena.compare(results)

        assert "overall_ranking" in comparison
        assert "per_category" in comparison
        assert "total_tasks" in comparison
        assert "agents_evaluated" in comparison
        assert comparison["agents_evaluated"] == 2

    def test_sorted_by_composite_score_descending(self, tmp_path: Path):
        replay_dir = tmp_path / "replays"
        _write_replay(replay_dir, "agent-a", "BUG-001", 60.0, 1.0, False)
        _write_replay(replay_dir, "agent-a", "FEAT-001", 60.0, 1.0, False)
        _write_replay(replay_dir, "agent-b", "BUG-001", 95.0, 0.5, True)
        _write_replay(replay_dir, "agent-b", "FEAT-001", 95.0, 0.5, True)

        arena = AgentArena(_make_config(), suite=_make_suite())
        results = arena.run_all(replay_dir=replay_dir)

        assert results[0].composite_score >= results[1].composite_score
        assert results[0].agent == "agent-b"
