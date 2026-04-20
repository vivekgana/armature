# Project Budget Summary: monorepo
Generated: 2026-04-19T18:00:00+00:00 | Specs: 2 | Period: 2026-Q2

## All Specs Overview

```
Spec ID                    Complexity   Tokens     Cost    Requests   Status (tier)
------------------------------------------------------------------------------------
SPEC-2026-Q2-001 (auth)    high        448,000    $3.78         15   ON BUDGET (medium)
SPEC-2026-Q2-002 (gql)     low/spike   168,400    $0.85         11   OVER BUDGET (low)
------------------------------------------------------------------------------------
TOTAL                                  616,400    $4.63         26
```

## Budget Utilization by Spec

```
Spec                      Tier Used    Token Util   Cost Util    Headroom
--------------------------------------------------------------------------
SPEC-2026-Q2-001          medium       90%          38%          $6.22
SPEC-2026-Q2-002          low          168% ⚠       43%          $1.15
--------------------------------------------------------------------------
Project (medium tier)                  123%         46%
```

⚠ SPEC-002 exceeded low tier token cap (168,400 vs 100,000). Cost stayed within
budget ($0.85 vs $2.00). **Recommendation: use medium tier for all spike/research
workloads** regardless of declared priority.

## Phase Allocation Across Project

```
Phase           Tokens       Cost    % Tokens   Target %   Delta
-----------------------------------------------------------------
validate        22,700     $0.01       3.7%       5.0%     -1.3%
audit           61,200     $0.03       9.9%      10.0%     -0.1%
plan           103,500     $0.59      16.8%      15.0%     +1.8%
build          278,000     $3.18      45.1%      40.0%     +5.1% (!)
test           116,000     $0.70      18.8%      25.0%     -6.2% (!)
review          35,000     $0.13       5.7%       5.0%     +0.7%
-----------------------------------------------------------------
TOTAL          616,400     $4.63     100.0%
```

**(!)** Build phase at 45.1% (target 40%) — driven by SPEC-001's cross-service
integration complexity (3 packages, JWT + Celery patterns).

**(!)** Test phase at 18.8% (target 25%) — SPEC-002 spike had 0% test target
(eval.unit_test_coverage_min=0), pulling down the project average. SPEC-001 alone
was at 22.8% test allocation.

## Cost Trend

```
Spec                        Date         Tokens      Cost    Cost/1K Tokens
---------------------------------------------------------------------------
SPEC-2026-Q2-001 (auth)     Apr 16       448,000     $3.78       $8.44
SPEC-2026-Q2-002 (gql)      Apr 18       168,400     $0.85       $5.05
---------------------------------------------------------------------------
Trend                                                             -40.2%
```

Cost per 1K tokens dropped 40% — the spike used no opus and leveraged Perplexity's
sonar-pro for research (cheaper than sonnet for information retrieval).

## Model Distribution

```
Model              Requests   Tokens     Cost    % Cost   Avg Latency
----------------------------------------------------------------------
claude-haiku              7     99,900    $0.04     0.9%     1,669ms
claude-sonnet            15    437,000    $2.73    59.0%     5,264ms
claude-opus               2     51,000    $1.79    38.7%    10,925ms
sonar-pro                 2     29,500    $0.08     1.7%     2,815ms
----------------------------------------------------------------------
TOTAL                    26    616,400    $4.63   100.0%
```

- **opus** (8% of requests, 39% of cost): JWT RS256/HS256 architecture + cross-service
  integration. High cost justified — these were the two most architecturally complex
  decisions across all three example projects.
- **sonnet** (58% of requests, 59% of cost): primary build/test workhorse
- **haiku** (27% of requests, <1% of cost): lightweight validation/audit/review phases
- **sonar-pro** (8% of requests, 2% of cost): Perplexity research queries for spike —
  demonstrates multi-provider routing for information retrieval

## Cache Performance

```
Metric                    SPEC-001     SPEC-002     Project
------------------------------------------------------------
Prompt cache hit rate     47% (7/15)   0% (0/11)    27% (7/26)
Tokens saved by cache     80,000       0            80,000
Semantic cache hits       0            1            1
```

- SPEC-001: strong prompt caching (47%) across multi-request build phase
- SPEC-002: no prompt cache hits, but 1 semantic cache hit saved 16,000 tokens
  (build-3 reused benchmark query from plan-2)

## Multi-Provider Analysis

```
Provider       Requests   Tokens     Cost    Use Case
------------------------------------------------------
Anthropic            24    587,900    $4.55   Code generation, testing, review
Perplexity            2     29,500    $0.08   Research/information retrieval
------------------------------------------------------
```

Perplexity sonar-pro used for 2 spike research queries at 1.7% of total cost.
Cost-effective for broad ecosystem surveys and benchmark comparisons where
up-to-date web knowledge matters more than code generation quality.

## Optimization Suggestions

1. **Use medium tier for spikes.** SPEC-002 proved that even low-priority spike
   workloads exceed the low tier token cap. Research queries are inherently
   token-heavy. Set `min_tier: medium` for spike type in budget config.
2. **Monitor cross-service specs at medium tier.** SPEC-001 hit 90% of medium tier
   token cap. Future specs touching 3+ packages may need high tier.
3. **Opus usage is justified but expensive.** 2 opus requests consumed 39% of total
   cost. The router's `complex_code_gen` intent correctly escalated — validate that
   the quality difference warrants the 10x cost premium on a case-by-case basis.
4. **Expand multi-provider routing.** sonar-pro at $0.08 for 2 research queries vs
   ~$0.45 if sonnet had been used. Route all `research` and `ecosystem_survey`
   intents to sonar-pro.
5. **Adjust test phase target for mixed workloads.** The 25% test target assumes all
   specs require testing. When spikes (0% test target) are included, the project
   average will always appear under-allocated. Consider per-type phase targets.
