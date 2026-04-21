# Cross-Project Budget Report: Token Planned vs Actual — 2026-Q2
Generated: 2026-04-20T00:00:00+00:00 | Projects: 3 | Specs: 6 | Period: 2026-Q2

## Executive Summary

```
Metric                          Value
--------------------------------------
Total specs processed               6
Total tokens consumed       1,484,200
Total cost                     $10.69
Total requests                     68
Specs on budget                     5
Specs over tier cap                 1   (monorepo SPEC-002, tokens only)
Prompt cache hits            23/68 (34%)
Tokens saved by caching       257,000   (prompt: 230,000 + semantic: 27,000)
Estimated cache savings         ~$1.55
```

All 6 specs stayed within cost caps. 1 spec exceeded its token cap (monorepo SPEC-002:
168% of low tier) while cost remained within budget. Net assessment: budget governance
is healthy; tier calibration needs one adjustment — spikes should default to medium.

---

## Budget Tiers (All Projects — Identical Config)

```
Tier        Token Cap    Cost Cap
----------------------------------
low           100,000      $2.00
medium        500,000     $10.00
high        1,000,000     $20.00
critical    2,000,000     $40.00
```

---

## Per-Spec Token and Cost: Planned vs Actual

```
Project           Spec ID   Title                           Type     Priority  Tier    Planned Tok  Actual Tok  Tok %   Planned $  Actual $  Cost %  Status
-----------------------------------------------------------------------------------------------------------------------------------------------------------
python-fastapi    SPEC-001  Add user authentication         feature  high      medium     500,000     376,000    75%      $10.00     $2.58    26%    ON BUDGET
python-fastapi    SPEC-002  Fix pagination off-by-one       bugfix   medium    low        100,000      74,700    75%       $2.00     $0.27    14%    ON BUDGET
typescript-nextjs SPEC-001  Add dark mode toggle            feature  medium    medium     500,000     198,000    40%      $10.00     $1.04    10%    ON BUDGET
typescript-nextjs SPEC-002  Refactor API routes middleware   refactor medium    medium     500,000     219,100    44%      $10.00     $1.17    12%    ON BUDGET
monorepo          SPEC-001  Add shared auth middleware pkg   feature  high      medium     500,000     448,000    90%      $10.00     $3.78    38%    ON BUDGET
monorepo          SPEC-002  Investigate GraphQL gateway      spike    low       low        100,000     168,400   168%  ⚠   $2.00     $0.85    43%    OVER (tok)
-----------------------------------------------------------------------------------------------------------------------------------------------------------
TOTAL                                                                                   2,200,000   1,484,200    67%      $44.00    $10.69    24%
```

Key observations:
- **5 of 6 specs** under both token and cost caps
- **monorepo SPEC-002** exceeded low tier by 68,400 tokens (68% over) — research-heavy
  spike workloads are structurally token-intensive regardless of business priority
- **monorepo SPEC-001** at 90% token utilization — minimal headroom for similar scope
- **Cost utilization is consistently lower than token utilization** — models are cheaper
  per-token than the tier pricing assumes, especially when haiku handles light phases

---

## Budget Gauge (Tokens vs Tier Cap)

```
py-fastapi  SPEC-001  [medium]  ████████████████████████░░░░░░░░░░  75%   376K / 500K
py-fastapi  SPEC-002  [low]     ████████████████████████░░░░░░░░░░  75%    75K / 100K
ts-nextjs   SPEC-001  [medium]  █████████████░░░░░░░░░░░░░░░░░░░░░  40%   198K / 500K
ts-nextjs   SPEC-002  [medium]  ██████████████░░░░░░░░░░░░░░░░░░░░  44%   219K / 500K
monorepo    SPEC-001  [medium]  █████████████████████████████░░░░░  90%   448K / 500K
monorepo    SPEC-002  [low]     ████████████████████████████████ ⚠ 168%   168K / 100K
                                0%              50%             100%
```

