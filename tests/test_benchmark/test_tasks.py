"""Tests for benchmark/tasks.py -- task definitions and loading."""

from __future__ import annotations

from pathlib import Path

import yaml

from armature.benchmark.tasks import (
    ArenaSuite,
    BenchmarkTask,
    GradeBoundaries,
    ScoringWeights,
    SWEBenchDataset,
    filter_tasks,
    load_arena_tasks,
    load_swebench_dataset,
    validate_tasks,
)

_DEFAULTS = dict(language="python", verification="pytest")


def _sample_tasks() -> list[BenchmarkTask]:
    return [
        BenchmarkTask(
            id="BUG-001", category="bugfix", description="Fix null ptr",
            difficulty="easy", estimated_tokens=10000, **_DEFAULTS,
        ),
        BenchmarkTask(
            id="FEAT-001", category="feature", description="Add pagination",
            difficulty="medium", estimated_tokens=30000, **_DEFAULTS,
        ),
        BenchmarkTask(
            id="REF-001", category="refactor", description="Extract class",
            difficulty="hard", estimated_tokens=50000, **_DEFAULTS,
        ),
        BenchmarkTask(
            id="TEST-001", category="test_gen", description="Add unit tests",
            difficulty="easy", estimated_tokens=15000, **_DEFAULTS,
        ),
        BenchmarkTask(
            id="DOC-001", category="documentation", description="API docs",
            difficulty="easy", estimated_tokens=8000,
            language="python", verification="check_md",
        ),
    ]


class TestBenchmarkTask:
    """Tests for BenchmarkTask dataclass."""

    def test_creation(self):
        task = BenchmarkTask(
            id="BUG-001", category="bugfix", description="Fix bug",
            difficulty="easy", language="python",
            estimated_tokens=10000, verification="pytest",
        )
        assert task.id == "BUG-001"
        assert task.category == "bugfix"
        assert task.files_touched == 1

    def test_frozen(self):
        task = BenchmarkTask(
            id="T-1", category="bugfix", description="x",
            difficulty="easy", language="python",
            estimated_tokens=100, verification="",
        )
        try:
            task.id = "T-2"  # type: ignore[misc]
            raise AssertionError("Should be frozen")
        except AttributeError:
            pass


class TestFilterTasks:
    """Tests for filter_tasks()."""

    def test_filter_by_category(self):
        tasks = _sample_tasks()
        result = filter_tasks(tasks, categories={"bugfix", "feature"})
        assert len(result) == 2
        assert all(t.category in {"bugfix", "feature"} for t in result)

    def test_filter_by_difficulty(self):
        tasks = _sample_tasks()
        result = filter_tasks(tasks, difficulties={"easy"})
        assert all(t.difficulty == "easy" for t in result)

    def test_no_filter(self):
        tasks = _sample_tasks()
        result = filter_tasks(tasks)
        assert len(result) == len(tasks)

    def test_combined_filter(self):
        tasks = _sample_tasks()
        result = filter_tasks(tasks, categories={"bugfix"}, difficulties={"easy"})
        assert len(result) == 1
        assert result[0].id == "BUG-001"


class TestValidateTasks:
    """Tests for validate_tasks()."""

    def test_valid_tasks(self):
        errors = validate_tasks(_sample_tasks())
        assert errors == []

    def test_duplicate_id(self):
        tasks = [
            BenchmarkTask(
                id="BUG-001", category="bugfix", description="A",
                difficulty="easy", **_DEFAULTS, estimated_tokens=1000,
            ),
            BenchmarkTask(
                id="BUG-001", category="bugfix", description="B",
                difficulty="easy", **_DEFAULTS, estimated_tokens=1000,
            ),
        ]
        errors = validate_tasks(tasks)
        assert any("Duplicate" in e for e in errors)

    def test_invalid_category(self):
        tasks = [
            BenchmarkTask(
                id="X-001", category="invalid", description="A",
                difficulty="easy", **_DEFAULTS, estimated_tokens=1000,
            ),
        ]
        errors = validate_tasks(tasks)
        assert any("invalid category" in e for e in errors)

    def test_invalid_difficulty(self):
        tasks = [
            BenchmarkTask(
                id="X-001", category="bugfix", description="A",
                difficulty="extreme", **_DEFAULTS, estimated_tokens=1000,
            ),
        ]
        errors = validate_tasks(tasks)
        assert any("invalid difficulty" in e for e in errors)

    def test_negative_tokens(self):
        tasks = [
            BenchmarkTask(
                id="X-001", category="bugfix", description="A",
                difficulty="easy", **_DEFAULTS, estimated_tokens=-1,
            ),
        ]
        errors = validate_tasks(tasks)
        assert any("positive" in e for e in errors)


