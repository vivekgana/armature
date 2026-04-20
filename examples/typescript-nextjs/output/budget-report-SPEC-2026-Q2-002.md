# Budget Report: SPEC-2026-Q2-002 — Refactor API routes to use middleware
Generated: 2026-04-17T17:30:00+00:00 | Complexity: medium

```
Phase           Tokens       Cost    % Total   Requests
-------------------------------------------------------
validate         6,300     $0.00       2.9%          1
audit           22,800     $0.01      10.4%          2
plan            40,500     $0.23      18.5%          2
build           87,000     $0.58      39.7%          3
test            51,500     $0.35      23.5%          2
review          11,000     $0.00       5.0%          1
-------------------------------------------------------
TOTAL          219,100     $1.17     100.0%         11
```

## Budget Comparison

```
Tier         Tokens Used / Cap          Cost / Cap             Status
------------------------------------------------------------------------
low          219,100 / 100,000 (219%)   $1.17 / $2.00 (59%)   OVER BUDGET (tokens)
medium       219,100 / 500,000 (44%)    $1.17 / $10.00 (12%)  ON BUDGET
high         219,100 / 1,000,000 (22%)  $1.17 / $20.00 (6%)   ON BUDGET
critical     219,100 / 2,000,000 (11%)  $1.17 / $40.00 (3%)   ON BUDGET
```

## Provider Breakdown

```
Provider         Requests     Tokens       Cost   Avg Latency
-----------------------------------------------------------------
anthropic              11    219,100     $1.17       3,819ms
  claude-haiku           3     29,100     $0.01       1,390ms
  claude-sonnet          8    190,000     $1.15       5,190ms
```

## Cache Performance

- Prompt cache hits: 5/11 requests (45%)
- Tokens saved by cache: 47,000

## Notes

- plan-1 used complex_code_gen intent (middleware composability required upfront architecture)
- Plan phase slightly over target (18.5% vs 15%) but below flag threshold
- Middleware refactor drove slightly more tokens than dark mode feature (219K vs 198K)
- Recommended tier: **medium** (44% token utilization)
