"""Tests for _internal/types.py -- shared type definitions."""

from __future__ import annotations

from armature._internal.types import (
    BaselineSnapshot,
    CheckResult,
    CircuitState,
    Complexity,
    HealResult,
    QualityLevel,
    Severity,
    Violation,
)


class TestViolation:
    """Tests for Violation dataclass."""

    def test_str_format(self):
        v = Violation(
            file="src/models/user.py",
            line=42,
            rule="layer-boundary",
            message="CROSSED: models -> routes",
            remediation="Move to shared",
        )
        output = str(v)
        assert "src/models/user.py:42" in output
        assert "layer-boundary" in output
        assert "FIX:" in output

    def test_default_severity_is_error(self):
        v = Violation(file="f", line=1, rule="r", message="m", remediation="fix")
        assert v.severity == Severity.ERROR


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_defaults(self):
        r = CheckResult(name="lint", passed=True)
        assert r.violation_count == 0
        assert r.score == 1.0
        assert r.details == ""


class TestHealResult:
    """Tests for HealResult dataclass."""

    def test_basic(self):
        r = HealResult(failure_type="lint", attempt=2, fixed=True, remaining_errors=0)
        assert r.fixed is True
        assert r.attempt == 2


class TestEnums:
    """Tests for enum types."""

    def test_severity_values(self):
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"

    def test_circuit_state_values(self):
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_quality_level_values(self):
        assert QualityLevel.DRAFT.value == "draft"
        assert QualityLevel.REVIEW_READY.value == "review_ready"
        assert QualityLevel.MERGE_READY.value == "merge_ready"

    def test_complexity_values(self):
        assert Complexity.LOW.value == "low"
        assert Complexity.MEDIUM.value == "medium"
        assert Complexity.HIGH.value == "high"
        assert Complexity.CRITICAL.value == "critical"


class TestBaselineSnapshot:
    """Tests for BaselineSnapshot dataclass."""

    def test_defaults(self):
        s = BaselineSnapshot(timestamp="2026-01-01T00:00:00Z")
        assert s.lint_violations == 0
        assert s.type_errors == 0
        assert s.test_passed == 0
        assert s.test_failed == 0
        assert s.coverage_pct == 0.0
        assert s.extra == {}
