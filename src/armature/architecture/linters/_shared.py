"""Shared linter output formatting."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from armature._internal.types import ArchViolation


def format_violations(linter_name: str, violations: list[ArchViolation], *, use_json: bool) -> tuple[str, int]:
    """Format violations for output. Returns (output_text, exit_code)."""
    if use_json:
        output = [
            {"file": v.file, "line": v.line, "rule": v.rule,
             "message": v.message, "remediation": v.remediation}
            for v in violations
        ]
        return json.dumps(output, indent=2), 1 if violations else 0

    if not violations:
        return f"{linter_name}: PASS -- no violations", 0

    lines = [f"{linter_name}: FAIL -- {len(violations)} violation(s)\n"]
    for v in violations:
        lines.append(str(v))
        lines.append("")
    return "\n".join(lines), 1
