"""CLI commands for ossature compatibility: convert and compare."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from armature._internal.output import console


@click.group("compat")
def compat_cmd() -> None:
    """Ossature compatibility: convert and compare ossature projects."""


@compat_cmd.command("convert")
@click.argument("ossature_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Write armature.yaml to this path (default: stdout)")
@click.option("--force", is_flag=True, help="Overwrite existing armature.yaml")
def convert_cmd(ossature_path: str, output: str | None, force: bool) -> None:
    """Convert an ossature project to armature.yaml."""
    from armature.compat.ossature import conversion_result_to_yaml, convert_ossature_project

    root = Path(ossature_path).resolve()
    result = convert_ossature_project(root)
    yaml_str = conversion_result_to_yaml(result)

    if output:
        out_path = Path(output)
        if out_path.exists() and not force:
            console.print(f"[red]File already exists: {out_path}. Use --force to overwrite.[/red]")
            sys.exit(1)
        out_path.write_text(yaml_str, encoding="utf-8")
        console.print(f"[green]Wrote armature.yaml to {out_path}[/green]")
    else:
        click.echo(yaml_str)

    if result.warnings:
        console.print(f"\n[yellow]{len(result.warnings)} warning(s):[/yellow]")
        for w in result.warnings:
            console.print(f"  [yellow]WARNING[/yellow] [{w.field}]: {w.reason}")


@compat_cmd.command("compare")
@click.argument("ossature_path", type=click.Path(exists=True))
@click.option("--json", "use_json", is_flag=True, help="Output results as JSON")
@click.option("--output-dir", type=click.Path(), help="Override ossature output directory")
def compare_cmd(ossature_path: str, use_json: bool, output_dir: str | None) -> None:
    """Run armature quality checks on an ossature project's generated output."""
    from armature.compat.compare import (
        compare_ossature_project,
        comparison_report_to_dict,
        format_comparison_report,
    )

    root = Path(ossature_path).resolve()
    out = Path(output_dir).resolve() if output_dir else None

    report = compare_ossature_project(root, output_dir=out)

    if use_json:
        click.echo(json.dumps(comparison_report_to_dict(report), indent=2))
    else:
        console.print(format_comparison_report(report))
