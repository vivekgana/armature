"""Pre-development harness: environment validation, spec readiness, baseline capture."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from armature._internal.output import console, print_check, print_header
from armature.config.loader import load_config_or_defaults


def run_pre_dev(*, spec_id: str | None = None, env_check_only: bool = False) -> None:
    """Run pre-development checks."""
    config = load_config_or_defaults()
    root = Path.cwd()

    print_header("Pre-Development Check")

    # Environment checks
    checks = _check_environment(config)
    console.print("\n  Environment:")
    all_ok = True
    for c in checks:
        print_check(c["name"], c["ok"], c["value"])
        if not c["ok"]:
            console.print(f"      FIX: {c['fix']}")
            all_ok = False

    if env_check_only:
        if not all_ok:
            raise SystemExit(1)
        return

    if spec_id is None:
        console.print("\n  Specify a spec ID for full pre-dev checks:")
        console.print("  armature pre-dev SPEC-2026-Q2-001")
        return

    # Baseline capture
    console.print(f"\n  Spec: {spec_id}")
    from armature.gc.baseline import BaselineManager
    from armature.quality.scorer import capture_baseline_snapshot

    snapshot = capture_baseline_snapshot(config.quality, root)
    manager = BaselineManager(root / ".armature" / "baselines")
    path = manager.save(spec_id, snapshot)

    console.print("\n  Baseline Snapshot:")
    console.print(f"    lint_violations: {snapshot.lint_violations}")
    console.print(f"    type_errors:     {snapshot.type_errors}")
    console.print(f"    test_passed:     {snapshot.test_passed}")
    console.print(f"    test_failed:     {snapshot.test_failed}")
    console.print(f"\n    Saved to: {path.relative_to(root)}")

    status = "[green]READY[/green]" if all_ok else "[red]BLOCKED[/red]"
    console.print(f"\n  RESULT: {status}")

    if not all_ok:
        raise SystemExit(1)


def _check_environment(config: object) -> list[dict]:
    """Validate development environment tools are available."""
    checks = []

    # Python version
    py_version = sys.version.split()[0]
    py_ok = sys.version_info >= (3, 11)
    checks.append({"name": "Python version", "value": py_version, "ok": py_ok,
                    "fix": "Requires Python >= 3.11"})

    # Check configured tools
    for tool_name in ["ruff", "mypy", "pytest"]:
        tool_path = shutil.which(tool_name)
        checks.append({"name": f"{tool_name} available", "value": tool_path or "not found",
                        "ok": bool(tool_path), "fix": f"pip install {tool_name}"})

    return checks
