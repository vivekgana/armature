"""CLI integration tests for ossature compatibility commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from armature.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestConvertCLI:
    def test_convert_spenny_to_stdout(self, runner: CliRunner, spenny_project: Path) -> None:
        result = runner.invoke(cli, ["compat", "convert", str(spenny_project)])
        assert result.exit_code == 0
        assert "project:" in result.output
        assert "language: python" in result.output

    def test_convert_writes_to_file(self, runner: CliRunner, spenny_project: Path, tmp_path: Path) -> None:
        out = tmp_path / "armature.yaml"
        result = runner.invoke(cli, ["compat", "convert", str(spenny_project), "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "language: python" in content

    def test_convert_refuses_overwrite_without_force(
        self, runner: CliRunner, spenny_project: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "armature.yaml"
        out.write_text("existing", encoding="utf-8")
        result = runner.invoke(cli, ["compat", "convert", str(spenny_project), "--output", str(out)])
        assert result.exit_code == 1

    def test_convert_force_overwrites(self, runner: CliRunner, spenny_project: Path, tmp_path: Path) -> None:
        out = tmp_path / "armature.yaml"
        out.write_text("existing", encoding="utf-8")
        result = runner.invoke(cli, ["compat", "convert", str(spenny_project), "--output", str(out), "--force"])
        assert result.exit_code == 0
        assert "language: python" in out.read_text(encoding="utf-8")

    def test_convert_lua_shows_warnings(self, runner: CliRunner, math_quest_project: Path) -> None:
        result = runner.invoke(cli, ["compat", "convert", str(math_quest_project)])
        assert result.exit_code == 0
        assert "warning" in result.output.lower() or "WARNING" in result.output

    def test_convert_rust_project(self, runner: CliRunner, markman_project: Path) -> None:
        result = runner.invoke(cli, ["compat", "convert", str(markman_project)])
        assert result.exit_code == 0
        assert "language: rust" in result.output


class TestCompareCLI:
    def test_compare_spenny_exits_zero(self, runner: CliRunner, spenny_project: Path) -> None:
        result = runner.invoke(cli, ["compat", "compare", str(spenny_project)])
        assert result.exit_code == 0

    def test_compare_json_output(self, runner: CliRunner, spenny_project: Path) -> None:
        result = runner.invoke(cli, ["compat", "compare", str(spenny_project), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "quality_score" in data
        assert "budget_tier" in data
        assert data["ossature_project_name"] == "Spenny"

    def test_compare_markman_json(self, runner: CliRunner, markman_project: Path) -> None:
        result = runner.invoke(cli, ["compat", "compare", str(markman_project), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["output_dir_exists"] is False
        assert data["budget_tier"] == "low"

    def test_compare_lua_json(self, runner: CliRunner, math_quest_project: Path) -> None:
        result = runner.invoke(cli, ["compat", "compare", str(math_quest_project), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["unsupported_language"] is True


class TestFullLifecycle:
    def test_convert_then_compare(self, runner: CliRunner, spenny_project: Path, tmp_path: Path) -> None:
        out = tmp_path / "armature.yaml"
        result = runner.invoke(cli, ["compat", "convert", str(spenny_project), "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

        result = runner.invoke(cli, ["compat", "compare", str(spenny_project), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data["quality_score"], float)
        assert data["spec_count"] == 1
