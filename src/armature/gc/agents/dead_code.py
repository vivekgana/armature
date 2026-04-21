"""GC Agent: Dead code and entropy detection.

Finds orphaned test files, oversized functions, and unused patterns.
"""

from __future__ import annotations

import ast
from pathlib import Path

from armature._internal.types import GCFinding, Severity
from armature.config.schema import ArmatureConfig


def scan_dead_code(root: Path, config: ArmatureConfig) -> list[GCFinding]:
    """Scan for dead code indicators."""
    findings: list[GCFinding] = []
    src_dir = root / config.project.src_dir
    test_dir = root / config.project.test_dir

    # Find oversized functions
    if src_dir.exists():
        for py_file in src_dir.rglob("*.py"):
            findings.extend(_check_function_size(py_file, root, max_lines=50))

    # Find orphaned test files (tests referencing non-existent specs)
    if config.specs.enabled and test_dir.exists():
        findings.extend(_check_orphaned_tests(test_dir, root, config))

    return findings


def _check_function_size(file_path: Path, root: Path, max_lines: int) -> list[GCFinding]:
    """Find functions exceeding max_lines."""
    findings: list[GCFinding] = []
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return findings

    for node in ast.walk(tree):
        is_func = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        if is_func and hasattr(node, "end_lineno") and node.end_lineno:
            size = node.end_lineno - node.lineno
            if size > max_lines:
                findings.append(GCFinding(
                    agent="dead_code",
                    category="oversized_function",
                    file=str(file_path.relative_to(root)),
                    message=f"{node.name}() is {size} lines (max {max_lines})",
                    severity=Severity.WARNING,
                ))

    return findings


def _check_orphaned_tests(test_dir: Path, root: Path, config: ArmatureConfig) -> list[GCFinding]:
    """Find test files referencing spec IDs that don't exist."""
    import re

    findings: list[GCFinding] = []
    spec_pattern = re.compile(config.specs.traceability.pattern)
    specs_dir = root / config.specs.dir

    # Collect existing spec IDs
    existing_specs: set[str] = set()
    if specs_dir.exists():
        for spec_file in specs_dir.glob("*.yaml"):
            try:
                import yaml
                data = yaml.safe_load(spec_file.read_text(encoding="utf-8"))
                if data and "spec_id" in data:
                    existing_specs.add(data["spec_id"])
            except Exception:
                continue

    # Scan test files for spec references
    for test_file in test_dir.rglob("*.py"):
        try:
            content = test_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for match in spec_pattern.finditer(content):
            spec_id = match.group(1)
            if spec_id.startswith("SPEC-YYYY"):
                continue
            if spec_id not in existing_specs:
                findings.append(GCFinding(
                    agent="dead_code",
                    category="orphaned_test",
                    file=str(test_file.relative_to(root)),
                    message=f"References non-existent spec: {spec_id}",
                    severity=Severity.WARNING,
                ))

    return findings
