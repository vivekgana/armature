"""Quality score calculator -- aggregates check results into a single score."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

from armature._internal.subprocess_utils import run_tool
from armature._internal.types import BaselineSnapshot, CheckResult
from armature.config.schema import QualityConfig


def run_quality_checks(config: QualityConfig, root: Path, *, file_path: str | None = None) -> list[CheckResult]:
    """Run all enabled quality checks and return results."""
    results: list[CheckResult] = []

    checks = config.checks

    # Lint check
    if "lint" in checks:
        lint_cfg = checks["lint"]
        target = [file_path] if file_path else [str(root)]
        args = [lint_cfg.tool, *lint_cfg.args, *target]
        result = run_tool(args, cwd=root, timeout=30)

        violation_count = _count_output_lines(result.stdout)
        passed = result.ok
        score = 1.0 if passed else max(0.0, 1.0 - violation_count * 0.05)

        results.append(CheckResult(
            name="lint",
            passed=passed,
            violation_count=violation_count,
            details=f"{lint_cfg.tool}: {violation_count} violation(s)" if not passed else f"{lint_cfg.tool}: clean",
            score=score,
        ))

    # Type check
    if "type_check" in checks:
        tc_cfg = checks["type_check"]
        target = [file_path] if file_path else [str(root)]
        args = [tc_cfg.tool, *tc_cfg.args, *target]
        result = run_tool(args, cwd=root, timeout=60)

        error_count = sum(1 for line in result.stdout.split("\n") if ": error:" in line)
        passed = result.ok
        score = 1.0 if passed else max(0.0, 1.0 - error_count * 0.1)

        results.append(CheckResult(
            name="type_check",
            passed=passed,
            violation_count=error_count,
            details=f"{tc_cfg.tool}: {error_count} error(s)" if not passed else f"{tc_cfg.tool}: clean",
            score=score,
        ))

    # Test check (only for whole-project mode)
    if "test" in checks and file_path is None:
        test_cfg = checks["test"]
        args = [test_cfg.tool, *test_cfg.args]
        result = run_tool(args, cwd=root, timeout=120)

        import re
        passed_count = int(m.group(1)) if (m := re.search(r"(\d+) passed", result.stdout)) else 0
        failed_count = int(m.group(1)) if (m := re.search(r"(\d+) failed", result.stdout)) else 0
        passed = result.ok
        score = 1.0 if passed else max(0.0, 1.0 - failed_count * 0.2)

        results.append(CheckResult(
            name="test",
            passed=passed,
            violation_count=failed_count,
            details=f"{test_cfg.tool}: {passed_count} passed, {failed_count} failed",
            score=score,
        ))

    return results


def capture_baseline_snapshot(config: QualityConfig, root: Path) -> BaselineSnapshot:
    """Capture current quality metrics as a baseline snapshot."""
    from datetime import datetime

    results = run_quality_checks(config, root)
    lint_violations = 0
    type_errors = 0
    test_passed = 0
    test_failed = 0

    for r in results:
        if r.name == "lint":
            lint_violations = r.violation_count
        elif r.name == "type_check":
            type_errors = r.violation_count
        elif r.name == "test":
            test_passed = int(r.details.split(" passed")[0].split()[-1]) if "passed" in r.details else 0
            test_failed = r.violation_count

    return BaselineSnapshot(
        timestamp=datetime.now(UTC).isoformat(),
        lint_violations=lint_violations,
        type_errors=type_errors,
        test_passed=test_passed,
        test_failed=test_failed,
    )


def _count_output_lines(output: str) -> int:
    """Count non-empty lines in tool output."""
    return len([line for line in output.strip().split("\n") if line.strip()]) if output.strip() else 0
