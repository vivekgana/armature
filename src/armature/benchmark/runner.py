"""Base benchmark runner -- executes tasks and captures metrics.

Runs in replay mode (pre-recorded agent outputs) or measurement mode
(post-hoc analysis of existing code changes).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from armature._internal.types import BenchmarkTaskResult, CheckResult
from armature.benchmark.tasks import BenchmarkTask
from armature.config.schema import ArmatureConfig


class BenchmarkRunner:
    """Execute benchmark tasks and capture quality + budget + heal metrics."""

    def __init__(self, config: ArmatureConfig, root: Path | None = None) -> None:
        self.config = config
        self.root = root or Path.cwd()

    def run_task(
        self,
        task: BenchmarkTask,
        agent: str,
        *,
        replay_dir: Path | None = None,
    ) -> BenchmarkTaskResult:
        """Execute one benchmark task and capture all metrics.

        In replay mode, reads pre-recorded results from replay_dir.
        In live mode, runs quality checks on the current workspace.
        """
        start_time = time.monotonic()

        if replay_dir:  # noqa: SIM108
            result = self._run_from_replay(task, agent, replay_dir)
        else:
            result = self._run_live(task, agent)

        elapsed = time.monotonic() - start_time
        return BenchmarkTaskResult(
            task_id=task.id,
            agent=agent,
            quality_score=result["quality_score"],
            budget_tokens=result["budget_tokens"],
            budget_cost_usd=result["budget_cost_usd"],
            heal_attempts=result["heal_attempts"],
            heal_fixed=result["heal_fixed"],
            cache_hits=result["cache_hits"],
            cache_total=result["cache_total"],
            duration_seconds=round(elapsed, 2),
            passed=result["passed"],
            check_results=result["check_results"],
        )

    def _run_live(self, task: BenchmarkTask, agent: str) -> dict[str, Any]:
        """Run quality checks on the current workspace."""
        from armature.quality.scorer import run_quality_checks

        results = run_quality_checks(
            self.config.quality, self.root,
            project_src_dir=self.config.project.src_dir,
            project_test_dir=self.config.project.test_dir,
        )

        total_weight = sum(r.weight for r in results)
        quality_score = (
            sum(r.score * r.weight for r in results) / total_weight * 100.0
            if total_weight > 0 else 0.0
        )

        heal_attempts = 0
        heal_fixed = 0
        failed_checks = {r.name for r in results if not r.passed}
        if failed_checks and self.config.heal.enabled:
            from armature.heal.pipeline import HealPipeline
            pipeline = HealPipeline(self.config.heal)
            heal_type_map = {"lint": "lint", "type_check": "type", "test": "test"}
            failure_types = {heal_type_map.get(c, c) for c in failed_checks if c in heal_type_map}
            if failure_types:
                heal_results = pipeline.heal(failure_types)
                heal_attempts = len(heal_results)
                heal_fixed = sum(1 for r in heal_results if r.fixed)

        return {
            "quality_score": round(quality_score, 1),
            "budget_tokens": 0,
            "budget_cost_usd": 0.0,
            "heal_attempts": heal_attempts,
            "heal_fixed": heal_fixed,
            "cache_hits": 0,
            "cache_total": 0,
            "passed": all(r.passed for r in results),
            "check_results": results,
        }

    def _run_from_replay(
        self, task: BenchmarkTask, agent: str, replay_dir: Path,
    ) -> dict[str, Any]:
        """Load pre-recorded results from replay directory."""
        replay_file = replay_dir / agent / f"{task.id}.json"
        if not replay_file.exists():
            return {
                "quality_score": 0.0,
                "budget_tokens": task.estimated_tokens,
                "budget_cost_usd": 0.0,
                "heal_attempts": 0,
                "heal_fixed": 0,
                "cache_hits": 0,
                "cache_total": 0,
                "passed": False,
                "check_results": [],
            }

        data = json.loads(replay_file.read_text(encoding="utf-8"))
        check_results = [
            CheckResult(
                name=c["name"],
                passed=c["passed"],
                violation_count=c.get("violations", 0),
                details=c.get("details", ""),
                score=c.get("score", 1.0),
                weight=c.get("weight", 25),
            )
            for c in data.get("check_results", [])
        ]

        return {
            "quality_score": data.get("quality_score", 0.0),
            "budget_tokens": data.get("budget_tokens", task.estimated_tokens),
            "budget_cost_usd": data.get("budget_cost_usd", 0.0),
            "heal_attempts": data.get("heal_attempts", 0),
            "heal_fixed": data.get("heal_fixed", 0),
            "cache_hits": data.get("cache_hits", 0),
            "cache_total": data.get("cache_total", 0),
            "passed": data.get("passed", False),
            "check_results": check_results,
        }


def save_replay(
    result: BenchmarkTaskResult,
    replay_dir: Path,
) -> Path:
    """Save a benchmark result as a replay file for future runs."""
    agent_dir = replay_dir / result.agent
    agent_dir.mkdir(parents=True, exist_ok=True)

    replay_file = agent_dir / f"{result.task_id}.json"
    data = {
        "task_id": result.task_id,
        "agent": result.agent,
        "quality_score": result.quality_score,
        "budget_tokens": result.budget_tokens,
        "budget_cost_usd": result.budget_cost_usd,
        "heal_attempts": result.heal_attempts,
        "heal_fixed": result.heal_fixed,
        "cache_hits": result.cache_hits,
        "cache_total": result.cache_total,
        "passed": result.passed,
        "check_results": [
            {
                "name": c.name, "passed": c.passed,
                "violations": c.violation_count, "details": c.details,
                "score": c.score, "weight": c.weight,
            }
            for c in result.check_results
        ],
    }
    replay_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return replay_file
