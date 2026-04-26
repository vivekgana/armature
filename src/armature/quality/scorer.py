"""Quality score calculator -- aggregates check results into a single score."""

from __future__ import annotations

import ast
import json
from datetime import UTC
from pathlib import Path

from armature._internal.subprocess_utils import run_tool
from armature._internal.types import BaselineSnapshot, CheckResult
from armature.config.schema import InternalCheckConfig, QualityConfig, ToolCheckConfig

_SOURCE_EXTENSIONS = frozenset({".py", ".ts", ".tsx", ".js", ".jsx"})
_COMMENT_PREFIXES = ("#", "//")


def run_quality_checks(
    config: QualityConfig,
    root: Path,
    *,
    file_path: str | None = None,
    project_src_dir: str = "src/",
    project_test_dir: str = "tests/",
) -> list[CheckResult]:
    """Run all enabled quality checks and return results."""
    results: list[CheckResult] = []
    checks = config.checks

    if "lint" in checks:
        r = _check_lint(checks["lint"], root, file_path)
        if r:
            results.append(r)

    if "type_check" in checks:
        r = _check_type(checks["type_check"], root, file_path)
        if r:
            results.append(r)

    if "test" in checks and file_path is None:
        r = _check_test(checks["test"], root)
        if r:
            results.append(r)

    if "complexity" in checks and file_path is None:
        r = _check_complexity(checks["complexity"], root, project_src_dir)
        if r:
            results.append(r)

    if "security" in checks and file_path is None:
        r = _check_security(checks["security"], root, project_src_dir)
        if r:
            results.append(r)

    if "test_ratio" in checks and file_path is None:
        r = _check_test_ratio(checks["test_ratio"], root, project_src_dir, project_test_dir)
        if r:
            results.append(r)

    if "docstring" in checks and file_path is None:
        r = _check_docstring(checks["docstring"], root, project_src_dir)
        if r:
            results.append(r)

    if "dependency_audit" in checks and file_path is None:
        r = _check_dependency_audit(checks["dependency_audit"], root)
        if r:
            results.append(r)

    return results


# ---------------------------------------------------------------------------
# Individual check implementations
# ---------------------------------------------------------------------------

def _check_lint(cfg: ToolCheckConfig | InternalCheckConfig, root: Path, file_path: str | None) -> CheckResult | None:
    if not isinstance(cfg, ToolCheckConfig) or not cfg.tool:
        return None
    target = [file_path] if file_path else [str(root)]
    args = [cfg.tool, *cfg.args, *target]
    result = run_tool(args, cwd=root, timeout=30)
    if result.returncode == -1:
        return None

    violation_count = _count_output_lines(result.stdout)
    passed = result.ok
    score = 1.0 if passed else max(0.0, 1.0 - violation_count * 0.05)
    return CheckResult(
        name="lint", passed=passed, violation_count=violation_count,
        details=f"{cfg.tool}: {violation_count} violation(s)" if not passed else f"{cfg.tool}: clean",
        score=score, weight=cfg.weight,
    )


def _check_type(cfg: ToolCheckConfig | InternalCheckConfig, root: Path, file_path: str | None) -> CheckResult | None:
    if not isinstance(cfg, ToolCheckConfig) or not cfg.tool:
        return None
    target = [file_path] if file_path else [str(root)]
    args = [cfg.tool, *cfg.args, *target]
    result = run_tool(args, cwd=root, timeout=60)
    if result.returncode == -1:
        return None

    error_count = sum(1 for line in result.stdout.split("\n") if ": error:" in line)
    passed = result.ok
    score = 1.0 if passed else max(0.0, 1.0 - error_count * 0.1)
    return CheckResult(
        name="type_check", passed=passed, violation_count=error_count,
        details=f"{cfg.tool}: {error_count} error(s)" if not passed else f"{cfg.tool}: clean",
        score=score, weight=cfg.weight,
    )


