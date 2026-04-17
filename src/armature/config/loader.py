"""YAML configuration loading with defaults and validation."""

from __future__ import annotations

from pathlib import Path

import yaml

from armature.config.schema import ArmatureConfig

CONFIG_FILENAMES = ["armature.yaml", "armature.yml", ".armature.yaml", ".armature.yml"]


def find_config(start_dir: Path | None = None) -> Path | None:
    """Search for armature.yaml starting from start_dir, walking up to root.

    Stops at git repository boundaries and the user home directory
    to prevent loading a malicious config from an ancestor directory.
    """
    current = (start_dir or Path.cwd()).resolve()
    home = Path.home().resolve()

    for _ in range(20):
        for name in CONFIG_FILENAMES:
            candidate = current / name
            if candidate.exists():
                return candidate
        if (current / ".git").exists() or current == home or current.parent == current:
            break
        current = current.parent
    return None


def load_config(config_path: Path | None = None) -> ArmatureConfig:
    """Load and validate armature.yaml.

    Args:
        config_path: Explicit path to config file. If None, searches for it.

    Returns:
        Validated ArmatureConfig instance.

    Raises:
        FileNotFoundError: If no config file found and config_path is None.
    """
    if config_path is None:
        config_path = find_config()
    if config_path is None:
        return ArmatureConfig()  # return defaults when no config exists

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if raw is None:
        return ArmatureConfig()

    return ArmatureConfig.model_validate(raw)


def load_config_or_defaults() -> ArmatureConfig:
    """Load config if it exists, otherwise return defaults."""
    config_path = find_config()
    if config_path is None:
        return ArmatureConfig()
    return load_config(config_path)
