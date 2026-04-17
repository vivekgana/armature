"""Tests for config/discovery.py -- project auto-detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature.config.discovery import detect_project


class TestDetectProject:
    """Tests for detect_project() auto-detection."""

    def test_detects_python_from_pyproject(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'myapp'\n", encoding="utf-8")
        (tmp_path / "src").mkdir()
        result = detect_project(tmp_path)
        assert result.language == "python"
        assert result.lint_tool == "ruff"
        assert result.type_tool == "mypy"
        assert result.test_tool == "pytest"
        assert result.src_dir == "src/"

    def test_detects_python_fastapi(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\ndependencies = ["fastapi"]\n', encoding="utf-8"
        )
        result = detect_project(tmp_path)
        assert result.framework == "fastapi"

    def test_detects_typescript_from_package_json(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"name": "myapp", "dependencies": {"react": "^18"}}', encoding="utf-8")
        (tmp_path / "src").mkdir()
        result = detect_project(tmp_path)
        assert result.language == "typescript"
        assert result.framework == "react"
        assert result.lint_tool == "eslint"

    def test_detects_go_from_go_mod(self, tmp_path: Path):
        (tmp_path / "go.mod").write_text("module myapp\ngo 1.21\n", encoding="utf-8")
        result = detect_project(tmp_path)
        assert result.language == "go"
        assert result.lint_tool == "golangci-lint"

    def test_detects_rust_from_cargo_toml(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "myapp"\n', encoding="utf-8")
        result = detect_project(tmp_path)
        assert result.language == "rust"
        assert result.lint_tool == "clippy"

    def test_defaults_to_python(self, tmp_path: Path):
        result = detect_project(tmp_path)
        assert result.language == "python"
