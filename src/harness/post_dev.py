"""Post-development harness: regression detection and compliance check."""

from __future__ import annotations

from pathlib import Path

from armature._internal.output import console, print_check, print_header
from armature.config.loader import load_config_or_defaults


def run_post_dev(*, spec_id: str) -> None:
    """Run post-development regression checks."""
    config = load_config_or_defaults()
    root = Path.cwd()

    print_header(f"Post-Development Check: {spec_id}")

    # Load baseline
    from armature.gc.baseline import BaselineManager
    manager = BaselineManager(root / ".armature" / "baselines")
    baseline = manager.load(spec_id)

    if baseline is None:
        console.print(f"  [yellow]No baseline found for {spec_id}[/yellow]")
        console.print(f"  Run: armature pre-dev {spec_id}")
        raise SystemExit(1)

    # Capture current state
    from armature.quality.scorer import capture_baseline_snapshot
    current = capture_baseline_snapshot(config.quality, root)

    # Compare
    diff = manager.diff(baseline, current)

    console.print("\n  Regression:")
    print_check("Lint violations",
                diff["lint_delta"] <= 0,
                f"{baseline.lint_violations} -> {current.lint_violations}")
    print_check("Type errors",
                diff["type_delta"] <= 0,
                f"{baseline.type_errors} -> {current.type_errors}")
    print_check("Test failures",
                diff["test_fail_delta"] <= 0,
                f"{baseline.test_failed} -> {current.test_failed}")

    # Architecture checks
    if config.architecture.enabled:
        from armature.architecture.boundary import run_boundary_check
        from armature.architecture.conformance import run_conformance_check
        boundary = run_boundary_check(config.architecture, root)
        conform = run_conformance_check(config.architecture, root)
        print_check("Layer boundaries", boundary.passed, boundary.details)
        print_check("Conformance", conform.passed, conform.details)

    # Verdict
    if diff["has_regression"]:
        console.print(f"\n  [red]RESULT: REGRESSION DETECTED[/red]")
        console.print("  Fix regressions before proceeding to human review.")
        raise SystemExit(1)
    else:
        console.print(f"\n  [green]RESULT: PASS -- proceed to human review[/green]")