def _check_test(cfg: ToolCheckConfig | InternalCheckConfig, root: Path) -> CheckResult | None:
    if not isinstance(cfg, ToolCheckConfig) or not cfg.tool:
        return None
    args = [cfg.tool, *cfg.args]
    result = run_tool(args, cwd=root, timeout=120)
    if result.returncode == -1:
        return None

    import re
    passed_count = int(m.group(1)) if (m := re.search(r"(\d+) passed", result.stdout)) else 0
    failed_count = int(m.group(1)) if (m := re.search(r"(\d+) failed", result.stdout)) else 0
    passed = result.ok
    score = 1.0 if passed else max(0.0, 1.0 - failed_count * 0.2)
    return CheckResult(
        name="test", passed=passed, violation_count=failed_count,
        details=f"{cfg.tool}: {passed_count} passed, {failed_count} failed",
        score=score, weight=cfg.weight,
    )


def _check_complexity(cfg: ToolCheckConfig | InternalCheckConfig, root: Path, src_dir: str) -> CheckResult | None:
    threshold = 10.0
    weight = 15
    if isinstance(cfg, InternalCheckConfig):
        threshold = cfg.threshold or 10.0
        weight = cfg.weight
        args = ["radon", "cc", "--json", str(root / src_dir)]
    elif isinstance(cfg, ToolCheckConfig):
        weight = cfg.weight
        args = [cfg.tool, *cfg.args, str(root / src_dir)]
    else:
        return None

    result = run_tool(args, cwd=root, timeout=60)
    if result.returncode == -1:
        return None

    over_threshold = 0
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
        for functions in data.values():
            if isinstance(functions, list):
                for func in functions:
                    if isinstance(func, dict) and func.get("complexity", 0) > threshold:
                        over_threshold += 1
    except (json.JSONDecodeError, TypeError):
        pass

    passed = over_threshold == 0
    score = max(0.0, 1.0 - over_threshold * 0.1)
    return CheckResult(
        name="complexity", passed=passed, violation_count=over_threshold,
        details=f"radon: {over_threshold} function(s) exceed CC threshold {threshold:.0f}",
        score=score, weight=weight,
    )


def _check_security(cfg: ToolCheckConfig | InternalCheckConfig, root: Path, src_dir: str) -> CheckResult | None:
    if isinstance(cfg, ToolCheckConfig) and cfg.tool:
        target_dir = str(root / src_dir)
        args = [cfg.tool, *cfg.args, target_dir]
        result = run_tool(args, cwd=root, timeout=60)
        if result.returncode == -1:
            return None

        findings = 0
        try:
            data = json.loads(result.stdout) if result.stdout.strip() else {}
            for issue in data.get("results", []):
                severity = issue.get("issue_severity", "").upper()
                if severity in ("HIGH", "MEDIUM"):
                    findings += 1
        except (json.JSONDecodeError, TypeError):
            pass

        passed = findings == 0
        score = max(0.0, 1.0 - findings * 0.15)
        return CheckResult(
            name="security", passed=passed, violation_count=findings,
            details=f"{cfg.tool}: {findings} security finding(s)" if findings else f"{cfg.tool}: clean",
            score=score, weight=cfg.weight,
        )

    return None


def _check_test_ratio(
    cfg: ToolCheckConfig | InternalCheckConfig, root: Path, src_dir: str, test_dir: str,
) -> CheckResult | None:
    if not isinstance(cfg, InternalCheckConfig):
        return None

    threshold = cfg.threshold or 0.5
    src_loc = _count_source_lines(root / src_dir)
    test_loc = _count_source_lines(root / test_dir)
    ratio = test_loc / src_loc if src_loc > 0 else 0.0

    passed = ratio >= threshold
    score = min(1.0, ratio / threshold) if threshold > 0 else 1.0
    return CheckResult(
        name="test_ratio", passed=passed,
        violation_count=0 if passed else 1,
        details=f"test_ratio: {ratio:.2f} (src {src_loc} LOC, test {test_loc} LOC, threshold {threshold:.2f})",
        score=score, weight=cfg.weight,
    )


