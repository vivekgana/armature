"""YAML configuration loading with defaults and validation.

Supports an ``extends`` top-level key that points to a base config file (local path
or HTTPS URL).  The base config is loaded first, then the project config is
deep-merged on top, so project values always take precedence.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from armature.config.schema import ArmatureConfig

logger = logging.getLogger(__name__)

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

    return ArmatureConfig.model_validate(_resolve_extends(raw))


def load_config_or_defaults() -> ArmatureConfig:
    """Load config if it exists, otherwise return defaults."""
    config_path = find_config()
    if config_path is None:
        return ArmatureConfig()
    return load_config(config_path)


# ---------------------------------------------------------------------------
# extends: directive -- team / org shared config inheritance
# ---------------------------------------------------------------------------

def _resolve_extends(raw: dict[str, Any]) -> dict[str, Any]:
    """Resolve an ``extends`` key by deep-merging the base config underneath *raw*.

    The ``extends`` value can be:
    - A local file path (absolute or relative to cwd)
    - An HTTPS URL pointing to a raw YAML file (e.g. a GitHub raw URL)

    The project config (``raw``) always wins over the base config.
    The ``extends`` key is consumed and not forwarded to Pydantic.
    """
    extends = raw.pop("extends", None)
    if not extends:
        return raw

    if not isinstance(extends, str):
        logger.warning("armature.yaml: 'extends' must be a string, ignoring")
        return raw

    base_raw = _load_remote_config(extends)
    if base_raw is None:
        return raw

    # Recursively resolve the base's own extends chain (max depth handled by call stack)
    base_raw = _resolve_extends(base_raw)

    return _deep_merge(base_raw, raw)


def _load_remote_config(source: str) -> dict[str, Any] | None:
    """Fetch and parse YAML from a URL or local file path.

    Returns the parsed dict, or ``None`` on any error.
    """
    try:
        if source.startswith("https://"):
            import urllib.request
            with urllib.request.urlopen(source, timeout=10) as resp:
                content = resp.read().decode("utf-8")
        elif source.startswith("http://"):
            logger.warning("armature.yaml: 'extends' with http:// is insecure, use https://")
            return None
        else:
            content = Path(source).read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("armature.yaml: failed to load extends %r: %s", source, exc)
        return None

    parsed = yaml.safe_load(content)
    if not isinstance(parsed, dict):
        logger.warning("armature.yaml: extends %r did not return a YAML mapping", source)
        return None
    return parsed


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* on top of *base*.

    Mapping values are merged recursively; all other values from *override*
    replace those in *base*.
    """
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result

