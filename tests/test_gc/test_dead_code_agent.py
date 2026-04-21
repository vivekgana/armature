"""Tests for gc/agents/dead_code.py -- dead code and entropy detection."""

from __future__ import annotations

from pathlib import Path

from armature.config.schema import ArmatureConfig, ProjectConfig
from armature.gc.agents.dead_code import _check_function_size, scan_dead_code


class TestCheckFunctionSize:
    """Tests for _check_function_size() oversized function detection."""

    def test_detects_oversized_function(self, tmp_path: Path):
        f = tmp_path / "big.py"
        # Create a function with 60 lines
        lines = ["def big_function():"]
        for i in range(59):
            lines.append(f"    x{i} = {i}")
        f.write_text("\n".join(lines), encoding="utf-8")

        findings = _check_function_size(f, tmp_path, max_lines=50)
        assert len(findings) >= 1
        assert "oversized_function" in findings[0].category
        assert "big_function" in findings[0].message

    def test_passes_small_function(self, tmp_path: Path):
        f = tmp_path / "small.py"
        f.write_text("def small():\n    return 1\n", encoding="utf-8")

        findings = _check_function_size(f, tmp_path, max_lines=50)
        assert len(findings) == 0

    def test_handles_syntax_error(self, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n", encoding="utf-8")

        findings = _check_function_size(f, tmp_path, max_lines=50)
        assert len(findings) == 0  # gracefully skips


class TestScanDeadCode:
    """Tests for scan_dead_code() top-level scanner."""

    def test_scans_src_dir(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "small.py").write_text("def f():\n    return 1\n", encoding="utf-8")

        config = ArmatureConfig(project=ProjectConfig(src_dir="src/", test_dir="tests/"))
        findings = scan_dead_code(tmp_path, config)
        assert isinstance(findings, list)

    def test_empty_project_no_findings(self, tmp_path: Path):
        config = ArmatureConfig(project=ProjectConfig(src_dir="src/", test_dir="tests/"))
        findings = scan_dead_code(tmp_path, config)
        assert len(findings) == 0
