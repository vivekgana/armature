"""Tests for config/loader.py -- YAML loading and config discovery."""

from __future__ import annotations

from pathlib import Path

import yaml

from armature.config.loader import find_config, load_config, load_config_or_defaults
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
