"""E2E test fixtures for ossature compatibility tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def ossature_fixtures_dir() -> Path:
    """Return path to bundled ossature fixture data."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def spenny_project(ossature_fixtures_dir: Path) -> Path:
    """Spenny: Python CLI expense tracker ossature project."""
    return ossature_fixtures_dir / "spenny"


@pytest.fixture(scope="session")
def markman_project(ossature_fixtures_dir: Path) -> Path:
    """Markman: Rust CLI bookmark manager ossature project."""
    return ossature_fixtures_dir / "markman"


@pytest.fixture(scope="session")
def math_quest_project(ossature_fixtures_dir: Path) -> Path:
    """Math Quest: Lua game (unsupported language test)."""
    return ossature_fixtures_dir / "math_quest"
