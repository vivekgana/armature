"""Tests for the 5 new quality checks: complexity, security, test_ratio, docstring, dependency_audit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from armature._internal.subprocess_utils import RunResult
from armature._internal.types import CheckResult
from armature.config.schema import InternalCheckConfig, ToolCheckConfig
from armature.quality.scorer import (
    _analyze_docstrings,
    _check_complexity,
    _check_dependency_audit,
    _check_docstring,
    _check_security,
    _check_test_ratio,
    _count_source_lines,
)


class TestComplexityCheck:
    def test_passes_when_all_below_threshold(self):
        cfg = InternalCheckConfig(weight=15, threshold=10.0)
        radon_output = '{"app/main.py": [{"name": "foo", "complexity": 5}]}'
        with patch("armature.quality.scorer.run_tool", return_value=RunResult(0, radon_output, "")):
            result = _check_complexity(cfg, Path("/project"), "src/")
        assert result is not None
        assert result.passed is True
        assert result.violation_count == 0
        assert result.score == 1.0
        assert result.weight == 15

    def test_score_decreases_per_violation(self):
        cfg = InternalCheckConfig(weight=15, threshold=5.0)
        radon_output = '{"a.py": [{"name": "f1", "complexity": 8}, {"name": "f2", "complexity": 12}]}'
        with patch("armature.quality.scorer.run_tool", return_value=RunResult(0, radon_output, "")):
            result = _check_complexity(cfg, Path("/project"), "src/")
        assert result is not None
        assert result.violation_count == 2
        assert result.score == pytest.approx(0.8)

    def test_score_floors_at_zero(self):
        cfg = InternalCheckConfig(weight=15, threshold=1.0)
        funcs = [{"name": f"f{i}", "complexity": 20} for i in range(15)]
        radon_output = f'{{"a.py": {__import__("json").dumps(funcs)}}}'
        with patch("armature.quality.scorer.run_tool", return_value=RunResult(0, radon_output, "")):
            result = _check_complexity(cfg, Path("/project"), "src/")
        assert result is not None
        assert result.score == 0.0

    def test_tool_not_installed_returns_none(self):
        cfg = InternalCheckConfig(weight=15, threshold=10.0)
        with patch("armature.quality.scorer.run_tool", return_value=RunResult(-1, "", "Command not found")):
            result = _check_complexity(cfg, Path("/project"), "src/")
        assert result is None


class TestSecurityCheck:
    def test_clean_project(self):
        cfg = ToolCheckConfig(tool="bandit", args=["-r", "-f", "json", "-q"], weight=20)
        with patch("armature.quality.scorer.run_tool", return_value=RunResult(0, '{"results": []}', "")):
            result = _check_security(cfg, Path("/project"), "src/")
        assert result is not None
        assert result.passed is True
        assert result.score == 1.0

    def test_scores_findings(self):
        findings = [
            {"issue_severity": "HIGH", "issue_confidence": "HIGH"},
            {"issue_severity": "MEDIUM", "issue_confidence": "HIGH"},
            {"issue_severity": "LOW", "issue_confidence": "HIGH"},
        ]
        output = f'{{"results": {__import__("json").dumps(findings)}}}'
        cfg = ToolCheckConfig(tool="bandit", args=["-r", "-f", "json", "-q"], weight=20)
        with patch("armature.quality.scorer.run_tool", return_value=RunResult(1, output, "")):
            result = _check_security(cfg, Path("/project"), "src/")
        assert result is not None
        assert result.violation_count == 2  # HIGH + MEDIUM only
        assert result.score == pytest.approx(0.7)

    def test_tool_not_installed_returns_none(self):
        cfg = ToolCheckConfig(tool="bandit", args=[], weight=20)
        with patch("armature.quality.scorer.run_tool", return_value=RunResult(-1, "", "not found")):
            result = _check_security(cfg, Path("/project"), "src/")
        assert result is None


class TestTestRatioCheck:
    def test_above_threshold_scores_1(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    return 1\n")
        test = tmp_path / "tests"
        test.mkdir()
        (test / "test_app.py").write_text("def test_main():\n    assert main() == 1\n")

        cfg = InternalCheckConfig(weight=10, threshold=0.5)
        result = _check_test_ratio(cfg, tmp_path, "src", "tests")
        assert result is not None
        assert result.passed is True
        assert result.score == 1.0

    def test_below_threshold_proportional_score(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("line1\nline2\nline3\nline4\n")
        test = tmp_path / "tests"
        test.mkdir()
        (test / "test_app.py").write_text("test1\n")

        cfg = InternalCheckConfig(weight=10, threshold=0.5)
        result = _check_test_ratio(cfg, tmp_path, "src", "tests")
        assert result is not None
        assert result.passed is False
        assert result.score == pytest.approx(0.5)  # 1/4 lines, ratio=0.25, threshold=0.5

    def test_empty_src_dir(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        test = tmp_path / "tests"
        test.mkdir()

        cfg = InternalCheckConfig(weight=10, threshold=0.5)
        result = _check_test_ratio(cfg, tmp_path, "src", "tests")
        assert result is not None
        assert result.score == 0.0


class TestDocstringCheck:
    def test_all_documented(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.py").write_text(
            'def hello():\n    """Says hello."""\n    pass\n\n'
            'class Foo:\n    """A foo."""\n    pass\n'
        )
        cfg = InternalCheckConfig(weight=10)
        result = _check_docstring(cfg, tmp_path, "src")
        assert result is not None
        assert result.score == 1.0
        assert result.violation_count == 0

    def test_partial_coverage(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.py").write_text(
            'def documented():\n    """Has doc."""\n    pass\n\n'
            'def undocumented():\n    pass\n'
        )
        cfg = InternalCheckConfig(weight=10)
        result = _check_docstring(cfg, tmp_path, "src")
        assert result is not None
        assert result.violation_count == 1
        assert result.score == pytest.approx(0.5)

    def test_private_excluded(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.py").write_text(
            'def _private():\n    pass\n\n'
            'def public():\n    """Doc."""\n    pass\n'
        )
        cfg = InternalCheckConfig(weight=10)
        result = _check_docstring(cfg, tmp_path, "src")
        assert result is not None
        assert result.score == 1.0

    def test_empty_src_dir(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        cfg = InternalCheckConfig(weight=10)
        result = _check_docstring(cfg, tmp_path, "src")
        assert result is not None
        assert result.score == 1.0


class TestDependencyAuditCheck:
    def test_zero_vulns(self):
        cfg = ToolCheckConfig(tool="pip-audit", args=["--format", "json"], weight=15)
        with patch("armature.quality.scorer.run_tool", return_value=RunResult(0, "[]", "")):
            result = _check_dependency_audit(cfg, Path("/project"))
        assert result is not None
        assert result.passed is True
        assert result.score == 1.0

    def test_with_vulns(self):
        output = '[{"name": "pkg", "version": "1.0", "vulns": [{"id": "CVE-1"}, {"id": "CVE-2"}]}]'
        cfg = ToolCheckConfig(tool="pip-audit", args=["--format", "json"], weight=15)
        with patch("armature.quality.scorer.run_tool", return_value=RunResult(1, output, "")):
            result = _check_dependency_audit(cfg, Path("/project"))
        assert result is not None
        assert result.violation_count == 2
        assert result.score == pytest.approx(0.6)

    def test_tool_not_installed_returns_none(self):
        cfg = ToolCheckConfig(tool="pip-audit", args=[], weight=15)
        with patch("armature.quality.scorer.run_tool", return_value=RunResult(-1, "", "not found")):
            result = _check_dependency_audit(cfg, Path("/project"))
        assert result is None


class TestWeightedScoring:
    def test_weighted_mean_differs_from_simple_mean(self):
        results = [
            CheckResult(name="lint", passed=True, score=1.0, weight=25),
            CheckResult(name="docstring", passed=False, score=0.5, weight=10),
        ]
        simple = sum(r.score for r in results) / len(results)
        total_w = sum(r.weight for r in results)
        weighted = sum(r.score * r.weight for r in results) / total_w
        assert simple == pytest.approx(0.75)
        assert weighted == pytest.approx((25 + 5) / 35)
        assert simple != weighted

    def test_equal_weights_matches_simple_mean(self):
        results = [
            CheckResult(name="a", passed=True, score=0.8, weight=10),
            CheckResult(name="b", passed=True, score=0.6, weight=10),
        ]
        total_w = sum(r.weight for r in results)
        weighted = sum(r.score * r.weight for r in results) / total_w
        simple = sum(r.score for r in results) / len(results)
        assert weighted == pytest.approx(simple)


class TestHelperFunctions:
    def test_count_source_lines(self, tmp_path):
        d = tmp_path / "src"
        d.mkdir()
        (d / "app.py").write_text("# comment\nimport os\n\ndef main():\n    pass\n")
        count = _count_source_lines(d)
        assert count == 3  # import os, def main():, pass

    def test_count_source_lines_nonexistent(self, tmp_path):
        assert _count_source_lines(tmp_path / "nope") == 0

    def test_analyze_docstrings_basic(self, tmp_path):
        d = tmp_path / "src"
        d.mkdir()
        (d / "mod.py").write_text(
            'def pub():\n    """Doc."""\n    pass\n\n'
            'def pub2():\n    pass\n\n'
            'def _priv():\n    pass\n'
        )
        total, documented = _analyze_docstrings(d)
        assert total == 2
        assert documented == 1
