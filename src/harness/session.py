"""Session lifecycle management."""

from __future__ import annotations

from pathlib import Path


def ensure_storage(root: Path | None = None) -> Path:
    """Ensure .armature/ storage directory exists."""
    root = root or Path.cwd()
    storage = root / ".armature"
    storage.mkdir(exist_ok=True)
    for subdir in ["baselines", "budget", "gc", "failures"]:
        (storage / subdir).mkdir(exist_ok=True)
    return storage
