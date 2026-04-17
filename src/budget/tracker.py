"""Session token/cost tracking -- persists usage data to JSONL.

Implements adaptive budget control: tracks actual usage per spec/phase,
compares against declared budgets, and provides optimization recommendations.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from armature.config.schema import BudgetConfig


class SessionTracker:
    """Tracks token/cost per development session, persists to JSONL."""

    def __init__(self, config: BudgetConfig, root: Path | None = None) -> None:
        self.config = config
        self.root = root or Path.cwd()
        self.storage_dir = self.root / config.storage
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        spec_id: str,
        phase: str,
        tokens: int,
        cost_usd: float,
        *,
        task_id: str = "",
        model: str = "",
        provider: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_hit_tokens: int = 0,
        latency_ms: int = 0,
        semantic_cache_hit: bool = False,
        intent: str = "",
    ) -> None:
        """Append a usage entry to the session log.

        Extended fields (model, provider, cache, latency, intent) are
        optional for backward compatibility. Old callers passing only
        positional (spec_id, phase, tokens, cost_usd) continue to work.
        """
        log_path = self.storage_dir / f"{spec_id}_cost.jsonl"
        entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spec_id": spec_id,
            "phase": phase,
            "tokens": tokens,
            "cost_usd": cost_usd,
        }
        # Extended fields -- only written when non-default to keep JSONL compact
        if task_id:
            entry["task_id"] = task_id
        if model:
            entry["model"] = model
        if provider:
            entry["provider"] = provider
        if input_tokens:
            entry["input_tokens"] = input_tokens
        if output_tokens:
            entry["output_tokens"] = output_tokens
        if cache_hit_tokens:
            entry["cache_hit_tokens"] = cache_hit_tokens
        if latency_ms:
            entry["latency_ms"] = latency_ms
        if semantic_cache_hit:
            entry["semantic_cache_hit"] = True
        if intent:
            entry["intent"] = intent

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_usage(self, spec_id: str) -> dict:
        """Get aggregated usage for a spec."""
        entries = self._load_entries(spec_id)
        if not entries:
            return {"total_tokens": 0, "total_cost_usd": 0.0, "phases": {}, "requests": 0}

        phase_totals: dict[str, dict] = {}
        for entry in entries:
            phase = entry["phase"]
            if phase not in phase_totals:
                phase_totals[phase] = {"tokens": 0, "cost_usd": 0.0, "requests": 0}
            phase_totals[phase]["tokens"] += entry["tokens"]
            phase_totals[phase]["cost_usd"] += entry["cost_usd"]
            phase_totals[phase]["requests"] += 1

        total_tokens = sum(p["tokens"] for p in phase_totals.values())
        total_cost = sum(p["cost_usd"] for p in phase_totals.values())
        total_requests = sum(p["requests"] for p in phase_totals.values())

        return {
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "requests": total_requests,
            "phases": phase_totals,
        }

    def get_usage_by_provider(self, spec_id: str) -> dict[str, dict]:
        """Get usage aggregated by provider for cross-provider reporting."""
        entries = self._load_entries(spec_id)
        provider_totals: dict[str, dict] = {}
        for entry in entries:
            prov = entry.get("provider", "unknown")
            if prov not in provider_totals:
                provider_totals[prov] = {
                    "tokens": 0, "cost_usd": 0.0, "requests": 0,
                    "input_tokens": 0, "output_tokens": 0,
                    "cache_hit_tokens": 0, "latency_ms_total": 0,
                    "models": {},
                }
            bucket = provider_totals[prov]
            bucket["tokens"] += entry.get("tokens", 0)
            bucket["cost_usd"] += entry.get("cost_usd", 0.0)
            bucket["requests"] += 1
            bucket["input_tokens"] += entry.get("input_tokens", 0)
            bucket["output_tokens"] += entry.get("output_tokens", 0)
            bucket["cache_hit_tokens"] += entry.get("cache_hit_tokens", 0)
            bucket["latency_ms_total"] += entry.get("latency_ms", 0)

            model = entry.get("model", "unknown")
            if model not in bucket["models"]:
                bucket["models"][model] = {"tokens": 0, "cost_usd": 0.0, "requests": 0}
            bucket["models"][model]["tokens"] += entry.get("tokens", 0)
            bucket["models"][model]["cost_usd"] += entry.get("cost_usd", 0.0)
            bucket["models"][model]["requests"] += 1

        return provider_totals

    def get_usage_by_intent(self, spec_id: str) -> dict[str, dict]:
        """Get usage aggregated by intent for anomaly detection."""
        entries = self._load_entries(spec_id)
        intent_totals: dict[str, dict] = {}
        for entry in entries:
            intent = entry.get("intent", "unknown")
            if intent not in intent_totals:
                intent_totals[intent] = {"tokens": 0, "cost_usd": 0.0, "requests": 0, "costs": []}
            bucket = intent_totals[intent]
            bucket["tokens"] += entry.get("tokens", 0)
            bucket["cost_usd"] += entry.get("cost_usd", 0.0)
            bucket["requests"] += 1
            bucket["costs"].append(entry.get("cost_usd", 0.0))
        return intent_totals

    def get_semantic_cache_stats(self, spec_id: str) -> dict:
        """Get semantic cache hit/miss stats for a spec."""
        entries = self._load_entries(spec_id)
        hits = sum(1 for e in entries if e.get("semantic_cache_hit"))
        total = len(entries)
        tokens_saved = sum(e.get("tokens", 0) for e in entries if e.get("semantic_cache_hit"))
        return {
            "total_requests": total,
            "cache_hits": hits,
            "cache_misses": total - hits,
            "hit_rate": hits / total if total > 0 else 0.0,
            "tokens_saved": tokens_saved,
        }

    def get_cross_spec_trends(self, limit: int = 10) -> list[dict]:
        """Get cost trends across recent specs for trend reporting."""
        specs = self.list_specs()[-limit:]
        trends = []
        for spec_id in specs:
            usage = self.get_usage(spec_id)
            provider_usage = self.get_usage_by_provider(spec_id)
            cache_stats = self.get_semantic_cache_stats(spec_id)
            model_count = sum(
                len(p.get("models", {})) for p in provider_usage.values()
            )
            trends.append({
                "spec_id": spec_id,
                "total_tokens": usage["total_tokens"],
                "total_cost_usd": usage["total_cost_usd"],
                "requests": usage["requests"],
                "providers": len(provider_usage),
                "models_used": model_count,
                "cache_hit_rate": cache_stats["hit_rate"],
            })
        return trends

    def _load_entries(self, spec_id: str) -> list[dict]:
        """Load all JSONL entries for a spec (backward-compatible)."""
        log_path = self.storage_dir / f"{spec_id}_cost.jsonl"
        if not log_path.exists():
            return []
        entries = []
        for line in log_path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                entries.append(json.loads(line))
        return entries

    def is_over_budget(self, spec_id: str, complexity: str = "medium") -> bool:
        """Check if a spec has exceeded its budget."""
        usage = self.get_usage(spec_id)
        tier = self.config.defaults.get(complexity)
        if tier is None:
            return False
        return usage["total_tokens"] > tier.max_tokens or usage["total_cost_usd"] > tier.max_cost_usd

    def get_optimization_suggestions(self, spec_id: str, complexity: str = "medium") -> list[str]:
        """Analyze usage patterns and suggest optimizations.

        Adaptive approach: examines phase distribution and per-request
        token usage to recommend specific actions.
        """
        usage = self.get_usage(spec_id)
        if usage["requests"] == 0:
            return []

        suggestions: list[str] = []
        tier = self.config.defaults.get(complexity)
        if tier is None:
            return suggestions

        # Check overall budget
        token_pct = (usage["total_tokens"] / tier.max_tokens) * 100 if tier.max_tokens > 0 else 0
        cost_pct = (usage["total_cost_usd"] / tier.max_cost_usd) * 100 if tier.max_cost_usd > 0 else 0

        if token_pct > 80:
            suggestions.append(f"Approaching token budget ({token_pct:.0f}%). "
                               "Consider: narrow context per task, batch file reads, use /compact.")

        if cost_pct > 80:
            suggestions.append(f"Approaching cost budget ({cost_pct:.0f}%). "
                               "Consider: fewer LLM-based checks, cache results, reduce scope.")

        # Check phase distribution skew
        allocation = self.config.phase_allocation
        for phase, data in usage["phases"].items():
            actual_pct = (data["tokens"] / usage["total_tokens"] * 100) if usage["total_tokens"] > 0 else 0
            expected_pct = allocation.get(phase, 0)
            if expected_pct > 0 and actual_pct > expected_pct * 1.5:
                suggestions.append(
                    f"Phase '{phase}' using {actual_pct:.0f}% of tokens "
                    f"(expected ~{expected_pct}%). Consider narrowing context for this phase."
                )

        # Check average tokens per request
        avg_tokens = usage["total_tokens"] / usage["requests"]
        if avg_tokens > 20_000:
            suggestions.append(
                f"Average {avg_tokens:,.0f} tokens/request is high. "
                "Consider: front-load context in first message, progressive disclosure, "
                "batch related file reads into single requests."
            )

        return suggestions

    def list_specs(self) -> list[str]:
        """List all specs with cost data."""
        specs = []
        for f in self.storage_dir.glob("*_cost.jsonl"):
            spec_id = f.stem.replace("_cost", "")
            specs.append(spec_id)
        return sorted(specs)
