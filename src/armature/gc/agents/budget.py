"""GC Agent: Budget audit across specs."""

from __future__ import annotations

from pathlib import Path

from armature._internal.types import GCFinding, Severity
from armature.budget.tracker import SessionTracker
from armature.config.schema import BudgetConfig


def audit_budgets(root: Path, config: BudgetConfig) -> list[GCFinding]:
    """Audit budget usage across all specs with cost data."""
    findings: list[GCFinding] = []

    if not config.enabled:
        return findings

    tracker = SessionTracker(config, root)
    specs = tracker.list_specs()

    for spec_id in specs:
        usage = tracker.get_usage(spec_id)
        if usage["requests"] == 0:
            continue

        # Check against medium budget (default)
        tier = config.defaults.get("medium")
        if tier:
            token_pct = (usage["total_tokens"] / tier.max_tokens * 100) if tier.max_tokens > 0 else 0
            cost_pct = (usage["total_cost_usd"] / tier.max_cost_usd * 100) if tier.max_cost_usd > 0 else 0

            if token_pct > 100 or cost_pct > 100:
                findings.append(GCFinding(
                    agent="budget",
                    category="over_budget",
                    file=f".armature/budget/{spec_id}_cost.jsonl",
                    message=(f"{spec_id}: {usage['total_tokens']:,} tokens ({token_pct:.0f}%), "
                             f"${usage['total_cost_usd']:.2f} ({cost_pct:.0f}%) -- OVER BUDGET"),
                    severity=Severity.WARNING,
                ))

        # Check for optimization opportunities
        suggestions = tracker.get_optimization_suggestions(spec_id)
        for s in suggestions:
            findings.append(GCFinding(
                agent="budget",
                category="optimization",
                file=f".armature/budget/{spec_id}_cost.jsonl",
                message=f"{spec_id}: {s}",
                severity=Severity.INFO,
            ))

    return findings
