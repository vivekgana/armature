"""Shared type definitions used across Armature modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    """Violation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CircuitState(StrEnum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class QualityLevel(StrEnum):
    """Quality gate levels."""
    DRAFT = "draft"
    REVIEW_READY = "review_ready"
    MERGE_READY = "merge_ready"


class Complexity(StrEnum):
    """Budget complexity tiers."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Violation:
    """A single architectural or quality violation.

    Messages include remediation instructions (OpenAI pattern):
    'Because the lints are custom, we write the error messages to inject
    remediation instructions into agent context.'
    """
    file: str
    line: int
    rule: str
    message: str
    remediation: str
    severity: Severity = Severity.ERROR

    def __str__(self) -> str:
        return f"{self.file}:{self.line} [{self.rule}] {self.message}\n  FIX: {self.remediation}"


@dataclass
class CheckResult:
    """Result of running a quality check (lint, type, test, etc.)."""
    name: str
    passed: bool
    violation_count: int = 0
    details: str = ""
    score: float = 1.0  # 0.0 to 1.0


@dataclass
class HealResult:
    """Result of a single self-heal attempt."""
    failure_type: str
    attempt: int
    fixed: bool
    remaining_errors: int
    details: str = ""


@dataclass
class GCFinding:
    """A single finding from a garbage collection agent."""
    agent: str
    category: str
    file: str
    message: str
    severity: Severity = Severity.WARNING


@dataclass
class BaselineSnapshot:
    """Quality metrics baseline for regression detection."""
    timestamp: str
    lint_violations: int = 0
    type_errors: int = 0
    test_passed: int = 0
    test_failed: int = 0
    coverage_pct: float = 0.0
    extra: dict[str, object] = field(default_factory=dict)
