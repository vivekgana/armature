"""Example Armature plugin -- template for community authors.

Copy this file, rename the class, update ``name`` / ``version`` / ``description``,
implement the hooks you need, and publish to PyPI.
"""

from __future__ import annotations

from armature._internal.types import CheckResult, GCFinding, HealResult
from armature.plugins import ArmaturePlugin


class ExamplePlugin(ArmaturePlugin):
    """A minimal example Armature plugin.

    This plugin logs a message after every quality check.  Use it as a
    starting point for your own custom checks, healers, or reporters.
    """

    name: str = "example-plugin"
    version: str = "0.1.0"
    description: str = "Example plugin -- demonstrates the Armature plugin interface"

    def on_check(
        self,
        file_path: str | None,
        results: list[CheckResult],
    ) -> list[CheckResult]:
        """Add a custom check result demonstrating a pass."""
        custom = CheckResult(
            name="example_check",
            passed=True,
            violation_count=0,
            details="example-plugin: no issues found",
            score=1.0,
            weight=5,
        )
        return results + [custom]

    def on_heal(
        self,
        failures: set[str],
        results: list[HealResult],
    ) -> list[HealResult]:
        """Return results unchanged (no custom healing logic)."""
        return results

    def on_gc(
        self,
        findings: list[GCFinding],
    ) -> list[GCFinding]:
        """Return findings unchanged (no custom GC logic)."""
        return findings
