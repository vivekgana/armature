"""Budget dataclass and phase allocation logic.

Implements adaptive budget control for AI coding agent sessions:
- Complexity-based budget tiers (low/medium/high/critical)
- Phase allocation (validate/audit/plan/build/test/review)
- Per-request token analysis and optimization recommendations
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DevBudget:
    """Development-time budget constraints per spec.

    Mirrors the LLMLimits pattern -- frozen dataclass for immutable budgets.
    """
    complexity: str = "medium"
    max_tokens_per_spec: int = 500_000
    max_cost_per_spec_usd: float = 10.0
    max_requests_per_task: int = 15
    cache_hit_target_pct: float = 0.30
    phase_allocation: dict[str, float] = field(default_factory=lambda: {
        "validate": 0.05,
        "audit": 0.10,
        "plan": 0.15,
        "build": 0.40,
        "test": 0.25,
        "review": 0.05,
    })

    @staticmethod
    def for_complexity(complexity: str) -> DevBudget:
        """Get a budget instance for a complexity tier."""
        multipliers = {"low": 0.2, "medium": 1.0, "high": 2.0, "critical": 4.0}
        mult = multipliers.get(complexity, 1.0)
        return DevBudget(
            complexity=complexity,
            max_tokens_per_spec=int(500_000 * mult),
            max_cost_per_spec_usd=10.0 * mult,
        )

    def tokens_for_phase(self, phase: str) -> int:
        """Calculate token budget for a specific phase."""
        allocation = self.phase_allocation.get(phase, 0.0)
        return int(self.max_tokens_per_spec * allocation)

    def cost_for_phase(self, phase: str) -> float:
        """Calculate cost budget for a specific phase."""
        allocation = self.phase_allocation.get(phase, 0.0)
        return self.max_cost_per_spec_usd * allocation


# Request optimization patterns with estimated savings
REQUEST_OPTIMIZATION_PATTERNS = {
    "batch_file_reads": {
        "description": "Read 5 related files in one request instead of 5 separate requests",
        "token_savings_pct": 40,
    },
    "front_load_context": {
        "description": "Put spec + relevant code in first message, not drip-fed",
        "token_savings_pct": 25,
    },
    "narrow_context": {
        "description": "Each task sees only its spec_refs + context_files",
        "token_savings_pct": 50,
    },
    "use_compact": {
        "description": "Compress when context exceeds 60% of window",
        "token_savings_pct": 30,
    },
    "progressive_disclosure": {
        "description": "Start with map (CLAUDE.md), navigate deeper as needed",
        "token_savings_pct": 35,
    },
}
