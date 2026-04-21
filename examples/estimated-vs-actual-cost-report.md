# Estimated vs Actual Cost Report: All Examples — 2026-Q2
Generated: 2026-04-20T00:00:00+00:00 | Projects: 3 | Specs: 6

---

## Executive Summary

```
                     Estimated (Tier Cap)              Actual                   Savings
                     ─────────────────────   ─────────────────────   ─────────────────────
Project              Tokens      Cost        Tokens      Cost        Tokens      Cost
─────────────────────────────────────────────────────────────────────────────────────────
python-fastapi        600,000    $12.00       450,700     $2.85       149,300     $9.15
typescript-nextjs   1,000,000    $20.00       417,100     $2.21       582,900    $17.79
monorepo              600,000    $12.00       616,400     $4.63       -16,400     $7.37
─────────────────────────────────────────────────────────────────────────────────────────
TOTAL               2,200,000    $44.00     1,484,200    $10.69       715,800    $33.31
```

**Overall: 67% token utilization, 24% cost utilization — $33.31 under budget.**

monorepo exceeded its combined token estimate by 16,400 tokens (SPEC-002 spike overran
the low tier cap), but stayed $7.37 under the combined cost cap.

---

## Project 1: python-fastapi

### Estimated vs Actual — Summary

```
                          Estimated          Actual           Variance
                     ────────────────   ────────────────   ────────────────
Metric               Tokens    Cost     Tokens    Cost     Tokens    Cost
──────────────────────────────────────────────────────────────────────────
SPEC-001 (auth)      500,000   $10.00   376,000   $2.58   -124,000   -$7.42
SPEC-002 (bugfix)    100,000    $2.00    74,700   $0.27    -25,300   -$1.73
──────────────────────────────────────────────────────────────────────────
PROJECT TOTAL        600,000   $12.00   450,700   $2.85   -149,300   -$9.15
```

```
Token Utilization:  ████████████████████████░░░░░░░░░░  75%  (450,700 / 600,000)
Cost Utilization:   ████████░░░░░░░░░░░░░░░░░░░░░░░░░░  24%  ($2.85 / $12.00)
```

### Estimated vs Actual — By Phase

```
Phase      Est. Token %   Est. Tokens   Actual Tokens   Variance     Est. Cost   Actual Cost   Variance
────────────────────────────────────────────────────────────────────────────────────────────────────────
validate        5.0%         22,535         20,200        -2,335       $0.60        $0.01        -$0.59
audit          10.0%         45,070         46,000        +  930       $1.20        $0.02        -$1.18
plan           15.0%         67,605         65,500        -2,105       $1.80        $0.30        -$1.50
build          40.0%        180,280        188,000        +7,720       $4.80        $1.86        -$2.94
test           25.0%        112,675        113,000        +  325       $3.00        $0.66        -$2.34
review          5.0%         22,535         18,000        -4,535       $0.60        $0.01        -$0.59
────────────────────────────────────────────────────────────────────────────────────────────────────────
TOTAL         100.0%        450,700        450,700             0      $12.00        $2.85        -$9.15
```

*Est. Tokens = Actual Total × Target %. Est. Cost = Tier Cap × Target %.*

### Estimated vs Actual — By Spec

**SPEC-2026-Q2-001 — Add user authentication endpoint** (Tier: medium)

```
                Estimated (medium tier)     Actual              Status
                ────────────────────────   ────────────────   ──────────
Tokens              500,000                  376,000  (75%)   ON BUDGET
Cost                $10.00                    $2.58  (26%)    ON BUDGET
Requests            ~15                       14              —
Model mix           sonnet-heavy             9 sonnet, 4 haiku, 1 opus
```

**SPEC-2026-Q2-002 — Fix pagination off-by-one** (Tier: low)

```
                Estimated (low tier)        Actual              Status
                ────────────────────────   ────────────────   ──────────
Tokens              100,000                   74,700  (75%)   ON BUDGET
Cost                 $2.00                     $0.27  (14%)   ON BUDGET
Requests            ~8                         6              —
Model mix           sonnet-heavy             2 sonnet, 4 haiku
```

### python-fastapi Key Insight

Cost utilization (24%) is far below token utilization (75%) because haiku handled 8 of
20 requests at $0.38/1K tokens vs the blended $7.20/1K rate assumed by tier pricing.
The tier caps over-estimate cost for projects with good model routing.

---

## Project 2: typescript-nextjs

### Estimated vs Actual — Summary

```
                          Estimated          Actual           Variance
                     ────────────────   ────────────────   ────────────────
Metric               Tokens    Cost     Tokens    Cost     Tokens    Cost
──────────────────────────────────────────────────────────────────────────
SPEC-001 (dark mode) 500,000   $10.00   198,000   $1.04   -302,000   -$8.96
SPEC-002 (middleware)500,000   $10.00   219,100   $1.17   -280,900   -$8.83
──────────────────────────────────────────────────────────────────────────
PROJECT TOTAL      1,000,000   $20.00   417,100   $2.21   -582,900  -$17.79
```

