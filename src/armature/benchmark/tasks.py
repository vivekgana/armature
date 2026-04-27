"""Task definitions loader and validation for benchmark suites."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

VALID_CATEGORIES = frozenset({"bugfix", "feature", "refactor", "test_gen", "documentation"})
VALID_DIFFICULTIES = frozenset({"easy", "medium", "hard"})


@dataclass(frozen=True)
class BenchmarkTask:
    """A single benchmark task definition."""
    id: str
    category: str
    description: str
    difficulty: str
    language: str
    estimated_tokens: int
    verification: str
    files_touched: int = 1


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for one AI coding agent."""
    name: str
    model: str
    provider: str
    description: str = ""


@dataclass
class ScoringWeights:
    """Composite scoring weights for arena evaluation."""
    quality: float = 0.40
    efficiency: float = 0.25
    heal: float = 0.20
    cache: float = 0.15


@dataclass
class GradeBoundaries:
    """Grade assignment thresholds (composite score percentage)."""
    A: float = 90.0
    B_plus: float = 85.0
    B: float = 80.0
    B_minus: float = 75.0
    C: float = 65.0


@dataclass
class ArenaSuite:
    """Complete arena benchmark suite loaded from YAML."""
    tasks: list[BenchmarkTask]
    agents: dict[str, AgentConfig]
    scoring: ScoringWeights
    grades: GradeBoundaries


def load_arena_tasks(path: Path) -> ArenaSuite:
    """Load arena task definitions from YAML file."""
    if not path.exists():
        pkg_path = Path(__file__).parent.parent.parent / "data" / "arena_tasks.yaml"
        if pkg_path.exists():
            path = pkg_path
        else:
            return ArenaSuite(
                tasks=[], agents={},
                scoring=ScoringWeights(), grades=GradeBoundaries(),
            )

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    tasks = [
        BenchmarkTask(
            id=t["id"],
            category=t["category"],
            description=t["description"],
            difficulty=t["difficulty"],
            language=t.get("language", "python"),
            estimated_tokens=t.get("estimated_tokens", 30000),
            verification=t.get("verification", ""),
            files_touched=t.get("files_touched", 1),
        )
        for t in data.get("tasks", [])
    ]

    agents = {}
    for name, cfg in data.get("agents", {}).items():
        agents[name] = AgentConfig(
            name=name,
            model=cfg.get("model", ""),
            provider=cfg.get("provider", ""),
            description=cfg.get("description", ""),
        )

    scoring_data = data.get("scoring", {})
    scoring = ScoringWeights(
        quality=scoring_data.get("quality_weight", 0.40),
        efficiency=scoring_data.get("efficiency_weight", 0.25),
        heal=scoring_data.get("heal_weight", 0.20),
        cache=scoring_data.get("cache_weight", 0.15),
    )

    grades_data = data.get("grades", {})
    grades = GradeBoundaries(
        A=grades_data.get("A", 90),
        B_plus=grades_data.get("B+", 85),
        B=grades_data.get("B", 80),
        B_minus=grades_data.get("B-", 75),
        C=grades_data.get("C", 65),
    )

    return ArenaSuite(tasks=tasks, agents=agents, scoring=scoring, grades=grades)


@dataclass(frozen=True)
class SWEBenchTask:
    """A single SWE-bench task for correlation analysis."""
    task_id: str
    repo: str
    category: str
    difficulty: str
    language: str
    estimated_tokens: int
    description: str


@dataclass
class SWEBenchDataset:
    """SWE-bench correlation dataset loaded from YAML."""
    name: str
    version: str
    tasks: list[SWEBenchTask]
    expected_correlation: dict[str, dict[str, Any]]
    references: list[dict[str, Any]]


def load_swebench_dataset(path: Path) -> SWEBenchDataset:
    """Load SWE-bench correlation dataset from YAML file."""
    if not path.exists():
        pkg_path = Path(__file__).parent.parent.parent / "data" / "swebench_correlation.yaml"
        if pkg_path.exists():
            path = pkg_path
        else:
            return SWEBenchDataset(
                name="swebench-lite", version="0.0", tasks=[],
                expected_correlation={}, references=[],
            )

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    metadata = data.get("metadata", {})

    tasks = [
        SWEBenchTask(
            task_id=t["task_id"],
            repo=t.get("repo", ""),
            category=t.get("category", "bugfix"),
            difficulty=t.get("difficulty", "medium"),
            language=t.get("language", "python"),
            estimated_tokens=t.get("estimated_tokens", 30000),
            description=t.get("description", ""),
        )
        for t in data.get("tasks", [])
    ]

    return SWEBenchDataset(
        name=metadata.get("dataset", "swebench-lite"),
        version=metadata.get("version", "1.0"),
        tasks=tasks,
        expected_correlation=data.get("expected_correlation", {}),
        references=data.get("references", []),
    )


def filter_tasks(tasks: list[BenchmarkTask], categories: set[str] | None = None,
                 difficulties: set[str] | None = None) -> list[BenchmarkTask]:
    """Filter tasks by category and/or difficulty."""
    result = tasks
    if categories:
        result = [t for t in result if t.category in categories]
    if difficulties:
        result = [t for t in result if t.difficulty in difficulties]
    return result


def validate_tasks(tasks: list[BenchmarkTask]) -> list[str]:
    """Validate task definitions, return list of error messages."""
    errors: list[str] = []
    seen_ids: set[str] = set()

    for task in tasks:
        if task.id in seen_ids:
            errors.append(f"Duplicate task ID: {task.id}")
        seen_ids.add(task.id)

        if task.category not in VALID_CATEGORIES:
            errors.append(f"{task.id}: invalid category '{task.category}'")
        if task.difficulty not in VALID_DIFFICULTIES:
            errors.append(f"{task.id}: invalid difficulty '{task.difficulty}'")
        if task.estimated_tokens <= 0:
            errors.append(f"{task.id}: estimated_tokens must be positive")

    return errors