class TestLoadArenaTasks:
    """Tests for load_arena_tasks() YAML loading."""

    def test_load_from_yaml(self, tmp_path: Path):
        data = {
            "tasks": [
                {
                    "id": "BUG-001", "category": "bugfix",
                    "description": "Fix", "difficulty": "easy",
                    "language": "python", "estimated_tokens": 10000,
                },
                {
                    "id": "FEAT-001", "category": "feature",
                    "description": "Add", "difficulty": "medium",
                    "language": "python", "estimated_tokens": 20000,
                },
            ],
            "agents": {
                "claude-code": {
                    "model": "claude-sonnet-4",
                    "provider": "anthropic",
                    "description": "Claude Code",
                },
            },
            "scoring": {
                "quality_weight": 0.50, "efficiency_weight": 0.20,
                "heal_weight": 0.15, "cache_weight": 0.15,
            },
            "grades": {"A": 92, "B+": 87, "B": 82, "B-": 77, "C": 67},
        }
        yaml_file = tmp_path / "arena_tasks.yaml"
        yaml_file.write_text(yaml.dump(data), encoding="utf-8")

        suite = load_arena_tasks(yaml_file)
        assert len(suite.tasks) == 2
        assert "claude-code" in suite.agents
        assert suite.scoring.quality == 0.50
        assert suite.grades.A == 92

    def test_missing_file_returns_empty(self, tmp_path: Path):
        suite = load_arena_tasks(tmp_path / "nonexistent.yaml")
        assert isinstance(suite, ArenaSuite)

    def test_defaults_for_missing_fields(self, tmp_path: Path):
        data = {
            "tasks": [
                {"id": "T-1", "category": "bugfix",
                 "description": "x", "difficulty": "easy"},
            ],
        }
        yaml_file = tmp_path / "arena.yaml"
        yaml_file.write_text(yaml.dump(data), encoding="utf-8")
        suite = load_arena_tasks(yaml_file)
        assert suite.tasks[0].language == "python"
        assert suite.tasks[0].estimated_tokens == 30000


class TestLoadSWEBenchDataset:
    """Tests for load_swebench_dataset() YAML loading."""

    def test_load_from_yaml(self, tmp_path: Path):
        data = {
            "metadata": {"dataset": "swebench-lite", "version": "2.0"},
            "tasks": [
                {
                    "task_id": "django__django-11099",
                    "repo": "django/django", "category": "bugfix",
                    "difficulty": "medium",
                    "description": "Fix queryset",
                },
            ],
        }
        yaml_file = tmp_path / "swebench.yaml"
        yaml_file.write_text(yaml.dump(data), encoding="utf-8")

        ds = load_swebench_dataset(yaml_file)
        assert ds.name == "swebench-lite"
        assert ds.version == "2.0"
        assert len(ds.tasks) == 1

    def test_missing_file_returns_empty(self, tmp_path: Path):
        ds = load_swebench_dataset(tmp_path / "nonexistent.yaml")
        assert isinstance(ds, SWEBenchDataset)
        assert ds.tasks == []


class TestScoringWeightsDefaults:
    def test_default_weights_sum_to_one(self):
        w = ScoringWeights()
        total = w.quality + w.efficiency + w.heal + w.cache
        assert abs(total - 1.0) < 1e-10


class TestGradeBoundariesOrdering:
    def test_default_boundaries_descending(self):
        g = GradeBoundaries()
        assert g.A > g.B_plus > g.B > g.B_minus > g.C
