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


@pytest.fixture(scope="session")
def examples_dir() -> Path:
    """Return path to example projects."""
    return Path(__file__).parent.parent.parent / "examples"


@pytest.fixture(scope="session")
def python_fastapi_project(examples_dir: Path) -> Path:
    """Python FastAPI example project with specs."""
    return examples_dir / "python-fastapi"


@pytest.fixture(scope="session")
def typescript_nextjs_project(examples_dir: Path) -> Path:
    """TypeScript Next.js example project with specs."""
    return examples_dir / "typescript-nextjs"


@pytest.fixture(scope="session")
def monorepo_project(examples_dir: Path) -> Path:
    """Monorepo example project with specs."""
    return examples_dir / "monorepo"
