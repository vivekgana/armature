"""TypeScript quality plugin -- eslint, tsc, and jest checks for TypeScript projects.

This is the first community-facing built-in plugin. It detects TypeScript projects
(presence of ``tsconfig.json`` or ``package.json`` with typescript dependency) and
runs eslint, tsc (type-checking), and jest (tests) as additional quality checks.

It is registered via the ``armature.plugins`` entry-point in ``pyproject.toml``, so it
is automatically discovered when ``armature-harness`` is installed.

To opt out, remove it from your config::

    # armature.yaml
    plugins:
      disabled: [typescript-quality]
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from armature._internal.types import CheckResult
from armature.plugins import ArmaturePlugin

logger = logging.getLogger(__name__)

# Subset of ALLOWED_TOOLS that cover TypeScript
_TS_TOOLS = frozenset({"eslint", "biome", "tsc", "jest", "vitest"})


class TypeScriptQualityPlugin(ArmaturePlugin):
    """Run TypeScript quality checks (eslint, tsc, jest) when a TS project is detected.

    Checks are only added to the results when the corresponding tool is available on
    ``PATH`` and the project contains TypeScript files, so the plugin is a no-op for
    pure-Python projects.
    """

    name: str = "typescript-quality"
    version: str = "0.1.0"
    description: str = "TypeScript quality checks: eslint (lint), tsc (types), jest (tests)"

    def on_check(
        self,
        file_path: str | None,
        results: list[CheckResult],
    ) -> list[CheckResult]:
        """Append TypeScript check results to the existing results list."""
        root = Path.cwd()

        if not _is_typescript_project(root):
            return results

        ts_results: list[CheckResult] = []

        # eslint
        eslint_result = _run_eslint(root, file_path)
        if eslint_result is not None:
            ts_results.append(eslint_result)

        # tsc (project-wide only)
        if file_path is None:
            tsc_result = _run_tsc(root)
            if tsc_result is not None:
                ts_results.append(tsc_result)

        # jest (project-wide only)
        if file_path is None:
            jest_result = _run_jest(root)
            if jest_result is not None:
                ts_results.append(jest_result)

        return results + ts_results


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def _is_typescript_project(root: Path) -> bool:
    """Return True when the project contains TypeScript configuration or source files."""
    if (root / "tsconfig.json").exists():
        return True
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {
                *data.get("dependencies", {}).keys(),
                *data.get("devDependencies", {}).keys(),
            }
            if "typescript" in deps:
                return True
        except (json.JSONDecodeError, OSError):
            pass
    return any(root.rglob("*.ts")) or any(root.rglob("*.tsx"))


def _tool_available(name: str) -> bool:
    """Return True when *name* is executable on PATH."""
    try:
        subprocess.run(
            [name, "--version"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return True
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# Individual check runners
# ---------------------------------------------------------------------------

def _run_eslint(root: Path, file_path: str | None) -> CheckResult | None:
    """Run eslint and return a CheckResult, or None if eslint is unavailable."""
    if not _tool_available("eslint"):
        return None

    target = file_path or "."
    try:
        proc = subprocess.run(
            ["eslint", "--format", "json", target],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("eslint failed: %s", exc)
        return None

    violation_count = 0
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else []
        for file_result in data:
            violation_count += len(file_result.get("messages", []))
    except (json.JSONDecodeError, TypeError):
        violation_count = max(0, proc.returncode)

    passed = proc.returncode == 0
    score = max(0.0, 1.0 - violation_count * 0.05)
    return CheckResult(
        name="ts_lint",
        passed=passed,
        violation_count=violation_count,
        details=f"eslint: {violation_count} violation(s)" if not passed else "eslint: clean",
        score=score,
        weight=25,
    )


def _run_tsc(root: Path) -> CheckResult | None:
    """Run tsc --noEmit and return a CheckResult, or None if tsc is unavailable."""
    tsc_cmd = "tsc"
    # Prefer local node_modules/.bin/tsc
    local_tsc = root / "node_modules" / ".bin" / "tsc"
    if local_tsc.exists():
        tsc_cmd = str(local_tsc)
    elif not _tool_available("tsc"):
        return None

    try:
        proc = subprocess.run(
            [tsc_cmd, "--noEmit"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("tsc failed: %s", exc)
        return None

    error_count = sum(1 for line in proc.stdout.split("\n") if "error TS" in line)
    passed = proc.returncode == 0
    score = max(0.0, 1.0 - error_count * 0.1)
    return CheckResult(
        name="ts_type_check",
        passed=passed,
        violation_count=error_count,
        details=f"tsc: {error_count} type error(s)" if not passed else "tsc: clean",
        score=score,
        weight=25,
    )


def _run_jest(root: Path) -> CheckResult | None:
    """Run jest and return a CheckResult, or None if jest is unavailable."""
    jest_cmd = "jest"
    local_jest = root / "node_modules" / ".bin" / "jest"
    if local_jest.exists():
        jest_cmd = str(local_jest)
    elif not _tool_available("jest"):
        return None

    try:
        proc = subprocess.run(
            [jest_cmd, "--json", "--passWithNoTests"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("jest failed: %s", exc)
        return None

    passed_count = 0
    failed_count = 0
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
        passed_count = data.get("numPassedTests", 0)
        failed_count = data.get("numFailedTests", 0)
    except (json.JSONDecodeError, TypeError):
        failed_count = 0 if proc.returncode == 0 else 1

    passed = proc.returncode == 0
    score = max(0.0, 1.0 - failed_count * 0.2)
    return CheckResult(
        name="ts_test",
        passed=passed,
        violation_count=failed_count,
        details=f"jest: {passed_count} passed, {failed_count} failed",
        score=score,
        weight=20,
    )
