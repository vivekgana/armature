"""armature gc -- garbage collection sweep."""

from __future__ import annotations

import click

from armature._internal.output import console, print_check, print_header
from armature.config.loader import load_config_or_defaults


@click.command()
@click.option("--agent", help="Run only a specific GC agent (architecture, docs, dead_code, budget)")
@click.option("--json", "use_json", is_flag=True, help="Output results as JSON")
def gc_cmd(agent: str | None, use_json: bool) -> None:
    """Run garbage collection agents (architecture drift, docs, dead code, budget)."""
    config = load_config_or_defaults()

    if not config.gc.enabled:
        console.print("[yellow]Garbage collection is disabled in armature.yaml[/yellow]")
        return

    from armature.gc.runner import GCRunner

    runner = GCRunner(config.gc, config)
    findings = runner.run(agent_name=agent)

    if use_json:
        import json
        output = [{"agent": f.agent, "category": f.category, "file": f.file,
                    "message": f.message, "severity": f.severity.value} for f in findings]
        click.echo(json.dumps(output, indent=2))
    else:
        print_header("Armature GC Sweep")
        if not findings:
            console.print("  [green]No issues found.[/green]")
        else:
            for finding in findings:
                print_check(f"[{finding.agent}] {finding.category}", False, finding.message)
            console.print(f"\n  Total findings: {len(findings)}")
