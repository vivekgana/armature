"""Class hierarchy/conformance linter.

Checks that classes matching configured patterns follow required hierarchy.
"""

from __future__ import annotations

from pathlib import Path

from armature.architecture.conformance import check_conformance
from armature.architecture.linters._shared import format_violations
from armature.config.loader import load_config_or_defaults


def lint_classes(root: Path | None = None, *, use_json: bool = False) -> int:
    """Run class conformance linting. Returns exit code (0=pass, 1=violations)."""
    root = root or Path.cwd()
    config = load_config_or_defaults()

    if not config.architecture.enabled:
        print("Architecture enforcement is disabled in armature.yaml")
        return 0

    violations = check_conformance(config.architecture, root)
    output, code = format_violations("class_linter", violations, use_json=use_json)
    print(output)
    return code
