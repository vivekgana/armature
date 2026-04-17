"""Multi-provider model routing -- cost-optimized task-to-model assignment.

Routes each task to the cheapest model that meets a quality threshold for
the task's intent. Decisions are deterministic and happen at plan time,
not runtime -- zero coordination tokens.

Supported providers: Anthropic, OpenAI, Google, Perplexity.
Pricing is per 1M tokens. Capability scores are 0.0-1.0 per dimension.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ProviderModel:
    """Pricing and metadata for a single model."""
    input: float              # $/1M input tokens
    output: float             # $/1M output tokens
    cache_read: float | None  # $/1M cached input (None = no caching support)
    cache_write: float | None  # $/1M cache write (None = no caching support)
    context: int              # max context window tokens
    provider: str             # "anthropic" | "openai" | "google" | "perplexity"


@dataclass(frozen=True)
class ModelCapabilities:
    """Quality scores (0.0-1.0) per capability dimension."""
    code_gen: float
    reasoning: float
    search: float
    explain: float
    test_gen: float

    def score_for(self, intent: str) -> float:
        """Look up the capability score for a given intent."""
        mapping = {
            "code_gen": self.code_gen,
            "complex_code_gen": self.code_gen,
            "simple_code_gen": self.code_gen,
            "reasoning": self.reasoning,
            "architecture": self.reasoning,
            "search": self.search,
            "research": self.search,
            "explain": self.explain,
            "explanation": self.explain,
            "test_gen": self.test_gen,
            "test": self.test_gen,
            "lint_fix": self.code_gen,
        }
        return mapping.get(intent, self.code_gen)


@dataclass
class RoutingDecision:
    """Result of routing a task to a model."""
    model: str
    reason: str                # e.g. "cheapest model meeting code_gen >= 0.90"
    estimated_cost_usd: float
    alternative: str | None    # next cheapest option


# ---------------------------------------------------------------------------
# Provider catalog -- pricing per 1M tokens (as of early 2026)
# ---------------------------------------------------------------------------

PROVIDERS: dict[str, ProviderModel] = {
    # Anthropic
    "claude-opus": ProviderModel(
        input=15.0, output=75.0, cache_read=1.50, cache_write=18.75,
        context=200_000, provider="anthropic",
    ),
    "claude-sonnet": ProviderModel(
        input=3.0, output=15.0, cache_read=0.30, cache_write=3.75,
        context=200_000, provider="anthropic",
    ),
    "claude-haiku": ProviderModel(
        input=0.25, output=1.25, cache_read=0.03, cache_write=0.30,
        context=200_000, provider="anthropic",
    ),
    # OpenAI
    "gpt-4o": ProviderModel(
        input=2.50, output=10.0, cache_read=1.25, cache_write=None,
        context=128_000, provider="openai",
    ),
    "gpt-4o-mini": ProviderModel(
        input=0.15, output=0.60, cache_read=0.075, cache_write=None,
        context=128_000, provider="openai",
    ),
    # Google
    "gemini-2.5-pro": ProviderModel(
        input=1.25, output=10.0, cache_read=0.315, cache_write=4.50,
        context=1_000_000, provider="google",
    ),
    "gemini-2.5-flash": ProviderModel(
        input=0.15, output=0.60, cache_read=0.0375, cache_write=1.00,
        context=1_000_000, provider="google",
    ),
    "gemini-flash-lite": ProviderModel(
        input=0.075, output=0.30, cache_read=None, cache_write=None,
        context=1_000_000, provider="google",
    ),
    # Perplexity
    "sonar-pro": ProviderModel(
        input=3.0, output=15.0, cache_read=None, cache_write=None,
        context=200_000, provider="perplexity",
    ),
    "sonar": ProviderModel(
        input=1.0, output=1.0, cache_read=None, cache_write=None,
        context=128_000, provider="perplexity",
    ),
}

# ---------------------------------------------------------------------------
# Capability matrix -- scores per model per dimension
# ---------------------------------------------------------------------------

CAPABILITIES: dict[str, ModelCapabilities] = {
    "claude-opus": ModelCapabilities(
        code_gen=0.98, reasoning=0.97, search=0.70, explain=0.95, test_gen=0.95,
    ),
    "claude-sonnet": ModelCapabilities(
        code_gen=0.93, reasoning=0.90, search=0.70, explain=0.90, test_gen=0.90,
    ),
    "claude-haiku": ModelCapabilities(
        code_gen=0.75, reasoning=0.70, search=0.60, explain=0.80, test_gen=0.70,
    ),
    "gpt-4o": ModelCapabilities(
        code_gen=0.90, reasoning=0.88, search=0.70, explain=0.88, test_gen=0.85,
    ),
    "gpt-4o-mini": ModelCapabilities(
        code_gen=0.72, reasoning=0.65, search=0.60, explain=0.78, test_gen=0.68,
    ),
    "gemini-2.5-pro": ModelCapabilities(
        code_gen=0.91, reasoning=0.92, search=0.80, explain=0.88, test_gen=0.85,
    ),
    "gemini-2.5-flash": ModelCapabilities(
        code_gen=0.80, reasoning=0.75, search=0.70, explain=0.82, test_gen=0.75,
    ),
    "gemini-flash-lite": ModelCapabilities(
        code_gen=0.60, reasoning=0.50, search=0.50, explain=0.70, test_gen=0.55,
    ),
    "sonar-pro": ModelCapabilities(
        code_gen=0.50, reasoning=0.70, search=0.95, explain=0.80, test_gen=0.40,
    ),
    "sonar": ModelCapabilities(
        code_gen=0.35, reasoning=0.50, search=0.90, explain=0.65, test_gen=0.30,
    ),
}

# Intent -> minimum quality floor for "premium" tasks (override quality_floor)
PREMIUM_INTENT_FLOORS: dict[str, float] = {
    "complex_code_gen": 0.90,
    "architecture": 0.90,
    "test_gen": 0.80,
}

# Default quality floor for intents not listed above
DEFAULT_QUALITY_FLOOR = 0.75


class ModelRouter:
    """Deterministic model routing: cheapest model meeting quality threshold.

    Usage:
        router = ModelRouter(
            enabled_models=["claude-sonnet", "gpt-4o-mini", "gemini-2.5-flash"],
            quality_floor=0.75,
        )
        decision = router.route("code_gen", estimated_input=10_000, estimated_output=4_000)
        print(decision.model, decision.estimated_cost_usd)
    """

    def __init__(
        self,
        enabled_models: Sequence[str] | None = None,
        quality_floor: float = DEFAULT_QUALITY_FLOOR,
        premium_intents: Sequence[str] | None = None,
    ) -> None:
        if enabled_models:
            self.enabled = [m for m in enabled_models if m in PROVIDERS]
        else:
            self.enabled = ["claude-sonnet"]  # safe default
        self.quality_floor = quality_floor
        self.premium_intents = set(premium_intents or PREMIUM_INTENT_FLOORS.keys())

    def route(
        self,
        intent: str,
        estimated_input: int = 0,
        estimated_output: int = 0,
    ) -> RoutingDecision:
        """Route to the cheapest enabled model that meets quality floor for *intent*.

        For premium intents (complex_code_gen, architecture), the quality floor
        is raised to the intent-specific minimum regardless of the configured floor.
        """
        floor = self.quality_floor
        if intent in self.premium_intents:
            floor = max(floor, PREMIUM_INTENT_FLOORS.get(intent, floor))

        # Score + cost for each enabled model
        candidates: list[tuple[str, float, float]] = []  # (model, score, cost)
        for model_name in self.enabled:
            caps = CAPABILITIES.get(model_name)
            if caps is None:
                continue
            score = caps.score_for(intent)
            if score < floor:
                continue
            # Check context window fits
            provider = PROVIDERS[model_name]
            if estimated_input > provider.context:
                continue
            cost = self.cost_for_model(model_name, estimated_input, estimated_output)
            candidates.append((model_name, score, cost))

        if not candidates:
            # No model meets the floor -- fall back to default
            default = self.enabled[0] if self.enabled else "claude-sonnet"
            cost = self.cost_for_model(default, estimated_input, estimated_output)
            return RoutingDecision(
                model=default,
                reason=f"no model meets {intent} >= {floor:.2f}, falling back to {default}",
                estimated_cost_usd=cost,
                alternative=None,
            )

        # Sort by cost ascending, then by score descending (tiebreaker)
        candidates.sort(key=lambda c: (c[2], -c[1]))
        best_name, best_score, best_cost = candidates[0]
        alt = candidates[1][0] if len(candidates) > 1 else None

        return RoutingDecision(
            model=best_name,
            reason=f"cheapest model meeting {intent} >= {floor:.2f} "
                   f"(score={best_score:.2f}, ${best_cost:.4f})",
            estimated_cost_usd=best_cost,
            alternative=alt,
        )

    def route_task(
        self,
        task_type: str,
        intent: str,
        estimated_input: int,
        estimated_output: int,
    ) -> RoutingDecision:
        """Convenience: route a build-plan task by type and intent."""
        return self.route(intent, estimated_input, estimated_output)

    def cost_for_model(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_hit_tokens: int = 0,
    ) -> float:
        """Calculate cost for a specific model given token counts."""
        provider = PROVIDERS.get(model)
        if provider is None:
            return 0.0

        non_cached_input = max(0, input_tokens - cache_hit_tokens)
        input_cost = (non_cached_input / 1_000_000) * provider.input
        output_cost = (output_tokens / 1_000_000) * provider.output

        cache_cost = 0.0
        if cache_hit_tokens > 0 and provider.cache_read is not None:
            cache_cost = (cache_hit_tokens / 1_000_000) * provider.cache_read

        return input_cost + output_cost + cache_cost

    def compare_models(
        self,
        intent: str,
        estimated_input: int,
        estimated_output: int,
    ) -> list[dict]:
        """Compare all enabled models for a given task -- useful for reports."""
        results = []
        for model_name in self.enabled:
            caps = CAPABILITIES.get(model_name)
            if caps is None:
                continue
            score = caps.score_for(intent)
            cost = self.cost_for_model(model_name, estimated_input, estimated_output)
            provider = PROVIDERS[model_name]
            results.append({
                "model": model_name,
                "provider": provider.provider,
                "score": round(score, 2),
                "cost_usd": round(cost, 4),
                "context": provider.context,
                "meets_floor": score >= self.quality_floor,
            })
        results.sort(key=lambda r: r["cost_usd"])
        return results

    def format_comparison(
        self,
        intent: str,
        estimated_input: int,
        estimated_output: int,
    ) -> str:
        """Format a model comparison table for CLI output."""
        results = self.compare_models(intent, estimated_input, estimated_output)
        lines = [
            f"MODEL COMPARISON (intent={intent}, "
            f"input={estimated_input:,}, output={estimated_output:,})",
            "=" * 70,
            f"  {'Model':<20} {'Provider':<12} {'Score':>6} {'Cost':>10} {'Floor':>6}",
            f"  {'-' * 62}",
        ]
        for r in results:
            flag = "YES" if r["meets_floor"] else "no"
            lines.append(
                f"  {r['model']:<20} {r['provider']:<12} {r['score']:>5.2f} "
                f"${r['cost_usd']:>9.4f} {flag:>6}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Backward-compatible PRICING dict -- used by optimizer.py and benchmark.py
# Maps old-style model aliases to provider pricing.
# ---------------------------------------------------------------------------

def get_pricing(model: str = "sonnet") -> dict[str, float]:
    """Return pricing dict for a model alias (backward compat with PRICING dict).

    Accepts both short names ("sonnet", "opus") and full names ("claude-sonnet").
    """
    alias_map = {
        "sonnet": "claude-sonnet",
        "opus": "claude-opus",
        "haiku": "claude-haiku",
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "gemini-pro": "gemini-2.5-pro",
        "gemini-flash": "gemini-2.5-flash",
        "gemini-flash-lite": "gemini-flash-lite",
        "sonar-pro": "sonar-pro",
        "sonar": "sonar",
    }
    full_name = alias_map.get(model, model)
    provider = PROVIDERS.get(full_name)
    if provider is None:
        provider = PROVIDERS["claude-sonnet"]

    return {
        "input": provider.input,
        "output": provider.output,
        "cache_read": provider.cache_read or 0.0,
        "cache_write": provider.cache_write or 0.0,
    }
