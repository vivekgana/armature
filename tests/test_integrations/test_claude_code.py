"""Tests for integrations/claude_code.py -- Claude Code hook generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from armature.config.schema import ArmatureConfig, ClaudeCodeConfig, IntegrationsConfig
from armature.integrations.claude_code import generate_claude_code_hooks


class TestGenerateClaudeCodeHooks:
    """Tests for generate_claude_code_hooks()."""

    def test_creates_settings_file(self, tmp_path: Path, monkeypatch, sample_config: ArmatureConfig):
        monkeypatch.chdir(tmp_path)
        path = generate_claude_code_hooks(sample_config)
        assert path.exists()
        assert path.name == "settings.local.json"

    def test_adds_post_tool_use_hook(self, tmp_path: Path, monkeypatch, sample_config: ArmatureConfig):
        monkeypatch.chdir(tmp_path)
        generate_claude_code_hooks(sample_config)
        settings = json.loads((tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
        hooks = settings.get("hooks", {})
        assert "PostToolUse" in hooks
        assert any("armature check" in h["command"] for h in hooks["PostToolUse"])

    def test_adds_pre_session_hook(self, tmp_path: Path, monkeypatch, sample_config: ArmatureConfig):
        monkeypatch.chdir(tmp_path)
        generate_claude_code_hooks(sample_config)
        settings = json.loads((tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
        hooks = settings.get("hooks", {})
        assert "PreSession" in hooks

    def test_adds_permissions(self, tmp_path: Path, monkeypatch, sample_config: ArmatureConfig):
        monkeypatch.chdir(tmp_path)
        generate_claude_code_hooks(sample_config)
        settings = json.loads((tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
        permissions = settings.get("permissions", {}).get("allow", [])
        assert any("armature check" in p for p in permissions)
        assert any("armature heal" in p for p in permissions)

    def test_preserves_existing_settings(self, tmp_path: Path, monkeypatch, sample_config: ArmatureConfig):
        monkeypatch.chdir(tmp_path)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        existing = {"customKey": "customValue", "permissions": {"allow": ["Bash(echo)"]}}
        (claude_dir / "settings.local.json").write_text(json.dumps(existing), encoding="utf-8")

        generate_claude_code_hooks(sample_config)
        settings = json.loads((claude_dir / "settings.local.json").read_text(encoding="utf-8"))
        assert settings["customKey"] == "customValue"
        assert "Bash(echo)" in settings["permissions"]["allow"]

    def test_replaces_existing_armature_hook(self, tmp_path: Path, monkeypatch, sample_config: ArmatureConfig):
        monkeypatch.chdir(tmp_path)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        existing = {"hooks": {"PostToolUse": [
            {"command": "armature check --old", "description": "Armature: old hook"},
        ]}}
        (claude_dir / "settings.local.json").write_text(json.dumps(existing), encoding="utf-8")

        generate_claude_code_hooks(sample_config)
        settings = json.loads((claude_dir / "settings.local.json").read_text(encoding="utf-8"))
        hooks = settings["hooks"]["PostToolUse"]
        # Old hook should be replaced, not duplicated
        armature_hooks = [h for h in hooks if "armature" in h.get("command", "").lower()]
        assert len(armature_hooks) == 1
