"""Input validation utilities to prevent path traversal and injection attacks."""

from __future__ import annotations

import re
from pathlib import Path

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_\-\.]{1,128}$")

ALLOWED_TOOLS = frozenset({
    "ruff", "flake8", "pylint", "eslint", "biome",
    "mypy", "pyright", "tsc", "pytype",
    "pytest", "unittest", "jest", "vitest",
})

ALLOWED_LANGUAGES = frozenset({
    "python", "typescript", "javascript", "go", "rust", "java", "kotlin", "ruby",
})

VALID_FAILURE_TYPES = frozenset({"lint", "type", "test"})

VALID_GC_AGENTS = frozenset({"architecture", "docs", "dead_code", "budget"})

VALID_COMPLEXITIES = frozenset({"low", "medium", "high", "critical"})

_DANGEROUS_ARG_CHARS = frozenset({";", "|", "&", "`", "$", ">", "<", "\n"})


def validate_spec_id(spec_id: str) -> str:
    if not _SAFE_IDENTIFIER.match(spec_id):
        raise ValueError(
            f"Invalid spec_id: {spec_id!r}. "
            "Only alphanumerics, hyphens, underscores, and dots allowed (max 128 chars)."
        )
    return spec_id


def validate_path_within_root(file_path: str, root: Path) -> Path:
    resolved = (root / file_path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Path {file_path!r} is outside project root")
    return resolved


def validate_tool_name(tool: str) -> str:
    if tool and tool not in ALLOWED_TOOLS:
        raise ValueError(f"Tool {tool!r} not in allowed list: {sorted(ALLOWED_TOOLS)}")
    return tool


def validate_tool_args(args: list[str]) -> list[str]:
    for arg in args:
        if any(c in arg for c in _DANGEROUS_ARG_CHARS):
            raise ValueError(f"Dangerous character in tool argument: {arg!r}")
    return args


def validate_language(language: str) -> str:
    if language and language not in ALLOWED_LANGUAGES:
        raise ValueError(f"Language {language!r} not in allowed list: {sorted(ALLOWED_LANGUAGES)}")
    return language
