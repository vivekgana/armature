"""E2E tests for spec loader and armature-vs-ossature comparison."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from armature.cli.main import cli
from armature.spec.loader import load_all_specs, load_project_specs, load_spec
from armature.spec.compare import (
    build_armature_summary,
    build_ossature_summary,
    compare_all_projects,
    compare_projects,
    format_all_comparisons,
    format_spec_comparison_report,
    spec_comparison_report_to_dict,
)


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


class TestSpecLoader:
    """Verify the spec loader produces correct structured data."""

    def test_load_single_spec_python_fastapi(self, python_fastapi_project: Path) -> None:
        spec = load_spec(python_fastapi_project / "specs" / "SPEC-2026-Q2-001.yaml")
        assert spec.spec_id == "SPEC-2026-Q2-001"
        assert spec.title == "Add user authentication endpoint"
        assert spec.spec_type == "feature"
        assert len(spec.acceptance_criteria) == 5
        assert spec.eval_requirements.unit_test_coverage_min == 90
        assert spec.eval_requirements.integration_test_required is True
        assert spec.eval_requirements.e2e_test_required is False
        assert len(spec.human_gates) == 3

    def test_load_spec_eval_defaults_on_spike(self, monorepo_project: Path) -> None:
        spec = load_spec(monorepo_project / "specs" / "SPEC-2026-Q2-002.yaml")
        assert spec.spec_type == "spike"
        assert spec.eval_requirements.unit_test_coverage_min == 0
        assert spec.eval_requirements.type_check_must_pass is False
        assert spec.eval_requirements.integration_test_required is False

    def test_load_all_specs_skips_templates(self, python_fastapi_project: Path) -> None:
        specs = load_all_specs(python_fastapi_project / "specs")
        assert len(specs) == 2
        ids = [s.spec_id for s in specs]
        assert "SPEC-2026-Q2-001" in ids
        assert "SPEC-2026-Q2-002" in ids

    def test_load_project_specs_returns_config_and_specs(self, python_fastapi_project: Path) -> None:
        config, specs = load_project_specs(python_fastapi_project)
        assert config.project.language == "python"
        assert len(specs) == 2

    def test_load_spec_typescript_nextjs(self, typescript_nextjs_project: Path) -> None:
        spec = load_spec(typescript_nextjs_project / "specs" / "SPEC-2026-Q2-001.yaml")
        assert spec.eval_requirements.e2e_test_required is True
        spec2 = load_spec(typescript_nextjs_project / "specs" / "SPEC-2026-Q2-002.yaml")
        assert spec2.eval_requirements.e2e_test_required is False

    def test_load_spec_missing_eval_uses_defaults(self, tmp_path: Path) -> None:
        spec_file = tmp_path / "minimal.yaml"
        spec_file.write_text(
            "spec_id: TEST-001\ntitle: Minimal\ntype: feature\npriority: low\n",
            encoding="utf-8",
        )
        spec = load_spec(spec_file)
        assert spec.eval_requirements.unit_test_coverage_min == 0
        assert spec.eval_requirements.integration_test_required is False
        assert spec.eval_requirements.e2e_test_required is False


class TestArmatureSummaryBuilder:
    """Verify build_armature_summary aggregates correctly."""

    def test_python_fastapi_summary(self, python_fastapi_project: Path) -> None:
        config, specs = load_project_specs(python_fastapi_project)
        summary = build_armature_summary(config, specs)
        assert summary.spec_count == 2
        assert summary.total_ac_count == 8  # 5 + 3
        assert summary.max_coverage_min == 90
        assert summary.min_coverage_min == 85
        assert summary.human_gate_count == 3
        assert summary.integration_test_required_count == 2

    def test_monorepo_summary_has_spike(self, monorepo_project: Path) -> None:
        config, specs = load_project_specs(monorepo_project)
        summary = build_armature_summary(config, specs)
        assert summary.spec_types.get("spike", 0) == 1
        assert summary.spec_types.get("feature", 0) == 1

    def test_typescript_nextjs_has_e2e_requirement(self, typescript_nextjs_project: Path) -> None:
        config, specs = load_project_specs(typescript_nextjs_project)
        summary = build_armature_summary(config, specs)
        assert summary.e2e_test_required_count == 1

    def test_summary_quality_tools_from_config(self, python_fastapi_project: Path) -> None:
        config, specs = load_project_specs(python_fastapi_project)
        summary = build_armature_summary(config, specs)
        assert "ruff" in summary.quality_tools
        assert "mypy" in summary.quality_tools
        assert "pytest" in summary.quality_tools


class TestOssatureSummaryBuilder:
    """Verify build_ossature_summary reshapes ComparisonReport correctly."""

    def test_spenny_summary(self, spenny_project: Path) -> None:
        from armature.compat._ossature_model import load_ossature_project
        from armature.compat.compare import compare_ossature_project

        report = compare_ossature_project(spenny_project)
        ossature = load_ossature_project(spenny_project)
        summary = build_ossature_summary(report, ossature)
        assert summary.project_name == "Spenny"
        assert summary.project_language == "python"
        assert summary.budget_tier == "medium"
        assert summary.has_output_dir is True
        assert summary.has_architecture_specs is True
        assert summary.architecture_component_count == 3

    def test_markman_summary_no_output_dir(self, markman_project: Path) -> None:
        from armature.compat._ossature_model import load_ossature_project
        from armature.compat.compare import compare_ossature_project

        report = compare_ossature_project(markman_project)
        ossature = load_ossature_project(markman_project)
        summary = build_ossature_summary(report, ossature)
        assert summary.has_output_dir is False
        assert summary.quality_score == 0.0

    def test_math_quest_unsupported_language(self, math_quest_project: Path) -> None:
        from armature.compat._ossature_model import load_ossature_project
        from armature.compat.compare import compare_ossature_project

        report = compare_ossature_project(math_quest_project)
        ossature = load_ossature_project(math_quest_project)
        summary = build_ossature_summary(report, ossature)
        assert summary.unsupported_language is True
        assert summary.project_language == "lua"


class TestComparePairing:
    """Integration: compare_projects() produces correct SpecComparisonReport."""

    def test_python_fastapi_vs_spenny(self, python_fastapi_project: Path, spenny_project: Path) -> None:
        report = compare_projects(
            python_fastapi_project, spenny_project, pairing_rationale="Both Python"
        )
        assert report.armature_project == "my-fastapi-app"
        assert report.ossature_project == "Spenny"
        assert len(report.dimensions) >= 10
        assert isinstance(report.overall_gap_count, int)
        assert isinstance(report.overall_meets_count, int)

    def test_typescript_nextjs_vs_math_quest(
        self, typescript_nextjs_project: Path, math_quest_project: Path
    ) -> None:
        report = compare_projects(
            typescript_nextjs_project, math_quest_project,
            pairing_rationale="Both alternative language stacks",
        )
        language_dim = next(d for d in report.dimensions if d.dimension == "Language compatibility")
        assert language_dim.gap == "GAP"

    def test_monorepo_vs_markman(self, monorepo_project: Path, markman_project: Path) -> None:
        report = compare_projects(
            monorepo_project, markman_project, pairing_rationale="Both multi-service"
        )
        coverage_dim = next(
            d for d in report.dimensions if "coverage" in d.dimension.lower()
        )
        assert coverage_dim.gap == "UNKNOWN"

    def test_report_is_json_serializable(
        self, python_fastapi_project: Path, spenny_project: Path
    ) -> None:
        report = compare_projects(python_fastapi_project, spenny_project)
        d = spec_comparison_report_to_dict(report)
        json_str = json.dumps(d)
        assert json_str
        parsed = json.loads(json_str)
        assert "armature_project" in parsed
        assert "dimensions" in parsed

    def test_budget_tier_dimension(
        self, python_fastapi_project: Path, spenny_project: Path
    ) -> None:
        report = compare_projects(python_fastapi_project, spenny_project)
        budget_dim = next(d for d in report.dimensions if "budget tier" in d.dimension.lower())
        assert budget_dim.gap == "MEETS"


class TestCompareAllProjects:
    """Integration: compare_all_projects() produces all three pairings."""

    def test_compare_all_returns_three_reports(
        self, examples_dir: Path, ossature_fixtures_dir: Path
    ) -> None:
        reports = compare_all_projects(examples_dir, ossature_fixtures_dir)
        assert len(reports) == 3

    def test_compare_all_project_names(
        self, examples_dir: Path, ossature_fixtures_dir: Path
    ) -> None:
        reports = compare_all_projects(examples_dir, ossature_fixtures_dir)
        armature_names = {r.armature_project for r in reports}
        ossature_names = {r.ossature_project for r in reports}
        assert "my-fastapi-app" in armature_names
        assert "Spenny" in ossature_names


class TestReportFormatting:
    """Verify text and JSON formatting of comparison reports."""

    def test_format_report_contains_dimension_rows(
        self, python_fastapi_project: Path, spenny_project: Path
    ) -> None:
        report = compare_projects(python_fastapi_project, spenny_project)
        text = format_spec_comparison_report(report)
        assert "Armature" in text
        assert "Ossature" in text
        assert "coverage" in text.lower()
        assert "budget" in text.lower()

    def test_format_all_has_summary(
        self, examples_dir: Path, ossature_fixtures_dir: Path
    ) -> None:
        reports = compare_all_projects(examples_dir, ossature_fixtures_dir)
        text = format_all_comparisons(reports)
        assert "my-fastapi-app" in text or "python-fastapi" in text.lower()
        assert "Spenny" in text or "spenny" in text.lower()


class TestSpecCompareCLI:
    """CLI integration tests for armature spec commands."""

    def test_compare_exits_zero(
        self, runner: CliRunner, python_fastapi_project: Path, spenny_project: Path
    ) -> None:
        result = runner.invoke(cli, [
            "spec", "compare",
            "--armature", str(python_fastapi_project),
            "--ossature", str(spenny_project),
        ])
        assert result.exit_code == 0

    def test_compare_json_output(
        self, runner: CliRunner, python_fastapi_project: Path, spenny_project: Path
    ) -> None:
        result = runner.invoke(cli, [
            "spec", "compare",
            "--armature", str(python_fastapi_project),
            "--ossature", str(spenny_project),
            "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "armature_project" in data
        assert "dimensions" in data
        assert isinstance(data["dimensions"], list)

    def test_load_spec_command(
        self, runner: CliRunner, python_fastapi_project: Path
    ) -> None:
        spec_path = python_fastapi_project / "specs" / "SPEC-2026-Q2-001.yaml"
        result = runner.invoke(cli, ["spec", "load", str(spec_path)])
        assert result.exit_code == 0
        assert "SPEC-2026-Q2-001" in result.output

    def test_compare_missing_path_fails(
        self, runner: CliRunner, spenny_project: Path
    ) -> None:
        result = runner.invoke(cli, [
            "spec", "compare",
            "--armature", "/nonexistent/path",
            "--ossature", str(spenny_project),
        ])
        assert result.exit_code != 0
