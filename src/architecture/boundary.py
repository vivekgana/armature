"""Layer boundary enforcement engine.

Enforces architectural layer boundaries by analyzing import graphs.
Based on OpenAI pattern: 'We built the application around a rigid architectural
model. Each business domain is divided into a fixed set of layers, with strictly
validated dependency directions.'
"""

from __future__ import annotations

from pathlib import Path

from armature._internal.ast_utils import extract_imports
from armature._internal.types import CheckResult, Violation
from armature.config.schema import ArchitectureConfig


def _resolve_layer(file_path: Path, config: ArchitectureConfig, root: Path) -> str | None:
    """Determine which architectural layer a file belongs to."""
    try:
        rel = str(file_path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return None

    for layer in config.layers:
        for layer_dir in layer.dirs:
            if rel.startswith(layer_dir):
                return layer.name
    return None


def _import_to_layer(import_module: str, config: ArchitectureConfig) -> str | None:
    """Map an import module path to an architectural layer."""
    # Convert module path to file-like path: src.agents.data -> src/agents/data/
    parts = import_module.replace(".", "/")

    for layer in config.layers:
        for layer_dir in layer.dirs:
            if parts.startswith(layer_dir.rstrip("/")):
                return layer.name
    return None


def _is_shared_import(import_module: str, config: ArchitectureConfig) -> bool:
    """Check if an import is from shared infrastructure (always allowed)."""
    parts = import_module.replace(".", "/")
    for shared in config.allowed_shared:
        if parts.startswith(shared.rstrip("/")):
            return True
    return False


def check_boundaries(config: ArchitectureConfig, root: Path) -> list[Violation]:
    """Check all source files for boundary violations."""
    violations: list[Violation] = []

    # Build boundary lookup: {from_layer: set_of_forbidden_layers}
    forbidden: dict[str, set[str]] = {}
    for rule in config.boundaries:
        forbidden.setdefault(rule.from_layer, set()).update(rule.to_layers)

    # Scan all Python files in layer directories
    for layer in config.layers:
        for layer_dir in layer.dirs:
            dir_path = root / layer_dir
            if not dir_path.exists():
                continue
            for py_file in dir_path.rglob("*.py"):
                source_layer = layer.name
                if source_layer not in forbidden:
                    continue

                for imp in extract_imports(py_file):
                    if _is_shared_import(imp.module, config):
                        continue
                    target_layer = _import_to_layer(imp.module, config)
                    if target_layer and target_layer in forbidden[source_layer]:
                        violations.append(Violation(
                            file=str(py_file.relative_to(root)),
                            line=imp.line,
                            rule="layer-boundary",
                            message=f"LAYER BOUNDARY CROSSED: {source_layer} -> {target_layer} (import {imp.module})",
                            remediation=(
                                f"Move shared logic to one of the allowed_shared directories "
                                f"({', '.join(config.allowed_shared)}). "
                                f"If inter-layer communication is needed, use an interface/protocol."
                            ),
                        ))

    return violations


def run_boundary_check(config: ArchitectureConfig, root: Path) -> CheckResult:
    """Run boundary check and return a CheckResult."""
    violations = check_boundaries(config, root)
    return CheckResult(
        name="layer_boundaries",
        passed=len(violations) == 0,
        violation_count=len(violations),
        details=f"{len(violations)} boundary violation(s)" if violations else "clean",
        score=1.0 if not violations else max(0.0, 1.0 - len(violations) * 0.2),
    )