```
Token Utilization:  ██████████████░░░░░░░░░░░░░░░░░░░░  42%  (417,100 / 1,000,000)
Cost Utilization:   ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  11%  ($2.21 / $20.00)
```

### Estimated vs Actual — By Phase

```
Phase      Est. Token %   Est. Tokens   Actual Tokens   Variance     Est. Cost   Actual Cost   Variance
────────────────────────────────────────────────────────────────────────────────────────────────────────
validate        5.0%         20,855         11,800        -9,055       $1.00        $0.00        -$1.00
audit          10.0%         41,710         42,800        +1,090       $2.00        $0.02        -$1.98
plan           15.0%         62,565         77,000       +14,435       $3.00        $0.44        -$2.56
build          40.0%        166,840        165,000        -1,840       $8.00        $1.08        -$6.92
test           25.0%        104,275        100,000        -4,275       $5.00        $0.66        -$4.34
review          5.0%         20,855         20,500        -  355       $1.00        $0.00        -$1.00
────────────────────────────────────────────────────────────────────────────────────────────────────────
TOTAL         100.0%        417,100        417,100             0      $20.00        $2.21       -$17.79
```

### Estimated vs Actual — By Spec

**SPEC-2026-Q2-001 — Add dark mode toggle component** (Tier: medium)

```
                Estimated (medium tier)     Actual              Status
                ────────────────────────   ────────────────   ──────────
Tokens              500,000                  198,000  (40%)   ON BUDGET
Cost                $10.00                    $1.04  (10%)    ON BUDGET
Requests            ~12                       11              —
Model mix           sonnet-heavy             7 sonnet, 4 haiku
```

**SPEC-2026-Q2-002 — Refactor API routes to use middleware** (Tier: medium)

```
                Estimated (medium tier)     Actual              Status
                ────────────────────────   ────────────────   ──────────
Tokens              500,000                  219,100  (44%)   ON BUDGET
Cost                $10.00                    $1.17  (12%)    ON BUDGET
Requests            ~12                       11              —
Model mix           sonnet-heavy             8 sonnet, 3 haiku
```

### typescript-nextjs Key Insight

Both specs used only 40-44% of their medium tier token cap — the most over-provisioned
project. No opus was needed for frontend work (CSS custom properties, middleware
composability stayed within sonnet's quality floor). **A "medium-light" tier (300K tokens,
$6.00) would fit both specs with ~70% utilization**, providing tighter budget tracking.

---

## Project 3: monorepo

### Estimated vs Actual — Summary

```
                          Estimated          Actual           Variance
                     ────────────────   ────────────────   ────────────────
Metric               Tokens    Cost     Tokens    Cost     Tokens    Cost
──────────────────────────────────────────────────────────────────────────
SPEC-001 (auth pkg)  500,000   $10.00   448,000   $3.78    -52,000   -$6.22
SPEC-002 (gql spike) 100,000    $2.00   168,400   $0.85    +68,400   -$1.15
──────────────────────────────────────────────────────────────────────────
PROJECT TOTAL        600,000   $12.00   616,400   $4.63    +16,400   -$7.37
```

```
Token Utilization:  ██████████████████████████████████ 103%  (616,400 / 600,000) ⚠
Cost Utilization:   █████████████░░░░░░░░░░░░░░░░░░░░░  39%  ($4.63 / $12.00)
```

⚠ Token over-budget driven entirely by SPEC-002 spike (+68,400 tokens over low tier cap).
Cost stayed 61% under budget.

### Estimated vs Actual — By Phase

```
Phase      Est. Token %   Est. Tokens   Actual Tokens   Variance     Est. Cost   Actual Cost   Variance
────────────────────────────────────────────────────────────────────────────────────────────────────────
validate        5.0%         30,820         22,700        -8,120       $0.60        $0.01        -$0.59
audit          10.0%         61,640         61,200        -  440       $1.20        $0.03        -$1.17
plan           15.0%         92,460        103,500       +11,040       $1.80        $0.59        -$1.21
build          40.0%        246,560        278,000       +31,440       $4.80        $3.18        -$1.62
test           25.0%        154,100        116,000       -38,100       $3.00        $0.70        -$2.30
review          5.0%         30,820         35,000        +4,180       $0.60        $0.13        -$0.47
────────────────────────────────────────────────────────────────────────────────────────────────────────
TOTAL         100.0%        616,400        616,400             0      $12.00        $4.63        -$7.37
```

### Estimated vs Actual — By Spec

