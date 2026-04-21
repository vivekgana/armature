# Project Budget Summary: typescript-nextjs
Generated: 2026-04-18T18:00:00+00:00 | Specs: 2 | Period: 2026-Q2

## All Specs Overview

```
Spec ID                    Complexity   Tokens     Cost    Requests   Status (tier)
------------------------------------------------------------------------------------
SPEC-2026-Q2-001 (dark)    medium      198,000    $1.04         11   ON BUDGET (medium)
SPEC-2026-Q2-002 (mw)      medium      219,100    $1.17         11   ON BUDGET (medium)
------------------------------------------------------------------------------------
TOTAL                                  417,100    $2.21         22
```

## Budget Utilization by Spec

```
Spec                      Tier Used    Token Util   Cost Util    Headroom
--------------------------------------------------------------------------
SPEC-2026-Q2-001          medium       40%          10%          $8.96
SPEC-2026-Q2-002          medium       44%          12%          $8.83
--------------------------------------------------------------------------
Weighted Avg                           42%          11%
```

Both specs well within medium tier — consistent utilization across similar complexity levels.

## Phase Allocation Across Project

```
Phase           Tokens       Cost    % Tokens   Target %   Delta
-----------------------------------------------------------------
validate        11,800     $0.00       2.8%       5.0%     -2.2%
audit           42,800     $0.02      10.3%      10.0%     +0.3%
plan            77,000     $0.44      18.5%      15.0%     +3.5% (!)
build          165,000     $1.08      39.5%      40.0%     -0.5%
test           100,000     $0.66      24.0%      25.0%     -1.0%
review          20,500     $0.00       4.9%       5.0%     -0.1%
-----------------------------------------------------------------
TOTAL          417,100     $2.21     100.0%
```

**(!)** Plan phase at 18.5% vs 15% target across both specs. Frontend component
architecture (CSS custom properties, middleware composability) requires more upfront
design than typical backend work.

## Cost Trend

```
Spec                        Date         Tokens      Cost    Cost/1K Tokens
---------------------------------------------------------------------------
SPEC-2026-Q2-001 (dark)     Apr 17       198,000     $1.04       $5.25
SPEC-2026-Q2-002 (mw)       Apr 17       219,100     $1.17       $5.34
---------------------------------------------------------------------------
Trend                                                             +1.7%
```

Cost per 1K tokens nearly identical — both specs used the same model mix (sonnet+haiku),
confirming consistent routing for medium-complexity frontend work.

## Model Distribution

```
Model              Requests   Tokens     Cost    % Cost   Avg Latency
----------------------------------------------------------------------
claude-haiku              7     74,100    $0.03     1.4%     1,344ms
claude-sonnet            15    343,000    $2.17    98.2%     4,998ms
----------------------------------------------------------------------
TOTAL                    22    417,100    $2.21   100.0%
```

- **No opus usage.** Frontend UI/CSS work and middleware refactoring stayed within
  sonnet's quality floor — no complex architecture decisions requiring opus escalation.
- **haiku** (32% of requests): validate, audit, and review phases
- **sonnet** (68% of requests): build and test phases

## Cache Performance

```
Metric                    SPEC-001     SPEC-002     Project
------------------------------------------------------------
Prompt cache hit rate     45% (5/11)   45% (5/11)   45% (10/22)
Tokens saved by cache     41,000       47,000       88,000
Semantic cache hits       0            0            0
```

Consistent 45% cache hit rate across both specs. No semantic cache opportunities
identified — each spec had distinct implementation patterns.

## Optimization Suggestions

1. **Plan phase consistently over target.** Both specs at ~18.5% plan allocation.
   Consider raising the plan budget to 18% for frontend/Next.js specs — component
   architecture decisions benefit from more upfront design tokens.
2. **Medium tier has significant headroom.** Both specs under 44% token utilization.
   If future frontend specs are similarly scoped, a "medium-light" tier (300K tokens,
   $6.00) could provide tighter budget tracking.
3. **No opus needed for frontend work.** CSS custom properties, React components, and
   Next.js middleware all resolved within sonnet's capabilities. This pattern should
   hold for typical frontend features.
4. **Cache performance is healthy** at 45%. The consistent hit rate suggests the
   conversation structure is well-suited for prompt caching.
