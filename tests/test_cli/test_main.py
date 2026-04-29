"""Tests for cli/main.py -- CLI entry point and command registration."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from armature.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestCLI:
    """Tests for the main CLI group."""

    def test_version(self, runner: CliRunner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "armature" in result.output.lower()

    def test_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "check" in result.output
        assert "heal" in result.output
        assert "gc" in result.output
        assert "budget" in result.output

    def test_check_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["check", "--help"])
        assert result.exit_code == 0
        assert "sensors" in result.output.lower() or "quality" in result.output.lower()

    def test_heal_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["heal", "--help"])
        assert result.exit_code == 0

    def test_gc_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["gc", "--help"])
        assert result.exit_code == 0

    def test_budget_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["budget", "--help"])
        assert result.exit_code == 0

    def test_init_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0

    def test_hooks_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["hooks", "--help"])
        assert result.exit_code == 0

    def test_baseline_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["baseline", "--help"])
        assert result.exit_code == 0

    def test_report_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["report", "--help"])
        assert result.exit_code == 0

    def test_pre_dev_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["pre-dev", "--help"])
        assert result.exit_code == 0

    def test_post_dev_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["post-dev", "--help"])
        assert result.exit_code == 0

    def test_plugin_command_registered(self, runner: CliRunner):
        result = runner.invoke(cli, ["plugin", "--help"])
        assert result.exit_code == 0

    def test_plugin_list_subcommand(self, runner: CliRunner):
        result = runner.invoke(cli, ["plugin", "list", "--help"])
        assert result.exit_code == 0
