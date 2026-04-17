"""AST-based cross-boundary import linter.

Reads layer definitions from armature.yaml and enforces boundary rules.
"""

from __future__ import annotations

from pathlib import Path

from armature.architecture.boundary import check_boundaries
from armature.config.loader import load_config_or_defaults


def lint_imports(root: Path | None = None, *, use_json: bool = False) -> int:
    """Run import boundary linting. Returns exit code (0=pass, 1=violations)."""
    root = root or Path.cwd()
    config = load_config_or_defaults()

    if not config.architecture.enabled:
        print("Architecture enforcement is disabled in armature.yaml")
        return 0

    violations = check_boundaries(config.architecture, root)

    if use_json:
        import json
        output = [{"file": v.file, "line": v.line, "rule": v.rule,
                    "message": v.message, "remediation": v.remediation} for v in violations]
        print(json.dumps(output, indent=2))
    else:
        if not violations:
            print("import_linter: PASS -- no cross-boundary import violations")
            return 0
        print(f"import_linter: FAIL -- {len(violations)} violation(s)\n")
        for v in violations:
            print(str(v))
            print()

    return 1 if violations else 0