---

## Phase Allocation: Target vs Actual (All Specs)

```
Phase      Target   py-fast    py-fast    ts-next    ts-next    mono       mono       Combined
                    SPEC-001   SPEC-002   SPEC-001   SPEC-002   SPEC-001   SPEC-002   Actual     Delta
-------------------------------------------------------------------------------------------------------
validate    5.0%      4.1%       6.3%       2.8%       2.9%       4.4%       2.8%       3.9%     -1.1%
audit      10.0%     10.0%      11.4%      10.1%      10.4%      10.6%      10.5%      10.5%     +0.5%
plan       15.0%     14.0%      17.4%      18.4%      18.5%      15.0%      24.9% (!)  17.4%     +2.4%
build      40.0%     43.6%      32.1%      39.4%      39.7%      50.6% (!)  42.2%      41.9%     +1.9%
test       25.0%     24.7%      26.8%      24.5%      23.5%      24.9%       8.3% (!)  22.2%     -2.8%
review      5.0%      3.6%       6.0%       4.8%       5.0%       3.9%      11.3% (!)   5.3%     +0.3%
-------------------------------------------------------------------------------------------------------
```

**(!)** flags (actual > target × 1.5):
- **plan** monorepo SPEC-002 (24.9%): spike research queries are inherently token-heavy.
  Raise plan target to 25% in spike template.
- **build** monorepo SPEC-001 (50.6%): cross-service integration across 3 packages drove
  higher build complexity. Expected for cross-service scope.
- **test** monorepo SPEC-002 (8.3%): `eval.unit_test_coverage_min=0` for spike type.
  Not a defect — test target doesn't apply to spikes.
- **review** monorepo SPEC-002 (11.3%): spike decision doc (no-go recommendation)
  required thorough review with trade-off analysis.

---

## Model Cost Efficiency

```
Model              Requests   Tokens       Cost    Cost / 1K Tokens   % of Total Cost
--------------------------------------------------------------------------------------
claude-haiku             30    397,100     $0.15           $0.38             1.4%
claude-sonnet            35  1,020,000     $6.89           $6.75            64.5%
claude-opus               3     74,000     $2.62          $35.41            24.5%
sonar-pro                 2     29,500     $0.08           $2.71             0.7%
--------------------------------------------------------------------------------------
Blended                  68  1,484,200    $10.69           $7.20           100.0%
```

- **claude-haiku** ($0.38/1K): 44% of requests, 1.4% of cost. Handles validate, audit,
  and review phases across all projects. Optimal for structured reasoning tasks.
- **claude-sonnet** ($6.75/1K): 51% of requests, 64.5% of cost. Primary workhorse for
  build, test, and plan phases. Consistent quality floor for code generation.
- **claude-opus** ($35.41/1K): 4% of requests, 24.5% of cost. Used exactly 3 times:
  JWT RS256/HS256 architecture (py-fastapi), JWT design (monorepo), and cross-service
  integration (monorepo). Each justified by `complex_code_gen` or `architecture` intent.
- **sonar-pro** ($2.71/1K): 3% of requests, 0.7% of cost. Perplexity research queries
  for monorepo spike — 60% cheaper than sonnet for information retrieval.

---

## Cross-Project Cost Ranking

```
Rank  Project           Spec     Type     Tokens     Cost    Requests  Cost/Req  Cost/1K Tok
---------------------------------------------------------------------------------------------
  1   monorepo          SPEC-001 feature  448,000    $3.78        15    $0.252       $8.44
  2   python-fastapi    SPEC-001 feature  376,000    $2.58        14    $0.184       $6.86
  3   typescript-nextjs SPEC-002 refactor 219,100    $1.17        11    $0.106       $5.34
  4   typescript-nextjs SPEC-001 feature  198,000    $1.04        11    $0.095       $5.25
  5   monorepo          SPEC-002 spike    168,400    $0.85        11    $0.077       $5.05
  6   python-fastapi    SPEC-002 bugfix    74,700    $0.27         6    $0.045       $3.61
---------------------------------------------------------------------------------------------
```

