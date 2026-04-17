"""Budget reporting -- cost analysis, provider breakdown, and anomaly detection."""

from __future__ import annotations

import statistics

from armature._internal.output import console
from armature.budget.tracker import SessionTracker
from armature.config.schema import BudgetConfig


def generate_report(tracker: SessionTracker, spec_id: str, config: BudgetConfig) -> None:
    """Generate and print a budget report for a spec."""
    usage = tracker.get_usage(spec_id)

    if usage["requests"] == 0:
        console.print(f"  No cost data found for {spec_id}")
        return

    total_tokens = usage["total_tokens"]
    total_cost = usage["total_cost_usd"]

    # Phase breakdown
    console.print(f"\n  {'Phase':<15} {'Tokens':>10} {'Cost':>10} {'% Total':>10} {'Requests':>10}")
    console.print(f"  {'-' * 55}")

    allocation = config.phase_allocation
    for phase in ["validate", "audit", "plan", "build", "test", "review"]:
        if phase in usage["phases"]:
            p = usage["phases"][phase]
            pct = (p["tokens"] / total_tokens * 100) if total_tokens > 0 else 0
            expected_pct = allocation.get(phase, 0)
            flag = " (!)" if expected_pct > 0 and pct > expected_pct * 1.5 else ""
            console.print(
                f"  {phase:<15} {p['tokens']:>10,} ${p['cost_usd']:>9.2f} "
                f"{pct:>8.1f}%{flag} {p['requests']:>10}"
            )

    console.print(f"  {'-' * 55}")
    console.print(f"  {'TOTAL':<15} {total_tokens:>10,} ${total_cost:>9.2f}")

    # Budget comparison
    for tier_name, tier in config.defaults.items():
        token_pct = (total_tokens / tier.max_tokens) * 100 if tier.max_tokens > 0 else 0
        cost_pct = (total_cost / tier.max_cost_usd) * 100 if tier.max_cost_usd > 0 else 0
        status = "[green]ON BUDGET[/green]" if token_pct <= 100 and cost_pct <= 100 else "[red]OVER BUDGET[/red]"
        console.print(
            f"\n  Budget ({tier_name}): {total_tokens:,}/{tier.max_tokens:,} tokens "
            f"({token_pct:.0f}%) | ${total_cost:.2f}/${tier.max_cost_usd:.2f} ({cost_pct:.0f}%) -- {status}"
        )

    # Optimization suggestions
    suggestions = tracker.get_optimization_suggestions(spec_id)
    if suggestions:
        console.print(f"\n  [yellow]Optimization suggestions:[/yellow]")
        for s in suggestions:
            console.print(f"    - {s}")


def generate_provider_report(
    tracker: SessionTracker, spec_id: str, config: BudgetConfig,
) -> None:
    """Generate per-provider cost breakdown with anomaly detection."""
    provider_usage = tracker.get_usage_by_provider(spec_id)
    cache_stats = tracker.get_semantic_cache_stats(spec_id)

    if not provider_usage:
        console.print(f"  No provider data for {spec_id}")
        return

    console.print(f"\n  PROVIDER BREAKDOWN: {spec_id}")
    console.print(f"  {'='*65}")
    console.print(
        f"  {'Provider':<16} {'Requests':>8} {'Tokens':>10} "
        f"{'Cost':>10} {'Avg Latency':>12}"
    )
    console.print(f"  {'-'*65}")

    total_tokens = 0
    total_cost = 0.0
    total_requests = 0

    for prov, data in sorted(provider_usage.items()):
        avg_latency = (
            f"{data['latency_ms_total'] / data['requests']:.0f}ms"
            if data["requests"] > 0 and data["latency_ms_total"] > 0
            else "n/a"
        )
        console.print(
            f"  {prov:<16} {data['requests']:>8} {data['tokens']:>10,} "
            f"${data['cost_usd']:>9.2f} {avg_latency:>12}"
        )
        total_tokens += data["tokens"]
        total_cost += data["cost_usd"]
        total_requests += data["requests"]

        # Show per-model breakdown within provider
        for model, mdata in sorted(data.get("models", {}).items()):
            console.print(
                f"    {model:<14} {mdata['requests']:>8} {mdata['tokens']:>10,} "
                f"${mdata['cost_usd']:>9.2f}"
            )

    # Semantic cache line
    if cache_stats["cache_hits"] > 0:
        console.print(
            f"  {'[cache]':<16} {cache_stats['cache_hits']:>8} "
            f"{cache_stats['tokens_saved']:>10,} ${'0.00':>9} {'0ms':>12}"
        )

    console.print(f"  {'-'*65}")
    console.print(
        f"  {'TOTAL':<16} {total_requests:>8} {total_tokens:>10,} "
        f"${total_cost:>9.2f}"
    )

    # Cache summary
    if cache_stats["total_requests"] > 0:
        console.print(
            f"\n  Cache: {cache_stats['cache_hits']}/{cache_stats['total_requests']} "
            f"hits ({cache_stats['hit_rate']:.0%}), "
            f"{cache_stats['tokens_saved']:,} tokens saved"
        )

    # Anomaly detection
    anomalies = detect_anomalies(tracker, spec_id, config.monitoring.anomaly_threshold)
    if anomalies:
        console.print(f"\n  [yellow]Anomalies detected:[/yellow]")
        for a in anomalies:
            console.print(f"    [!] {a}")


def generate_trend_report(tracker: SessionTracker, limit: int = 10) -> None:
    """Generate cross-spec cost trend report."""
    trends = tracker.get_cross_spec_trends(limit)
    if not trends:
        console.print("  No spec data available for trends.")
        return

    console.print(f"\n  COST TRENDS (last {len(trends)} specs)")
    console.print(f"  {'='*70}")
    console.print(
        f"  {'Spec':<25} {'Tasks':>6} {'Cost':>8} {'Cache%':>8} {'Models':>7}"
    )
    console.print(f"  {'-'*70}")

    for t in trends:
        console.print(
            f"  {t['spec_id']:<25} {t['requests']:>6} "
            f"${t['total_cost_usd']:>7.2f} "
            f"{t['cache_hit_rate']:>7.0%} {t['models_used']:>7}"
        )

    # Show trend direction
    if len(trends) >= 2:
        first_cost = trends[0]["total_cost_usd"]
        last_cost = trends[-1]["total_cost_usd"]
        if first_cost > 0:
            change = ((last_cost - first_cost) / first_cost) * 100
            direction = "down" if change < 0 else "up"
            console.print(
                f"\n  Trend: {abs(change):.0f}% {direction} over {len(trends)} specs"
            )


def detect_anomalies(
    tracker: SessionTracker, spec_id: str, threshold: float = 3.0,
) -> list[str]:
    """Detect cost anomalies: tasks costing >threshold× the average for their intent."""
    intent_usage = tracker.get_usage_by_intent(spec_id)
    anomalies: list[str] = []

    for intent, data in intent_usage.items():
        if data["requests"] < 2:
            continue
        costs = data["costs"]
        avg = statistics.mean(costs)
        if avg <= 0:
            continue
        for i, cost in enumerate(costs):
            if cost > avg * threshold:
                anomalies.append(
                    f"Request {i+1} for '{intent}' cost ${cost:.4f} "
                    f"({cost/avg:.1f}x average ${avg:.4f})"
                )

    return anomalies
