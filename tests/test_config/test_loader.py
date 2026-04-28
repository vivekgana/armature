"""Tests for config/loader.py -- YAML loading and config discovery."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from armature.config.loader import (
    _deep_merge,
    _load_remote_config,
    _resolve_extends,
    find_config,
    load_config,
    load_config_or_defaults,
)
from armature.config.schema import ArmatureConfig


class TestFindConfig:
    """Tests for find_config() config file discovery."""

    def test_finds_armature_yaml(self, tmp_path: Path):
        config_path = tmp_path / "armature.yaml"
        config_path.write_text("project:\n  name: test\n", encoding="utf-8")
        result = find_config(tmp_path)
        assert result == config_path

    def test_finds_armature_yml(self, tmp_path: Path):
        config_path = tmp_path / "armature.yml"
        config_path.write_text("project:\n  name: test\n", encoding="utf-8")
        result = find_config(tmp_path)
        assert result == config_path

    def test_finds_dotfile(self, tmp_path: Path):
        config_path = tmp_path / ".armature.yaml"
        config_path.write_text("project:\n  name: test\n", encoding="utf-8")
        result = find_config(tmp_path)
        assert result == config_path

    def test_returns_none_when_missing(self, tmp_path: Path):
        result = find_config(tmp_path)
        assert result is None

    def test_walks_up_directories(self, tmp_path: Path):
        config_path = tmp_path / "armature.yaml"
        config_path.write_text("project:\n  name: test\n", encoding="utf-8")
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        result = find_config(nested)
        assert result == config_path


class TestLoadConfig:
    """Tests for load_config() and load_config_or_defaults()."""

    def test_load_valid_yaml(self, tmp_path: Path):
        config_data = {
            "project": {"name": "test-proj", "language": "python"},
            "quality": {"enabled": True},
        }
        config_path = tmp_path / "armature.yaml"
        config_path.write_text(yaml.dump(config_data), encoding="utf-8")

        config = load_config(config_path)
        assert config.project.name == "test-proj"
        assert config.quality.enabled is True

    def test_load_empty_yaml_returns_defaults(self, tmp_path: Path):
        config_path = tmp_path / "armature.yaml"
        config_path.write_text("", encoding="utf-8")
        config = load_config(config_path)
        assert isinstance(config, ArmatureConfig)
        assert config.project.language == "python"

    def test_load_config_or_defaults_no_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = load_config_or_defaults()
        assert isinstance(config, ArmatureConfig)
        assert config.quality.enabled is True

    def test_load_config_or_defaults_with_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "armature.yaml"
        config_path.write_text("project:\n  name: from-file\n", encoding="utf-8")
        config = load_config_or_defaults()
        assert config.project.name == "from-file"


# ---------------------------------------------------------------------------
# extends: directive tests
# ---------------------------------------------------------------------------

class TestDeepMerge:
    def test_override_wins_for_scalars(self):
        base = {"a": 1, "b": 2}
        override = {"b": 99, "c": 3}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 99, "c": 3}

    def test_nested_dicts_are_merged(self):
        base = {"project": {"name": "base", "language": "python"}}
        override = {"project": {"name": "override"}}
        result = _deep_merge(base, override)
        assert result["project"]["name"] == "override"
        assert result["project"]["language"] == "python"

    def test_non_dict_override_replaces_base(self):
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = _deep_merge(base, override)
        assert result["items"] == [4, 5]


class TestResolveExtends:
    def test_no_extends_key_returns_unchanged(self):
        raw = {"project": {"name": "test"}}
        result = _resolve_extends(raw)
        assert result == {"project": {"name": "test"}}

    def test_extends_key_is_consumed(self):
        """The 'extends' key must not appear in the returned dict."""
        with patch(
            "armature.config.loader._load_remote_config",
            return_value={"project": {"name": "base", "language": "python"}},
        ):
            raw = {"extends": "/fake/path.yaml", "project": {"name": "override"}}
            result = _resolve_extends(raw)
        assert "extends" not in result

    def test_project_override_wins_over_base(self):
        base = {"project": {"name": "base-name", "language": "python"}}
        with patch("armature.config.loader._load_remote_config", return_value=base):
            raw = {"extends": "/fake/base.yaml", "project": {"name": "my-project"}}
            result = _resolve_extends(raw)
        assert result["project"]["name"] == "my-project"
        assert result["project"]["language"] == "python"

    def test_non_string_extends_ignored(self):
        raw = {"extends": 123, "project": {"name": "test"}}
        result = _resolve_extends(raw)
        assert result["project"]["name"] == "test"

    def test_extends_load_failure_returns_original(self):
        with patch("armature.config.loader._load_remote_config", return_value=None):
            raw = {"extends": "/nonexistent/path.yaml", "project": {"name": "test"}}
            result = _resolve_extends(raw)
        assert result["project"]["name"] == "test"


class TestLoadRemoteConfig:
    def test_loads_local_file(self, tmp_path: Path):
        base = tmp_path / "base.yaml"
        base.write_text("project:\n  name: base\n", encoding="utf-8")
        result = _load_remote_config(str(base))
        assert result == {"project": {"name": "base"}}

    def test_returns_none_for_missing_file(self):
        result = _load_remote_config("/nonexistent/path.yaml")
        assert result is None

    def test_returns_none_for_http(self):
        """http:// URLs should be rejected (insecure)."""
        result = _load_remote_config("http://example.com/config.yaml")
        assert result is None

    def test_returns_none_when_yaml_not_mapping(self, tmp_path: Path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("- item1\n- item2\n", encoding="utf-8")
        result = _load_remote_config(str(bad))
        assert result is None

    def test_https_url_is_fetched(self):
        yaml_content = b"project:\n  name: remote\n"
        mock_resp = patch("urllib.request.urlopen")
        with mock_resp as m:
            cm = m.return_value.__enter__.return_value
            cm.read.return_value = yaml_content
            result = _load_remote_config("https://example.com/config.yaml")
        assert result == {"project": {"name": "remote"}}

    def test_load_config_with_local_extends(self, tmp_path: Path):
        base = tmp_path / "base.yaml"
        base.write_text("project:\n  name: base\n  language: python\n", encoding="utf-8")

        project = tmp_path / "armature.yaml"
        project.write_text(f"extends: {base}\nproject:\n  name: child\n", encoding="utf-8")

        config = load_config(project)
        assert config.project.name == "child"
        assert config.project.language == "python"

