# Budget Report: SPEC-2026-Q2-001 — Add user authentication endpoint
Generated: 2026-04-15T15:00:00+00:00 | Complexity: high

```
Phase           Tokens       Cost    % Total   Requests
-------------------------------------------------------
validate        15,500     $0.01       4.1%          1
audit           37,500     $0.02      10.0%          2
plan            52,500     $0.29      14.0%          2
build          164,000     $1.72      43.6%          5
test            93,000     $0.55      24.7%          3
review          13,500     $0.01       3.6%          1
-------------------------------------------------------
TOTAL          376,000     $2.58     100.0%         14
```

## Budget Comparison

```
Tier         Tokens Used / Cap          Cost / Cap             Status
------------------------------------------------------------------------
low          376,000 / 100,000 (376%)   $2.58 / $2.00 (129%)  OVER BUDGET
medium       376,000 / 500,000 (75%)    $2.58 / $10.00 (26%)  ON BUDGET
high         376,000 / 1,000,000 (38%)  $2.58 / $20.00 (13%)  ON BUDGET
critical     376,000 / 2,000,000 (19%)  $2.58 / $40.00 (6%)   ON BUDGET
```

## Provider Breakdown

```
Provider         Requests     Tokens       Cost   Avg Latency
-----------------------------------------------------------------
anthropic              14    376,000     $2.58       4,899ms
  claude-haiku           4     66,500     $0.03       1,875ms
  claude-sonnet          9    286,500     $1.73       5,405ms
  claude-opus            1     23,000     $0.83       9,450ms
```

## Cache Performance

- Prompt cache hits: 6/14 requests (43%)
- Tokens saved by cache: 62,000
- Semantic cache hits: 1 (test-3 reused test scaffolding from test-1)

## Notes

- build-5-arch used claude-opus for JWT RS256/HS256 token architecture (complex_code_gen intent)
- All phases within expected allocation (no flags)
- Recommended tier: **medium** (75% token utilization, 26% cost utilization)