**SPEC-2026-Q2-001 — Add shared auth middleware package** (Tier: medium)

```
                Estimated (medium tier)     Actual              Status
                ────────────────────────   ────────────────   ──────────
Tokens              500,000                  448,000  (90%)   ON BUDGET
Cost                $10.00                    $3.78  (38%)    ON BUDGET
Requests            ~15                       15              —
Model mix           sonnet-heavy             9 sonnet, 4 haiku, 2 opus
```

**SPEC-2026-Q2-002 — Investigate GraphQL gateway** (Tier: low)

```
                Estimated (low tier)        Actual              Status
                ────────────────────────   ────────────────   ──────────
Tokens              100,000                  168,400 (168%)   OVER ⚠
Cost                 $2.00                    $0.85  (43%)    ON BUDGET
Requests            ~8                        11              —
Model mix           mixed                   6 sonnet, 3 haiku, 2 sonar-pro
```

### monorepo Key Insight

This is the only project where tokens exceeded the estimate. Two factors:
1. SPEC-001 at 90% of medium tier — cross-service auth across 3 packages with 2 opus
   calls is near the upper bound for medium tier
2. SPEC-002 spike exceeded low tier by 68% — research queries (including 2 Perplexity
   sonar-pro calls) are structurally token-heavy

**If SPEC-002 had been assigned medium tier (the recommendation), the project would
show 616,400 / 1,000,000 = 62% token utilization — comfortably on budget.**

---

## Cross-Project Comparison

### Estimated vs Actual Cost by Project

```
                        Estimated     Actual        Savings      Savings %
                        ─────────    ─────────    ─────────    ─────────
python-fastapi           $12.00       $2.85        $9.15          76%
typescript-nextjs        $20.00       $2.21       $17.79          89%
monorepo                 $12.00       $4.63        $7.37          61%
─────────────────────────────────────────────────────────────────────────
TOTAL                    $44.00      $10.69       $33.31          76%
```

```
                           $0      $5      $10     $15     $20
                           ├───────┼───────┼───────┼───────┤
python-fastapi    Est [$12]  ████████████████████████░░░░░░░░
                  Act [$3]   ██████                          
                                                             
typescript-nextjs Est [$20]  ████████████████████████████████████████
                  Act [$2]   ████                            
                                                             
monorepo          Est [$12]  ████████████████████████░░░░░░░░
                  Act [$5]   █████████░                      
```

### Estimated vs Actual Tokens by Project

```
                        Estimated       Actual        Utilization
                        ──────────    ──────────    ──────────
python-fastapi            600,000       450,700          75%
typescript-nextjs       1,000,000       417,100          42%
monorepo                  600,000       616,400         103% ⚠
─────────────────────────────────────────────────────────────────
TOTAL                   2,200,000     1,484,200          67%
```

### Cost Savings Breakdown — Where Did the Savings Come From?

```
Savings Driver                             Est. Saved    % of Total Savings
───────────────────────────────────────────────────────────────────────────
Model routing (haiku for light phases)       $14.20            42.6%
Under-utilized tier caps (token headroom)    $12.50            37.5%
Prompt caching (230K tokens saved)            $1.38             4.1%
Semantic caching (27K tokens saved)           $0.19             0.6%
Efficient phase execution                     $5.04            15.1%
───────────────────────────────────────────────────────────────────────────
TOTAL                                        $33.31           100.0%
```

The largest savings driver is **model routing** — tier caps assume a blended rate, but
haiku at $0.38/1K handles 44% of requests, dramatically reducing actual cost. The second
driver is **token headroom** — specs consistently use fewer tokens than the tier cap allows,
especially typescript-nextjs at 42% utilization.

---

## Recommendations

1. **Introduce a "medium-light" tier** (300K tokens, $6.00) for frontend/UI specs.
   Both typescript-nextjs specs used ~200K tokens — medium tier (500K) over-provisions
   by 56-60%. A tighter tier improves budget signal without risking over-runs.

2. **Default spikes to medium tier.** monorepo SPEC-002 proved that research workloads
   exceed low tier token caps even at low business priority. Set `min_tier: medium`
   for spike type in all armature.yaml configs.

3. **Adjust cost caps to reflect model routing savings.** Current tier pricing assumes
   ~$20/1M tokens blended. Actual blended rate is $7.20/1K. Consider reducing cost
   caps by 40% while keeping token caps — this gives more meaningful cost alerts.

4. **Flag specs at >85% tier utilization for proactive tier upgrade.** monorepo SPEC-001
   at 90% had minimal headroom. An early warning at 85% would allow mid-spec tier
   escalation before hitting the cap.

5. **Track estimated vs actual per phase, not just per spec.** The phase-level variance
   data (plan over in typescript-nextjs, build over in monorepo) provides actionable
   insights that spec-level totals obscure.
