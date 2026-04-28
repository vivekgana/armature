"""armature plugin -- manage and inspect installed plugins."""

from __future__ import annotations

import click

from armature._internal.output import console, print_header


@click.group("plugin")
def plugin_cmd() -> None:
    """Manage Armature plugins."""


@plugin_cmd.command("list")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
def plugin_list(use_json: bool) -> None:
    """List all installed Armature plugins."""
    from armature.plugins import registry

    registry.load_entry_points()
    plugins = registry.list_plugins()

    if use_json:
        import json
        output = [{"name": p.name, "version": p.version, "description": p.description} for p in plugins]
        click.echo(json.dumps(output, indent=2))
        return

    print_header("Armature Plugins")

    if not plugins:
        console.print("  [yellow]No plugins installed.[/yellow]")
        console.print("\n  Install plugins via pip:")
        console.print('  [dim]pip install armature-plugin-<name>[/dim]')
        console.print("\n  Or build your own: see examples/armature-plugin-example/")
        return

    for plugin in plugins:
        version_str = f" [dim]v{plugin.version}[/dim]" if plugin.version != "0.0.0" else ""
        console.print(f"  [green]●[/green] [bold]{plugin.name}[/bold]{version_str}")
        if plugin.description:
            console.print(f"    {plugin.description}")

    console.print(f"\n  {len(plugins)} plugin(s) loaded.")
