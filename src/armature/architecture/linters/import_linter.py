"""AST-based cross-boundary import linter.

Reads layer definitions from armature.yaml and enforces boundary rules.
"""

from __future__ import annotations

from pathlib import Path

from armature.architecture.boundary import check_boundaries
from armature.architecture.linters._shared import format_violations
from armature.config.loader import load_config_or_defaults


def lint_imports(root: Path | None = None, *, use_json: bool = False) -> int:
    """Run import boundary linting. Returns exit code (0=pass, 1=violations)."""
    root = root or Path.cwd()
    config = load_config_or_defaults()

    if not config.architecture.enabled:
        print("Architecture enforcement is disabled in armature.yaml")
        return 0

    violations = check_boundaries(config.architecture, root)
    output, code = format_violations("import_linter", violations, use_json=use_json)
    print(output)
    return code
