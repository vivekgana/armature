"""Tests for ossature-armature comparison engine."""

from __future__ import annotations

from pathlib import Path

from armature.compat.compare import (
    ComparisonReport,
    compare_ossature_project,
    comparison_report_to_dict,
    format_comparison_report,
)


class TestComparisonEngine:
    def test_compare_spenny_runs_without_error(self, spenny_project: Path) -> None:
        report = compare_ossature_project(spenny_project)
        assert isinstance(report, ComparisonReport)
        assert report.ossature_project_name == "Spenny"

    def test_compare_spenny_has_output_dir(self, spenny_project: Path) -> None:
        report = compare_ossature_project(spenny_project)
        assert report.output_dir_exists is True

    def test_compare_spenny_has_specs(self, spenny_project: Path) -> None:
        report = compare_ossature_project(spenny_project)
        assert report.spec_count == 1
        assert "EXPENSE_TRACKER" in report.spec_ids

    def test_compare_spenny_has_architecture(self, spenny_project: Path) -> None:
        report = compare_ossature_project(spenny_project)
        assert report.architecture_enabled is True
        assert report.layer_count == 3

    def test_compare_with_missing_output_dir(self, markman_project: Path) -> None:
        report = compare_ossature_project(markman_project)
        assert report.output_dir_exists is False
        assert report.quality_score == 0.0

    def test_compare_lua_unsupported_language(self, math_quest_project: Path) -> None:
        report = compare_ossature_project(math_quest_project)
        assert report.unsupported_language is True

    def test_compare_budget_tier_inferred(self, spenny_project: Path) -> None:
        report = compare_ossature_project(spenny_project)
        assert report.budget_tier == "medium"
        assert report.budget_estimate_tokens > 0

    def test_compare_markman_haiku_tier(self, markman_project: Path) -> None:
        report = compare_ossature_project(markman_project)
        assert report.budget_tier == "low"

    def test_compare_math_quest_opus_tier(self, math_quest_project: Path) -> None:
        report = compare_ossature_project(math_quest_project)
        assert report.budget_tier == "high"


class TestReportFormatting:
    def test_format_report_text(self, spenny_project: Path) -> None:
        report = compare_ossature_project(spenny_project)
        text = format_comparison_report(report)
        assert "Spenny" in text
        assert "Quality" in text
        assert "Architecture" in text
        assert "Budget" in text

    def test_format_missing_output(self, markman_project: Path) -> None:
        report = compare_ossature_project(markman_project)
        text = format_comparison_report(report)
        assert "NOT FOUND" in text

    def test_report_to_dict(self, spenny_project: Path) -> None:
        report = compare_ossature_project(spenny_project)
        d = comparison_report_to_dict(report)
        assert d["ossature_project_name"] == "Spenny"
        assert "quality_score" in d
        assert "budget_tier" in d
        assert isinstance(d["spec_ids"], list)

    def test_report_dict_json_serializable(self, spenny_project: Path) -> None:
        import json
        report = compare_ossature_project(spenny_project)
        d = comparison_report_to_dict(report)
        json_str = json.dumps(d)
        assert json_str