The two high-priority specs account for $6.36 (59.5%) of total spend, driven by opus
escalation and cross-service scope. The bugfix (SPEC-002) achieved the lowest cost per
request ($0.045) and cost per 1K tokens ($3.61) — effective model routing for simple tasks.

---

## Cache Performance Summary

```
Project           Spec     Prompt Hits    Tokens Saved   Semantic Hits   Semantic Saved
----------------------------------------------------------------------------------------
python-fastapi    SPEC-001  6/14 (43%)       62,000            1            ~11,000
python-fastapi    SPEC-002  0/6  (0%)             0            0                  0
typescript-nextjs SPEC-001  5/11 (45%)       41,000            0                  0
typescript-nextjs SPEC-002  5/11 (45%)       47,000            0                  0
monorepo          SPEC-001  7/15 (47%)       80,000            0                  0
monorepo          SPEC-002  0/11 (0%)             0            1            ~16,000
----------------------------------------------------------------------------------------
TOTAL                       23/68 (34%)     230,000            2            ~27,000
```

- Multi-request specs consistently achieve 43-47% prompt cache hit rates
- Single-pass specs (py-fastapi SPEC-002) and multi-provider spikes get 0% prompt hits
- 2 semantic cache hits saved ~27,000 tokens at zero cost
- Estimated total cache savings: ~$1.55 at blended $7.20/1K rate

---

## Tier Recommendation vs Actual Fit

```
Project           Spec     Priority   Naive Tier   Actual Fit   Recommendation
               (from priority)
--------------------------------------------------------------------------------
python-fastapi    SPEC-001 high       high         medium       medium (75% util)
python-fastapi    SPEC-002 medium     medium       low          low (75% util)
typescript-nextjs SPEC-001 medium     medium       medium       medium (40% util)
typescript-nextjs SPEC-002 medium     medium       medium       medium (44% util)
monorepo          SPEC-001 high       high         medium       medium (90% util) ⚠
monorepo          SPEC-002 low        low          medium ⚠     medium (34% util)
--------------------------------------------------------------------------------
```

- Priority-based tier assignment over-provisions in 2/6 cases (high→medium)
- Priority-based assignment under-provisions in 1/6 cases (low spike→needs medium)
- **Recommendation**: use spec *type* (not priority) as primary tier signal.
  Spikes and cross-service features need medium regardless of priority.

---

## Optimization Recommendations

1. **Set `min_tier: medium` for spike type in all armature.yaml configs.** monorepo
   SPEC-002 exceeded low tier at 168% token utilization. Research workloads are
   structurally token-heavy regardless of business priority.

2. **Monitor cross-service specs at medium tier.** monorepo SPEC-001 hit 90% of
   medium tier. Future specs touching 3+ packages may need high tier. Add an
   auto-escalation rule: if build phase alone exceeds 50% of tier cap, recommend
   tier upgrade.

3. **Opus usage is correctly calibrated but expensive.** 3 requests consumed 24.5%
   of total Q2 cost ($2.62). The router's `complex_code_gen` intent correctly
   identified all three escalations. Validate each opus use case before accepting
   auto-escalation.

4. **Expand sonar-pro routing.** 2 sonar-pro requests cost $0.08 vs ~$0.45 if
   sonnet had been used (82% saving). Route all `research` and `ecosystem_survey`
   intents to sonar-pro across all projects.

5. **Raise plan phase target to 18% for frontend specs.** Both typescript-nextjs
   specs hit 18.4-18.5% plan allocation. This is consistent and expected for
   component architecture decisions — adjust the template to reduce false flag noise.

6. **Tighten validate phase target to 4%.** Combined actual is 3.9% vs 5% target.
   All projects finish validate efficiently — free the 1% headroom for build phase.
