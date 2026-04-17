"""Class hierarchy/conformance linter.

Checks that classes matching configured patterns follow required hierarchy.
"""

from __future__ import annotations

from pathlib import Path

from armature.architecture.conformance import check_conformance
from armature.config.loader import load_config_or_defaults


def lint_classes(root: Path | None = None, *, use_json: bool = False) -> int:
    """Run class conformance linting. Returns exit code (0=pass, 1=violations)."""
    root = root or Path.cwd()
    config = load_config_or_defaults()

    if not config.architecture.enabled:
        print("Architecture enforcement is disabled in armature.yaml")
        return 0

    violations = check_conformance(config.architecture, root)

    if use_json:
        import json
        output = [{"file": v.file, "line": v.line, "rule": v.rule,
                    "message": v.message, "remediation": v.remediation} for v in violations]
        print(json.dumps(output, indent=2))
    else:
        if not violations:
            print("class_linter: PASS -- no conformance violations")
            return 0
        print(f"class_linter: FAIL -- {len(violations)} violation(s)\n")
        for v in violations:
            print(str(v))
            print()

    return 1 if violations else 0
