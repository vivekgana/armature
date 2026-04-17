"""armature check -- run all enabled quality sensors."""

from __future__ import annotations

from pathlib import Path

import click

from armature._internal.output import console, print_check, print_header
from armature._internal.types import CheckResult
from armature.config.loader import load_config_or_defaults


@click.command()
@click.option("--file", "file_path", help="Check a single file instead of the whole project")
@click.option("--json", "use_json", is_flag=True, help="Output results as JSON")
def check_cmd(file_path: str | None, use_json: bool) -> None:
    """Run all enabled sensors (lint, type, architecture, conformance)."""
    config = load_config_or_defaults()
    root = Path.cwd()
    results: list[CheckResult] = []

    if not use_json:
        print_header("Armature Check")

    # Quality checks
    if config.quality.enabled:
        from armature.quality.scorer import run_quality_checks
        quality_results = run_quality_checks(config.quality, root, file_path=file_path)
        results.extend(quality_results)

    # Architecture checks (skip for single-file mode)
    if config.architecture.enabled and file_path is None:
        from armature.architecture.boundary import run_boundary_check
        from armature.architecture.conformance import run_conformance_check
        results.append(run_boundary_check(config.architecture, root))
        results.append(run_conformance_check(config.architecture, root))

    if use_json:
        import json
        output = [{"name": r.name, "passed": r.passed, "violations": r.violation_count, "details": r.details}
                  for r in results]
        click.echo(json.dumps(output, indent=2))
    else:
        for r in results:
            print_check(r.name, r.passed, r.details)

        # Quality score
        total_weight = sum(r.score for r in results)
        score = total_weight / len(results) if results else 1.0
        level = "merge_ready" if score >= 0.95 else "review_ready" if score >= 0.85 else "draft"
        console.print(f"\n  [bold]Quality score:[/bold] {score:.2f} ({level})")

    if any(not r.passed for r in results):
        raise SystemExit(1)
