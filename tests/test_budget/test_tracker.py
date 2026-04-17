"""Tests for budget/tracker.py -- JSONL-based session tracking."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from armature.budget.tracker import SessionTracker
from armature.config.schema import BudgetConfig


@pytest.fixture
def tracker(tmp_path: Path) -> SessionTracker:
    config = BudgetConfig(enabled=True, storage=".armature/budget/")
    return SessionTracker(config, tmp_path)


class TestSessionTracker:
    """Tests for SessionTracker logging and queries."""

    def test_log_creates_jsonl(self, tracker: SessionTracker, tmp_path: Path):
        tracker.log("SPEC-001", "build", 10000, 0.50)
        log_path = tmp_path / ".armature" / "budget" / "SPEC-001_cost.jsonl"
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["spec_id"] == "SPEC-001"
        assert entry["tokens"] == 10000

    def test_log_appends(self, tracker: SessionTracker):
        tracker.log("SPEC-001", "build", 10000, 0.50)
        tracker.log("SPEC-001", "test", 5000, 0.25)
        usage = tracker.get_usage("SPEC-001")
        assert usage["requests"] == 2
        assert usage["total_tokens"] == 15000

    def test_log_extended_fields(self, tracker: SessionTracker, tmp_path: Path):
        tracker.log(
            "SPEC-001", "build", 10000, 0.50,
            task_id="task-1", model="claude-sonnet", provider="anthropic",
            input_tokens=6000, output_tokens=4000, intent="code_gen",
        )
        log_path = tmp_path / ".armature" / "budget" / "SPEC-001_cost.jsonl"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["task_id"] == "task-1"
        assert entry["model"] == "claude-sonnet"
        assert entry["input_tokens"] == 6000

    def test_get_usage_empty_spec(self, tracker: SessionTracker):
        usage = tracker.get_usage("NONEXISTENT")
        assert usage["total_tokens"] == 0
        assert usage["requests"] == 0

    def test_get_usage_phases(self, tracker: SessionTracker):
        tracker.log("SPEC-001", "build", 20000, 0.40)
        tracker.log("SPEC-001", "test", 10000, 0.20)
        usage = tracker.get_usage("SPEC-001")
        assert "build" in usage["phases"]
        assert "test" in usage["phases"]
        assert usage["phases"]["build"]["tokens"] == 20000

    def test_get_usage_by_provider(self, tracker: SessionTracker):
        tracker.log("SPEC-001", "build", 10000, 0.50, provider="anthropic", model="claude-sonnet")
        tracker.log("SPEC-001", "build", 8000, 0.30, provider="openai", model="gpt-4o")
        result = tracker.get_usage_by_provider("SPEC-001")
        assert "anthropic" in result
        assert "openai" in result
        assert result["anthropic"]["tokens"] == 10000

    def test_get_usage_by_intent(self, tracker: SessionTracker):
        tracker.log("SPEC-001", "build", 10000, 0.50, intent="code_gen")
        tracker.log("SPEC-001", "build", 5000, 0.25, intent="test_gen")
        result = tracker.get_usage_by_intent("SPEC-001")
        assert "code_gen" in result
        assert result["code_gen"]["requests"] == 1

    def test_get_semantic_cache_stats(self, tracker: SessionTracker):
        tracker.log("SPEC-001", "build", 10000, 0.50, semantic_cache_hit=False)
        tracker.log("SPEC-001", "build", 10000, 0.00, semantic_cache_hit=True)
        stats = tracker.get_semantic_cache_stats("SPEC-001")
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_is_over_budget(self, tracker: SessionTracker):
        # Medium tier: 500K tokens
        tracker.log("SPEC-001", "build", 600_000, 15.0)
        assert tracker.is_over_budget("SPEC-001", "medium") is True
        assert tracker.is_over_budget("SPEC-001", "high") is False

    def test_list_specs(self, tracker: SessionTracker):
        tracker.log("SPEC-001", "build", 100, 0.01)
        tracker.log("SPEC-002", "build", 100, 0.01)
        specs = tracker.list_specs()
        assert "SPEC-001" in specs
        assert "SPEC-002" in specs

    def test_get_optimization_suggestions_high_usage(self, tracker: SessionTracker):
        # Push past 80% of medium tier (500K)
        tracker.log("SPEC-001", "build", 450_000, 9.0)
        suggestions = tracker.get_optimization_suggestions("SPEC-001")
        assert len(suggestions) > 0
        assert any("token budget" in s.lower() or "approaching" in s.lower() for s in suggestions)

    def test_cross_spec_trends(self, tracker: SessionTracker):
        tracker.log("SPEC-001", "build", 10000, 0.50)
        tracker.log("SPEC-002", "build", 20000, 1.00)
        trends = tracker.get_cross_spec_trends()
        assert len(trends) == 2
        assert trends[0]["spec_id"] == "SPEC-001"
