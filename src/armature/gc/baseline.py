"""Baseline capture and comparison for drift detection."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from armature._internal.types import BaselineSnapshot
from armature._internal.validation import validate_spec_id


class BaselineManager:
    """Manages quality baselines for regression detection."""

    def __init__(self, baselines_dir: Path) -> None:
        self.baselines_dir = baselines_dir
        self.baselines_dir.mkdir(parents=True, exist_ok=True)

    def save(self, spec_id: str, snapshot: BaselineSnapshot) -> Path:
        """Save a baseline snapshot."""
        spec_id = validate_spec_id(spec_id)
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
        with tempfile.NamedTemporaryFile(
            mode="w", dir=self.baselines_dir, suffix=".json.tmp",
            delete=False, encoding="utf-8",
        ) as tmp:
            tmp.write(json.dumps(data, indent=2))
        try:
            Path(tmp.name).replace(path)
        except Exception:
            Path(tmp.name).unlink(missing_ok=True)
            raise
        return path

    def load(self, spec_id: str) -> BaselineSnapshot | None:
        """Load a baseline snapshot, returning None if not found."""
        spec_id = validate_spec_id(spec_id)
        path = self.baselines_dir / f"{spec_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        known = {"timestamp", "lint_violations", "type_errors", "test_passed", "test_failed", "coverage_pct"}
        return BaselineSnapshot(
            timestamp=data.get("timestamp", ""),
            lint_violations=data.get("lint_violations", 0),
            type_errors=data.get("type_errors", 0),
            test_passed=data.get("test_passed", 0),
            test_failed=data.get("test_failed", 0),
            coverage_pct=data.get("coverage_pct", 0.0),
            extra={k: v for k, v in data.items() if k not in known},
        )

    @staticmethod
    def _extra_int(snap: BaselineSnapshot, key: str) -> int:
        val = snap.extra.get(key, 0)
        return int(val) if isinstance(val, (int, float, str)) else 0

    def diff(self, baseline: BaselineSnapshot, current: BaselineSnapshot) -> dict[str, object]:
        """Compare current metrics against baseline."""
        lint_delta = current.lint_violations - baseline.lint_violations
        type_delta = current.type_errors - baseline.type_errors
        test_fail_delta = current.test_failed - baseline.test_failed

        complexity_delta = (
            self._extra_int(current, "complexity_over_threshold")
            - self._extra_int(baseline, "complexity_over_threshold")
        )
        security_delta = (
            self._extra_int(current, "security_findings")
            - self._extra_int(baseline, "security_findings")
        )
        vuln_delta = (
            self._extra_int(current, "vuln_count")
            - self._extra_int(baseline, "vuln_count")
        )

        has_regression = (
            lint_delta > 0 or type_delta > 0 or test_fail_delta > 0
            or complexity_delta > 0 or security_delta > 0 or vuln_delta > 0
        )

        return {
            "lint_delta": lint_delta,
            "type_delta": type_delta,
            "test_fail_delta": test_fail_delta,
            "complexity_delta": complexity_delta,
            "security_delta": security_delta,
            "vuln_delta": vuln_delta,
            "has_regression": has_regression,
            "drift": "growing" if (lint_delta > 0 or type_delta > 0) else
                     "improving" if (lint_delta < 0 or type_delta < 0) else "stable",
        }
