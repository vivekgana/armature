"""Armature CLI entry point.

Usage:
    armature init          Scaffold armature.yaml for a new project
    armature check         Run all enabled sensors
    armature heal          Self-healing pipeline
    armature gc            Garbage collection sweep
    armature budget        Cost tracking and reporting
    armature baseline      Capture or compare quality baselines
    armature report        Generate full harness report
    armature hooks         Generate IDE/agent hook configs
    armature pre-dev       Pre-development checks
    armature post-dev      Post-development checks
    armature version       Show version info
"""

from __future__ import annotations

import click

from armature import __version__


@click.group()
@click.version_option(__version__, prog_name="armature")
def cli() -> None:
    """Armature -- Harness engineering framework for AI coding agents.

    The invisible skeleton that gives shape to what agents produce.
    """


# --- Import and register commands ---

from armature.cli.init_cmd import init_cmd  # noqa: E402
from armature.cli.check_cmd import check_cmd  # noqa: E402
from armature.cli.heal_cmd import heal_cmd  # noqa: E402
from armature.cli.gc_cmd import gc_cmd  # noqa: E402
from armature.cli.budget_cmd import budget_cmd  # noqa: E402
from armature.cli.baseline_cmd import baseline_cmd  # noqa: E402
from armature.cli.report_cmd import report_cmd  # noqa: E402
from armature.cli.hooks_cmd import hooks_cmd  # noqa: E402
from armature.cli.compat_cmd import compat_cmd  # noqa: E402
from armature.cli.spec_cmd import spec_cmd  # noqa: E402

cli.add_command(init_cmd, "init")
cli.add_command(check_cmd, "check")
cli.add_command(heal_cmd, "heal")
cli.add_command(gc_cmd, "gc")
cli.add_command(budget_cmd, "budget")
cli.add_command(baseline_cmd, "baseline")
cli.add_command(report_cmd, "report")
cli.add_command(hooks_cmd, "hooks")
cli.add_command(compat_cmd, "compat")
cli.add_command(spec_cmd, "spec")


@cli.command("pre-dev")
@click.option("--env-check-only", is_flag=True, help="Only check environment, skip spec validation")
@click.argument("spec_id", required=False)
def pre_dev_cmd(env_check_only: bool, spec_id: str | None) -> None:
    """Pre-development checks: env, spec readiness, baseline capture."""
    from armature.harness.pre_dev import run_pre_dev
    run_pre_dev(spec_id=spec_id, env_check_only=env_check_only)


@cli.command("post-dev")
@click.argument("spec_id")
def post_dev_cmd(spec_id: str) -> None:
    """Post-development checks: regression detection, compliance."""
    from armature.harness.post_dev import run_post_dev
    run_post_dev(spec_id=spec_id)


if __name__ == "__main__":
    cli()
