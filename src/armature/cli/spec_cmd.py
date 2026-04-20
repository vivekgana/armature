"""CLI commands for spec loading and comparison."""

from __future__ import annotations

import json
from pathlib import Path

import click


@click.group("spec")
def spec_cmd() -> None:
    """Spec management and comparison commands."""


@spec_cmd.command("load")
@click.argument("spec_file", type=click.Path(exists=True, path_type=Path))
def load_cmd(spec_file: Path) -> None:
    """Load and display a spec file's structured content."""
    from armature.spec.loader import load_spec

    record = load_spec(spec_file)
    output = {
        "spec_id": record.spec_id,
        "title": record.title,
        "type": record.spec_type,
        "priority": record.priority,
        "acceptance_criteria": [
            {"id": ac.id, "description": ac.description, "testable": ac.testable}
            for ac in record.acceptance_criteria
        ],
        "eval": {
            "unit_test_coverage_min": record.eval_requirements.unit_test_coverage_min,
            "integration_test_required": record.eval_requirements.integration_test_required,
            "e2e_test_required": record.eval_requirements.e2e_test_required,
            "linting_must_pass": record.eval_requirements.linting_must_pass,
            "type_check_must_pass": record.eval_requirements.type_check_must_pass,
        },
        "human_gates": record.human_gates,
        "scope_modules": record.scope_modules,
        "depends_on": record.depends_on,
        "blocks": record.blocks,
    }
    click.echo(json.dumps(output, indent=2))


@spec_cmd.command("compare")
@click.option("--armature", "armature_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--ossature", "ossature_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--pairing", default="", help="Label for this pairing")
def compare_cmd(armature_path: Path, ossature_path: Path, as_json: bool, pairing: str) -> None:
    """Compare armature spec requirements against an ossature project."""
    from armature.spec.compare import (
        compare_projects,
        format_spec_comparison_report,
        spec_comparison_report_to_dict,
    )

    report = compare_projects(armature_path, ossature_path, pairing_rationale=pairing)

    if as_json:
        click.echo(json.dumps(spec_comparison_report_to_dict(report), indent=2))
    else:
        click.echo(format_spec_comparison_report(report))


@spec_cmd.command("compare-all")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--examples-dir", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--fixtures-dir", type=click.Path(exists=True, path_type=Path), default=None)
def compare_all_cmd(as_json: bool, examples_dir: Path | None, fixtures_dir: Path | None) -> None:
    """Compare all three armature examples against ossature fixtures."""
    from armature.spec.compare import (
        compare_all_projects,
        format_all_comparisons,
        spec_comparison_report_to_dict,
    )

    if examples_dir is None:
        pkg_root = Path(__file__).resolve().parent.parent.parent.parent
        examples_dir = pkg_root / "examples"
    if fixtures_dir is None:
        pkg_root = Path(__file__).resolve().parent.parent.parent.parent
        fixtures_dir = pkg_root / "tests" / "test_e2e" / "fixtures"

    if not examples_dir.exists():
        click.echo(f"Error: examples directory not found: {examples_dir}", err=True)
        raise SystemExit(1)
    if not fixtures_dir.exists():
        click.echo(f"Error: fixtures directory not found: {fixtures_dir}", err=True)
        raise SystemExit(1)

    reports = compare_all_projects(examples_dir, fixtures_dir)

    if as_json:
        click.echo(json.dumps([spec_comparison_report_to_dict(r) for r in reports], indent=2))
    else:
        click.echo(format_all_comparisons(reports))
