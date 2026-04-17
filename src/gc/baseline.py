"""Baseline capture and comparison for drift detection."""

from __future__ import annotations

import json
from pathlib import Path

from armature._internal.types import BaselineSnapshot


class BaselineManager:
    """Manages quality baselines for regression detection."""

    def __init__(self, baselines_dir: Path) -> None:
        self.baselines_dir = baselines_dir
        self.baselines_dir.mkdir(parents=True, exist_ok=True)

    def save(self, spec_id: str, snapshot: BaselineSnapshot) -> Path:
        """Save a baseline snapshot."""
        path = self.baselines_dir / f"{spec_id}.json"
        data = {
            "timestamp": snapshot.timestamp,
            "lint_violations": snapshot.lint_violations,
            "type_errors": snapshot.type_errors,
            "test_passed": snapshot.test_passed,
            "test_failed": snapshot.test_failed,
            "coverage_pct": snapshot.coverage_pct,
            **snapshot.extra,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def load(self, spec_id: str) -> BaselineSnapshot | None:
        """Load a baseline snapshot, returning None if not found."""
        path = self.baselines_dir / f"{spec_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return BaselineSnapshot(
            timestamp=data.get("timestamp", ""),
            lint_violations=data.get("lint_violations", 0),
            type_errors=data.get("type_errors", 0),
            test_passed=data.get("test_passed", 0),
            test_failed=data.get("test_failed", 0),
            coverage_pct=data.get("coverage_pct", 0.0),
        )

    def diff(self, baseline: BaselineSnapshot, current: BaselineSnapshot) -> dict:
        """Compare current metrics against baseline."""
        lint_delta = current.lint_violations - baseline.lint_violations
        type_delta = current.type_errors - baseline.type_errors
        test_fail_delta = current.test_failed - baseline.test_failed

        return {
            "lint_delta": lint_delta,
            "type_delta": type_delta,
            "test_fail_delta": test_fail_delta,
            "has_regression": lint_delta > 0 or type_delta > 0 or test_fail_delta > 0,
            "drift": "growing" if (lint_delta > 0 or type_delta > 0) else
                     "improving" if (lint_delta < 0 or type_delta < 0) else "stable",
        }
