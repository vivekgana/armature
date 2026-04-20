# Budget Report: SPEC-2026-Q2-001 — Add shared auth middleware package
Generated: 2026-04-16T16:00:00+00:00 | Complexity: high

```
Phase           Tokens       Cost    % Total   Requests
-------------------------------------------------------
validate        18,000     $0.01       4.4%          1
audit           43,500     $0.02      10.6%          2
plan            61,500     $0.33      15.0%          2
build          207,000     $2.81      50.6%          6
test           102,000     $0.61      24.9%          3
review          16,000     $0.01       3.9%          1
-------------------------------------------------------
TOTAL          448,000     $3.78     100.0%         15
```

## Budget Comparison

```
Tier         Tokens Used / Cap            Cost / Cap              Status
--------------------------------------------------------------------------
low          448,000 / 100,000 (448%)     $3.78 / $2.00 (189%)   OVER BUDGET
medium       448,000 / 500,000 (90%)      $3.78 / $10.00 (38%)   ON BUDGET
high         448,000 / 1,000,000 (45%)    $3.78 / $20.00 (19%)   ON BUDGET
critical     448,000 / 2,000,000 (22%)    $3.78 / $40.00 (9%)    ON BUDGET
```

## Provider Breakdown

```
Provider         Requests     Tokens       Cost   Avg Latency
-----------------------------------------------------------------
anthropic              15    448,000     $3.78       5,907ms
  claude-haiku           4     77,500     $0.03       2,135ms
  claude-sonnet          9    319,500     $1.98       6,140ms
  claude-opus            2     51,000     $1.79      10,925ms
```

## Cache Performance

- Prompt cache hits: 7/15 requests (47%)
- Tokens saved by cache: 80,000

## Notes

- build-5-jwt used claude-opus: JWT RS256/HS256 dual-algorithm implementation
- build-6-integ used claude-opus: cross-service integration (FastAPI + Celery patterns)
- Most complex spec across all projects — cross-service auth with 3 packages
- Medium tier at 90% token utilization — monitor for future cross-service specs
- Recommended tier: **medium** (90% utilization, consider high for similar scopes)
