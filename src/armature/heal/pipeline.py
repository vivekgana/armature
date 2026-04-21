"""Self-healing pipeline orchestrator.

Runs healers (lint, type, test) with circuit breakers per failure type.
Saves structured failure reports for human review when circuit opens.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from armature._internal.output import console
from armature._internal.subprocess_utils import run_tool
from armature._internal.types import HealResult
from armature._internal.validation import validate_spec_id
from armature.config.schema import HealConfig
from armature.heal.circuit_breaker import CircuitBreaker


class HealPipeline:
    """Orchestrates self-healing with circuit breakers per failure type."""

    def __init__(self, config: HealConfig) -> None:
        self.config = config
        self.root = Path.cwd()

    def heal(self, failure_types: set[str]) -> list[HealResult]:
        """Run healers for the specified failure types."""
        results: list[HealResult] = []
        healers = {"lint": self._heal_lint, "type": self._heal_type, "test": self._heal_test}

        for ft in sorted(failure_types):
            healer_config = self.config.healers.get(ft if ft != "type" else "type_check")
            if healer_config is None or not healer_config.enabled:
                continue

            healer = healers.get(ft)
            if healer is None:
                continue

            console.print(f"  --- {ft} ---")
            result = healer()
            results.append(result)
            icon = "[green]FIXED[/green]" if result.fixed else "[red]ESCALATE[/red]"
            console.print(f"  [{icon}] {result.details}\n")

        return results

    def _heal_lint(self) -> HealResult:
        """Auto-fix lint violations using the configured lint tool."""
        circuit = CircuitBreaker(threshold=self.config.circuit_breaker_threshold)

        for attempt in range(1, self.config.max_attempts + 1):
            if circuit.is_open:
                break

            # Check current violations
            result = run_tool(["ruff", "check", ".", "--statistics"], cwd=self.root)
            if result.ok:
                return HealResult("lint", attempt, fixed=True, remaining_errors=0, details="No lint violations")

            violation_count = len([line for line in result.stdout.strip().split("\n") if line.strip()])

            # Attempt auto-fix
            run_tool(["ruff", "check", ".", "--fix"], cwd=self.root)

            # Re-check
            recheck = run_tool(["ruff", "check", ".", "--statistics"], cwd=self.root)
            if recheck.ok:
                circuit.record_success(f"Fixed {violation_count} violations")
                return HealResult("lint", attempt, fixed=True, remaining_errors=0,
                                  details=f"Fixed {violation_count} violations on attempt {attempt}")

            remaining = len([line for line in recheck.stdout.strip().split("\n") if line.strip()])
            circuit.record_failure(f"{remaining} violations remain after ruff --fix")

        return HealResult("lint", self.config.max_attempts, fixed=False, remaining_errors=remaining,
                          details=f"Circuit open after {self.config.max_attempts} attempts. "
                                  f"{remaining} unfixable violations.")

    def _heal_type(self) -> HealResult:
        """Report type errors with fix suggestions."""
        circuit = CircuitBreaker(threshold=self.config.circuit_breaker_threshold)

        for attempt in range(1, self.config.max_attempts + 1):
            if circuit.is_open:
                break

            result = run_tool(["mypy", ".", "--no-error-summary", "--no-pretty"], cwd=self.root, timeout=60)
            if result.ok:
                return HealResult("type", attempt, fixed=True, remaining_errors=0, details="No type errors")

            error_lines = [line for line in result.stdout.strip().split("\n") if ": error:" in line]
            error_count = len(error_lines)
            circuit.record_failure(f"{error_count} mypy errors remain")

        return HealResult("type", self.config.max_attempts, fixed=False, remaining_errors=error_count,
                          details=f"Circuit open. {error_count} type errors require manual intervention.\n"
                                  f"  Common fixes: add `from __future__ import annotations`, "
                                  f"add missing imports, add `type: ignore` for untyped libs")

    def _heal_test(self) -> HealResult:
        """Run failing tests and report diagnostics."""
        circuit = CircuitBreaker(threshold=self.config.circuit_breaker_threshold)

        for attempt in range(1, self.config.max_attempts + 1):
            if circuit.is_open:
                break

            result = run_tool(["pytest", "-x", "--tb=short", "-q", "--no-header"], cwd=self.root, timeout=120)
            if result.ok:
                return HealResult("test", attempt, fixed=True, remaining_errors=0, details="All tests pass")

            output = result.stdout + result.stderr
            failure_lines = [line for line in output.split("\n") if "FAILED" in line or "ERROR" in line]
            error_count = len(failure_lines)
            circuit.record_failure(f"{error_count} test failure(s)")

        return HealResult("test", self.config.max_attempts, fixed=False, remaining_errors=error_count,
                          details=f"Circuit open. {error_count} test failures require human review.")

    def save_failure_report(self, spec_id: str, results: list[HealResult]) -> Path:
        """Save structured failure report for human review."""
        spec_id = validate_spec_id(spec_id)
        report_dir = self.root / self.config.failure_report_dir
        report_dir.mkdir(parents=True, exist_ok=True)

        report = {
            "spec_id": spec_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "results": [
                {"failure_type": r.failure_type, "fixed": r.fixed, "attempts": r.attempt,
                 "remaining_errors": r.remaining_errors, "details": r.details}
                for r in results
            ],
            "overall_fixed": all(r.fixed for r in results),
        }
        output = report_dir / f"{spec_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return output
