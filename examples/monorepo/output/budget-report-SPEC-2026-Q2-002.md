# Budget Report: SPEC-2026-Q2-002 — Investigate GraphQL gateway
Generated: 2026-04-18T14:00:00+00:00 | Complexity: low (spike)

```
Phase           Tokens       Cost    % Total   Requests
-------------------------------------------------------
validate         4,700     $0.00       2.8%          1
audit           17,700     $0.01      10.5%          2
plan            42,000     $0.26      24.9% (!)      3
build           71,000     $0.37      42.2%          3
test            14,000     $0.09       8.3%          1
review          19,000     $0.12      11.3%          1
-------------------------------------------------------
TOTAL          168,400     $0.85     100.0%         11
```

## Budget Comparison

```
Tier         Tokens Used / Cap            Cost / Cap              Status
--------------------------------------------------------------------------
low          168,400 / 100,000 (168%)     $0.85 / $2.00 (43%)    OVER BUDGET (tokens)
medium       168,400 / 500,000 (34%)      $0.85 / $10.00 (9%)    ON BUDGET
high         168,400 / 1,000,000 (17%)    $0.85 / $20.00 (4%)    ON BUDGET
critical     168,400 / 2,000,000 (8%)     $0.85 / $40.00 (2%)    ON BUDGET
```

## Optimization Suggestions

- **(!)** Phase 'plan' using 24.9% of tokens (expected ~15%). Spike workloads are
  research-heavy by nature. Consider raising plan allocation in spike template to 25%.
- Spike matched LOW priority but consumed 168,400 tokens vs low tier cap (100,000).
  **Recommend using medium tier for spikes regardless of priority** — research queries
  are token-heavy.

## Provider Breakdown

```
Provider         Requests     Tokens       Cost   Avg Latency
-----------------------------------------------------------------
anthropic               9    139,900     $0.76       3,590ms
  claude-haiku           3     22,400     $0.01       1,203ms
  claude-sonnet          6    117,500     $0.75       4,470ms
perplexity              2     29,500     $0.08       2,815ms
  sonar-pro              2     29,500     $0.08       2,815ms
```

## Cache Performance

- Prompt cache hits: 0/11 requests
- Semantic cache hits: 1 (build-3 reused benchmark query from plan-2; 16,000 tokens saved)

## Notes

- sonar-pro (Perplexity) used for 2 research queries: GraphQL ecosystem survey and REST vs GraphQL benchmarks
- build-3 semantic cache hit: identical benchmark query to plan-2, zero cost
- Test phase light (8.3% vs 25% target): eval.unit_test_coverage_min=0 for spike type
- Review phase heavier than usual (11.3% vs 5%): spike decision doc required thorough review
- Outcome: **NO-GO recommendation** for GraphQL gateway (latency overhead unacceptable)
