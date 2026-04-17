"""armature baseline -- capture or compare quality baselines."""

from __future__ import annotations

from pathlib import Path

import click

from armature._internal.output import console, print_check, print_header
from armature.config.loader import load_config_or_defaults


@click.command()
@click.option("--capture", "spec_id", help="Capture baseline for spec ID")
@click.option("--compare", "compare_spec", help="Compare current state against baseline for spec ID")
def baseline_cmd(spec_id: str | None, compare_spec: str | None) -> None:
    """Capture or compare quality baselines."""
    config = load_config_or_defaults()
    root = Path.cwd()

    from armature.gc.baseline import BaselineManager

    manager = BaselineManager(root / ".armature" / "baselines")

    if spec_id:
        print_header(f"Capturing Baseline: {spec_id}")
        from armature.quality.scorer import capture_baseline_snapshot
        snapshot = capture_baseline_snapshot(config.quality, root)
        path = manager.save(spec_id, snapshot)
        console.print(f"[green]Saved:[/green] {path}")
        console.print(f"  lint_violations: {snapshot.lint_violations}")
        console.print(f"  type_errors: {snapshot.type_errors}")
        console.print(f"  test_passed: {snapshot.test_passed}")
        console.print(f"  test_failed: {snapshot.test_failed}")

    elif compare_spec:
        print_header(f"Comparing Against Baseline: {compare_spec}")
        baseline = manager.load(compare_spec)
        if baseline is None:
            console.print(f"[red]No baseline found for {compare_spec}[/red]")
            raise SystemExit(1)

        from armature.quality.scorer import capture_baseline_snapshot
        current = capture_baseline_snapshot(config.quality, root)
        diff = manager.diff(baseline, current)

        print_check("Lint", diff["lint_delta"] <= 0, f"{baseline.lint_violations} -> {current.lint_violations}")
        print_check("Type", diff["type_delta"] <= 0, f"{baseline.type_errors} -> {current.type_errors}")
        print_check("Tests", diff["test_fail_delta"] <= 0,
                     f"{baseline.test_passed}/{baseline.test_failed} -> {current.test_passed}/{current.test_failed}")

        if diff["has_regression"]:
            console.print("\n[red]REGRESSION DETECTED[/red]")
            raise SystemExit(1)
        else:
            console.print("\n[green]No regressions.[/green]")
    else:
        console.print("Usage:")
        console.print("  armature baseline --capture SPEC-ID")
        console.print("  armature baseline --compare SPEC-ID")