def _check_docstring(cfg: ToolCheckConfig | InternalCheckConfig, root: Path, src_dir: str) -> CheckResult | None:
    if not isinstance(cfg, InternalCheckConfig):
        return None

    total, documented = _analyze_docstrings(root / src_dir)
    coverage_pct = (documented / total * 100.0) if total > 0 else 100.0

    passed = coverage_pct >= (cfg.min_coverage_pct or 0.0)
    score = coverage_pct / 100.0
    return CheckResult(
        name="docstring", passed=passed,
        violation_count=total - documented,
        details=f"docstring: {documented}/{total} public symbols documented ({coverage_pct:.0f}%)",
        score=score, weight=cfg.weight,
    )


def _check_dependency_audit(cfg: ToolCheckConfig | InternalCheckConfig, root: Path) -> CheckResult | None:
    if not isinstance(cfg, ToolCheckConfig) or not cfg.tool:
        return None

    args = [cfg.tool, *cfg.args]
    result = run_tool(args, cwd=root, timeout=120)
    if result.returncode == -1:
        return None

    vuln_count = 0
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
        if cfg.tool == "pip-audit":
            for dep in data if isinstance(data, list) else data.get("dependencies", []):
                vulns = dep.get("vulns", [])
                vuln_count += len(vulns)
        elif cfg.tool == "npm":
            for _name, info in data.get("vulnerabilities", {}).items():
                if info.get("severity", "") in ("high", "critical"):
                    vuln_count += 1
    except (json.JSONDecodeError, TypeError):
        pass

    passed = vuln_count == 0
    score = max(0.0, 1.0 - vuln_count * 0.2)
    return CheckResult(
        name="dependency_audit", passed=passed, violation_count=vuln_count,
        details=f"{cfg.tool}: {vuln_count} vulnerability(ies)" if vuln_count else f"{cfg.tool}: clean",
        score=score, weight=cfg.weight,
    )


# ---------------------------------------------------------------------------
# Baseline capture
# ---------------------------------------------------------------------------

def capture_baseline_snapshot(
    config: QualityConfig,
    root: Path,
    *,
    project_src_dir: str = "src/",
    project_test_dir: str = "tests/",
) -> BaselineSnapshot:
    """Capture current quality metrics as a baseline snapshot."""
    from datetime import datetime

    results = run_quality_checks(
        config, root, project_src_dir=project_src_dir, project_test_dir=project_test_dir,
    )
    lint_violations = 0
    type_errors = 0
    test_passed = 0
    test_failed = 0
    extra: dict[str, object] = {}

    for r in results:
        if r.name == "lint":
            lint_violations = r.violation_count
        elif r.name == "type_check":
            type_errors = r.violation_count
        elif r.name == "test":
            test_passed = int(r.details.split(" passed")[0].split()[-1]) if "passed" in r.details else 0
            test_failed = r.violation_count
        elif r.name == "complexity":
            extra["complexity_over_threshold"] = r.violation_count
        elif r.name == "security":
            extra["security_findings"] = r.violation_count
        elif r.name == "test_ratio":
            extra["test_ratio"] = r.score
        elif r.name == "docstring":
            extra["docstring_coverage_pct"] = r.score * 100.0
        elif r.name == "dependency_audit":
            extra["vuln_count"] = r.violation_count

    return BaselineSnapshot(
        timestamp=datetime.now(UTC).isoformat(),
        lint_violations=lint_violations,
        type_errors=type_errors,
        test_passed=test_passed,
        test_failed=test_failed,
        extra=extra,
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _count_output_lines(output: str) -> int:
    """Count non-empty lines in tool output."""
    return len([line for line in output.strip().split("\n") if line.strip()]) if output.strip() else 0


def _count_source_lines(directory: Path) -> int:
    """Count non-blank, non-comment lines in source files."""
    if not directory.exists():
        return 0
    total = 0
    for path in directory.rglob("*"):
        if path.suffix in _SOURCE_EXTENSIONS and path.is_file():
            try:
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                    stripped = line.strip()
                    if stripped and not any(stripped.startswith(p) for p in _COMMENT_PREFIXES):
                        total += 1
            except OSError:
                continue
    return total


def _analyze_docstrings(directory: Path) -> tuple[int, int]:
    """Count public symbols and how many have docstrings. Returns (total, documented)."""
    if not directory.exists():
        return 0, 0
    total = 0
    documented = 0
    for path in directory.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_"):
                    continue
                total += 1
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    documented += 1
    return total, documented
