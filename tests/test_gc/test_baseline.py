"""Tests for gc/baseline.py -- quality baseline management."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature._internal.types import BaselineSnapshot
from armature.gc.baseline import BaselineManager


@pytest.fixture
def manager(tmp_path: Path) -> BaselineManager:
    return BaselineManager(tmp_path / "baselines")


@pytest.fixture
def sample_snapshot() -> BaselineSnapshot:
    return BaselineSnapshot(
        timestamp="2026-01-15T10:00:00+00:00",
        lint_violations=5,
        type_errors=2,
        test_passed=100,
        test_failed=3,
        coverage_pct=87.5,
    )


class TestBaselineManager:
    """Tests for BaselineManager save/load/diff."""

    def test_save_creates_file(self, manager: BaselineManager, sample_snapshot: BaselineSnapshot):
        path = manager.save("SPEC-001", sample_snapshot)
        assert path.exists()
        assert path.name == "SPEC-001.json"

    def test_load_returns_snapshot(self, manager: BaselineManager, sample_snapshot: BaselineSnapshot):
        manager.save("SPEC-001", sample_snapshot)
        loaded = manager.load("SPEC-001")
        assert loaded is not None
        assert loaded.lint_violations == 5
        assert loaded.type_errors == 2
        assert loaded.test_passed == 100

    def test_load_missing_returns_none(self, manager: BaselineManager):
        result = manager.load("NONEXISTENT")
        assert result is None

    def test_diff_no_regression(self, manager: BaselineManager):
        baseline = BaselineSnapshot(timestamp="", lint_violations=5, type_errors=2, test_failed=1)
        current = BaselineSnapshot(timestamp="", lint_violations=3, type_errors=1, test_failed=0)
        diff = manager.diff(baseline, current)
        assert diff["has_regression"] is False
        assert diff["lint_delta"] == -2
        assert diff["drift"] == "improving"

    def test_diff_with_regression(self, manager: BaselineManager):
        baseline = BaselineSnapshot(timestamp="", lint_violations=5, type_errors=2, test_failed=1)
        current = BaselineSnapshot(timestamp="", lint_violations=8, type_errors=3, test_failed=2)
        diff = manager.diff(baseline, current)
        assert diff["has_regression"] is True
        assert diff["lint_delta"] == 3
        assert diff["drift"] == "growing"

    def test_diff_stable(self, manager: BaselineManager):
        baseline = BaselineSnapshot(timestamp="", lint_violations=5, type_errors=2, test_failed=1)
        current = BaselineSnapshot(timestamp="", lint_violations=5, type_errors=2, test_failed=1)
        diff = manager.diff(baseline, current)
        assert diff["has_regression"] is False
        assert diff["drift"] == "stable"
