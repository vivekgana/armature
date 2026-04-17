"""Auto-detect project type, language, and framework."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProjectDetection:
    """Result of project auto-detection."""
    language: str
    framework: str
    src_dir: str
    test_dir: str
    lint_tool: str
    type_tool: str
    test_tool: str


def detect_project(root: Path | None = None) -> ProjectDetection:
    """Auto-detect project language, framework, and tooling.

    Examines marker files (pyproject.toml, package.json, go.mod, Cargo.toml)
    to determine the project type and suggest appropriate defaults.
    """
    root = root or Path.cwd()

    # Python detection
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        framework = _detect_python_framework(root)
        src_dir = _detect_python_src(root)
        return ProjectDetection(
            language="python",
            framework=framework,
            src_dir=src_dir,
            test_dir="tests/",
            lint_tool="ruff",
            type_tool="mypy",
            test_tool="pytest",
        )

    # TypeScript/JavaScript detection
    if (root / "package.json").exists():
        framework = _detect_ts_framework(root)
        src_dir = "src/" if (root / "src").exists() else "./"
        test_dir = "__tests__/" if (root / "__tests__").exists() else "tests/"
        return ProjectDetection(
            language="typescript",
            framework=framework,
            src_dir=src_dir,
            test_dir=test_dir,
            lint_tool="eslint",
            type_tool="tsc",
            test_tool="jest" if (root / "jest.config.ts").exists() or (root / "jest.config.js").exists() else "vitest",
        )

    # Go detection
    if (root / "go.mod").exists():
        return ProjectDetection(
            language="go",
            framework="",
            src_dir="./",
            test_dir="./",
            lint_tool="golangci-lint",
            type_tool="go-vet",
            test_tool="go-test",
        )

    # Rust detection
    if (root / "Cargo.toml").exists():
        return ProjectDetection(
            language="rust",
            framework="",
            src_dir="src/",
            test_dir="tests/",
            lint_tool="clippy",
            type_tool="rustc",
            test_tool="cargo-test",
        )

    # Default to Python
    return ProjectDetection(
        language="python",
        framework="",
        src_dir="src/" if (root / "src").exists() else "./",
        test_dir="tests/" if (root / "tests").exists() else "./",
        lint_tool="ruff",
        type_tool="mypy",
        test_tool="pytest",
    )


def _detect_python_framework(root: Path) -> str:
    """Detect Python web framework from dependencies."""
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8").lower()
        if "fastapi" in content:
            return "fastapi"
        if "django" in content:
            return "django"
        if "flask" in content:
            return "flask"
    return ""


def _detect_python_src(root: Path) -> str:
    """Detect Python source directory."""
    if (root / "src").exists():
        return "src/"
    if (root / "app").exists():
        return "app/"
    return "./"


def _detect_ts_framework(root: Path) -> str:
    """Detect TypeScript/JavaScript framework from package.json."""
    pkg = root / "package.json"
    if pkg.exists():
        content = pkg.read_text(encoding="utf-8").lower()
        if "next" in content:
            return "nextjs"
        if "express" in content:
            return "express"
        if "react" in content:
            return "react"
        if "vue" in content:
            return "vue"
    return ""
