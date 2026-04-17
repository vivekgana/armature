"""Tests for integrations/cursor.py -- Cursor rules generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature.config.schema import ArmatureConfig
from armature.integrations.cursor import generate_cursor_rules


class TestGenerateCursorRules:
    """Tests for generate_cursor_rules()."""

    def test_creates_rules_file(self, tmp_path: Path, monkeypatch, sample_config: ArmatureConfig):
        monkeypatch.chdir(tmp_path)
        path = generate_cursor_rules(sample_config)
        assert path.exists()
        assert path.name == "rules"
        content = path.read_text(encoding="utf-8")
        assert "Armature" in content

    def test_includes_boundary_rules(self, tmp_path: Path, monkeypatch, sample_config: ArmatureConfig):
        monkeypatch.chdir(tmp_path)
        path = generate_cursor_rules(sample_config)
        content = path.read_text(encoding="utf-8")
        assert "Layer Boundaries" in content
        assert "models" in content

    def test_includes_quality_gates(self, tmp_path: Path, monkeypatch, sample_config: ArmatureConfig):
        monkeypatch.chdir(tmp_path)
        path = generate_cursor_rules(sample_config)
        content = path.read_text(encoding="utf-8")
        assert "Quality Requirements" in content
        assert "armature check" in content
