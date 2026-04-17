"""Pattern conformance checker -- class hierarchy enforcement.

Verifies that classes follow required patterns (e.g., all Agents
inherit BaseAgent, all Errors inherit AppError).
"""

from __future__ import annotations

from pathlib import Path

from armature._internal.ast_utils import extract_classes
from armature._internal.types import CheckResult, Violation
from armature.config.schema import ArchitectureConfig


def check_conformance(config: ArchitectureConfig, root: Path) -> list[Violation]:
    """Check class conformance rules across the codebase."""
    violations: list[Violation] = []

    for rule in config.conformance:
        for rule_dir in rule.dirs:
            dir_path = root / rule_dir
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                classes = extract_classes(py_file)
                for cls in classes:
                    # Skip if class doesn't match the pattern
                    if rule.pattern not in cls.name:
                        continue

                    # Check base class
                    if rule.base_class and rule.base_class not in cls.bases:
                        # Allow transitive inheritance through checking direct bases
                        violations.append(Violation(
                            file=str(py_file.relative_to(root)),
                            line=cls.line,
                            rule="conformance-base",
                            message=f"{cls.name} does not inherit from {rule.base_class}",
                            remediation=f"class {cls.name}({rule.base_class}): ...",
                        ))

                    # Check required methods
                    for method in rule.required_methods:
                        if method not in cls.methods:
                            violations.append(Violation(
                                file=str(py_file.relative_to(root)),
                                line=cls.line,
                                rule="conformance-method",
                                message=f"{cls.name} missing required method: {method}",
                                remediation=f"Add `def {method}(self, ...):` to {cls.name}",
                            ))

                    # Check required attributes
                    for attr in rule.required_attributes:
                        if attr not in cls.attributes:
                            violations.append(Violation(
                                file=str(py_file.relative_to(root)),
                                line=cls.line,
                                rule="conformance-attr",
                                message=f"{cls.name} missing required attribute: {attr}",
                                remediation=f"Add `{attr} = ...` as class attribute in {cls.name}",
                            ))

    return violations


def run_conformance_check(config: ArchitectureConfig, root: Path) -> CheckResult:
    """Run conformance check and return a CheckResult."""
    violations = check_conformance(config, root)
    return CheckResult(
        name="conformance",
        passed=len(violations) == 0,
        violation_count=len(violations),
        details=f"{len(violations)} conformance violation(s)" if violations else "clean",
        score=1.0 if not violations else max(0.0, 1.0 - len(violations) * 0.15),
    )
