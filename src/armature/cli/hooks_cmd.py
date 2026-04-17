"""armature hooks -- generate IDE/agent hook configuration files."""

from __future__ import annotations

import click

from armature._internal.output import console, print_header
from armature.config.loader import load_config_or_defaults


@click.command()
@click.option("--claude-code", "gen_claude", is_flag=True, help="Generate .claude/settings.local.json")
@click.option("--cursor", "gen_cursor", is_flag=True, help="Generate .cursor/rules")
@click.option("--copilot", "gen_copilot", is_flag=True, help="Generate .github/copilot-instructions.md")
@click.option("--github-actions", "gen_gha", is_flag=True, help="Generate .github/workflows/armature.yml")
@click.option("--pre-commit", "gen_precommit", is_flag=True, help="Generate .pre-commit-config.yaml")
@click.option("--all", "gen_all", is_flag=True, help="Generate all enabled integrations")
def hooks_cmd(gen_claude: bool, gen_cursor: bool, gen_copilot: bool,
              gen_gha: bool, gen_precommit: bool, gen_all: bool) -> None:
    """Generate IDE/agent hook configuration files."""
    config = load_config_or_defaults()
    print_header("Armature Hooks")

    generated = False

    if gen_claude or gen_all and config.integrations.claude_code.enabled:
        from armature.integrations.claude_code import generate_claude_code_hooks
        path = generate_claude_code_hooks(config)
        console.print(f"[green]Generated:[/green] {path}")
        generated = True

    if gen_cursor or gen_all and config.integrations.cursor.enabled:
        from armature.integrations.cursor import generate_cursor_rules
        path = generate_cursor_rules(config)
        console.print(f"[green]Generated:[/green] {path}")
        generated = True

    if gen_copilot or gen_all and config.integrations.copilot.enabled:
        from armature.integrations.copilot import generate_copilot_instructions
        path = generate_copilot_instructions(config)
        console.print(f"[green]Generated:[/green] {path}")
        generated = True

    if gen_gha or gen_all and config.integrations.github_actions.enabled:
        from armature.integrations.github_actions import generate_github_actions
        path = generate_github_actions(config)
        console.print(f"[green]Generated:[/green] {path}")
        generated = True

    if gen_precommit or gen_all and config.integrations.pre_commit.enabled:
        from armature.integrations.pre_commit import generate_pre_commit
        path = generate_pre_commit(config)
        console.print(f"[green]Generated:[/green] {path}")
        generated = True

    if not generated:
        console.print("  No hooks generated. Specify --claude-code, --cursor, --github-actions, etc.")
        console.print("  Or use --all to generate all enabled integrations.")
