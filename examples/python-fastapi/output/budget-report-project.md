# Project Budget Summary: python-fastapi
Generated: 2026-04-18T18:00:00+00:00 | Specs: 2 | Period: 2026-Q2

## All Specs Overview

```
Spec ID                  Complexity   Tokens     Cost    Requests   Status (tier)
----------------------------------------------------------------------------------
SPEC-2026-Q2-001 (auth)  high        376,000    $2.58         14   ON BUDGET (medium)
SPEC-2026-Q2-002 (pag.)  medium       74,700    $0.27          6   ON BUDGET (low)
----------------------------------------------------------------------------------
TOTAL                                450,700    $2.85         20
```

## Budget Utilization by Spec

```
Spec                      Tier Used    Token Util   Cost Util    Headroom
--------------------------------------------------------------------------
SPEC-2026-Q2-001          medium       75%          26%          $7.42
SPEC-2026-Q2-002          low          75%          14%          $1.73
--------------------------------------------------------------------------
Weighted Avg                           75%          24%
```

## Phase Allocation Across Project

```
Phase           Tokens       Cost    % Tokens   Target %   Delta
-----------------------------------------------------------------
validate        20,200     $0.01       4.5%       5.0%     -0.5%
audit           46,000     $0.02      10.2%      10.0%     +0.2%
plan            65,500     $0.30      14.5%      15.0%     -0.5%
build          188,000     $1.86      41.7%      40.0%     +1.7%
test           113,000     $0.66      25.1%      25.0%     +0.1%
review          18,000     $0.01       4.0%       5.0%     -1.0%
-----------------------------------------------------------------
TOTAL          450,700     $2.85     100.0%
```

All phases within target allocation — no flags triggered.

## Cost Trend

```
Spec                        Date         Tokens      Cost    Cost/1K Tokens
---------------------------------------------------------------------------
SPEC-2026-Q2-001 (auth)     Apr 15       376,000     $2.58       $6.86
SPEC-2026-Q2-002 (pag.)     Apr 16        74,700     $0.27       $3.61
---------------------------------------------------------------------------
Trend                                                             -47.3%
```

Cost per 1K tokens dropped 47% — the bugfix used cheaper models (no opus), showing
effective model routing for simpler tasks.

## Model Distribution

```
Model              Requests   Tokens     Cost    % Cost   Avg Latency
----------------------------------------------------------------------
claude-haiku              8     97,200    $0.04     1.4%     1,590ms
claude-sonnet            11    330,500    $1.99    69.8%     5,047ms
claude-opus               1     23,000    $0.83    29.1%     9,450ms
----------------------------------------------------------------------
TOTAL                    20    450,700    $2.85   100.0%
```

- **haiku** (40% of requests): validate, audit, review phases + simple bugfix phases
- **sonnet** (55% of requests): build and test phases — primary workhorse
- **opus** (5% of requests): JWT architecture decision only — used sparingly for high-value tasks

## Cache Performance

```
Metric                    SPEC-001     SPEC-002     Project
------------------------------------------------------------
Prompt cache hit rate     43% (6/14)   0% (0/6)     30% (6/20)
Tokens saved by cache     62,000       0            62,000
Semantic cache hits       1            0            1
```

Prompt caching effective for multi-request specs. Single-request-per-phase specs
(SPEC-002) don't benefit from prompt caching.

## Optimization Suggestions

1. **Model routing is well-calibrated.** Opus used only once (JWT architecture) — cost
   justified by complexity. Haiku handles low-complexity phases effectively.
2. **Consider low tier for scoped bugfixes.** SPEC-002 used only 75% of low tier —
   well-scoped bugs don't need medium tier overhead.
3. **Prompt caching opportunity.** SPEC-002 had 0% cache hits. For future bugfix specs,
   consider batching validate+audit into a single context to enable caching.
4. **Phase allocation is healthy.** All phases within 2% of target — no rebalancing needed.
