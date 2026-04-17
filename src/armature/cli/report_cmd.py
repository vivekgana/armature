"""armature report -- generate full harness report."""

from __future__ import annotations

from pathlib import Path

import click

from armature._internal.output import console, print_header
from armature.config.loader import load_config_or_defaults


@click.command()
@click.option("--spec", "spec_id", help="Spec ID to include in report")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
def report_cmd(spec_id: str | None, use_json: bool) -> None:
    """Generate full harness report (quality score, budget, compliance)."""
    config = load_config_or_defaults()
    root = Path.cwd()

    report: dict = {"sections": []}

    # Quality section
    if config.quality.enabled:
        from armature.quality.scorer import run_quality_checks
        results = run_quality_checks(config.quality, root)
        score = sum(r.score for r in results) / len(results) if results else 1.0
        report["sections"].append({
            "name": "quality",
            "score": round(score, 2),
            "checks": [{"name": r.name, "passed": r.passed, "violations": r.violation_count} for r in results],
        })

    # Architecture section
    if config.architecture.enabled:
        from armature.architecture.boundary import run_boundary_check
        from armature.architecture.conformance import run_conformance_check
        boundary = run_boundary_check(config.architecture, root)
        conform = run_conformance_check(config.architecture, root)
        report["sections"].append({
            "name": "architecture",
            "boundary_violations": boundary.violation_count,
            "conformance_violations": conform.violation_count,
        })

    # Budget section
    if config.budget.enabled and spec_id:
        from armature.budget.tracker import SessionTracker
        tracker = SessionTracker(config.budget)
        usage = tracker.get_usage(spec_id)
        report["sections"].append({"name": "budget", "spec_id": spec_id, **usage})

    if use_json:
        import json
        click.echo(json.dumps(report, indent=2))
    else:
        print_header("Armature Harness Report")
        for section in report["sections"]:
            console.print(f"\n  [bold]{section['name'].upper()}[/bold]")
            for key, value in section.items():
                if key != "name":
                    console.print(f"    {key}: {value}")
