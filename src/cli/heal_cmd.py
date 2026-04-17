"""armature heal -- self-healing pipeline."""

from __future__ import annotations

import click

from armature._internal.output import console, print_header
from armature.config.loader import load_config_or_defaults


@click.command()
@click.option("--failures", default="lint,type,test", help="Comma-separated failure types to heal")
@click.option("--spec", "spec_id", default="UNKNOWN", help="Spec ID for failure report")
def heal_cmd(failures: str, spec_id: str) -> None:
    """Self-healing pipeline: auto-fix what's fixable, escalate the rest."""
    config = load_config_or_defaults()

    if not config.heal.enabled:
        console.print("[yellow]Self-healing is disabled in armature.yaml[/yellow]")
        return

    from armature.heal.pipeline import HealPipeline

    print_header("Armature Self-Heal")
    console.print(f"  Max attempts per type: {config.heal.max_attempts}")
    console.print(f"  Failure types: {failures}\n")

    pipeline = HealPipeline(config.heal)
    failure_types = set(failures.split(","))
    results = pipeline.heal(failure_types)

    unfixed = [r for r in results if not r.fixed]
    if unfixed:
        report_path = pipeline.save_failure_report(spec_id, results)
        console.print(f"\n[red]FAILURE REPORT:[/red] {report_path}")
        console.print("  Action: Review the report and fix manually, then re-run.")
        raise SystemExit(1)
    else:
        console.print("\n[green]All failures resolved.[/green]")
