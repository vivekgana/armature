# Example: Armature Project Report

**Project**: E-commerce API (FastAPI + PostgreSQL)
**Team**: 8 developers using Claude Code + Cursor
**Period**: April 2026 (1 month)
**Specs completed**: 12

---

## Executive Summary

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ARMATURE PROJECT REPORT — April 2026                                         │
│  Project: ecommerce-api | Language: Python | Framework: FastAPI               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  QUALITY SCORE:  94.2% (merge_ready)                                          │
│  ████████████████████████████████████████████░░░░  94.2/100                   │
│                                                                               │
│  BUDGET UTILIZATION:  $847 of $2,000 budget (42.4%)                           │
│  █████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░  42.4%                      │
│                                                                               │
│  ROUTING SAVINGS:  $4,230 saved vs all-premium pricing                        │
│  Routing ratio: 5.9x (target: 2.0x) — Grade: A                               │
│                                                                               │
│  SELF-HEAL RATE:  87% of lint issues auto-fixed                               │
│  Circuit breaker triggered: 2 times (both resolved within 1 hour)             │
│                                                                               │
│  SPECS DELIVERED:  12/12 (100% completion rate)                               │
│  First-pass quality gate: 8/12 (67%) — improving from 50% last month          │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Quality Gate Results

### Per-Check Scores (Weighted)

```
CHECK                SCORE   WEIGHT   CONTRIBUTION   STATUS
═══════════════════════════════════════════════════════════════
lint (ruff)          0.98    25       24.5/25        ✅ PASS
type_check (mypy)   0.95    25       23.8/25        ✅ PASS
test (pytest)       1.00    20       20.0/20        ✅ PASS
security (bandit)   0.90    20       18.0/20        ✅ PASS
complexity (radon)  0.87    15       13.0/15        ⚠️  3 functions >CC10
dependency_audit    1.00    15       15.0/15        ✅ PASS
test_ratio          0.92    10        9.2/10        ✅ PASS (ratio: 0.46)
docstring           0.85    10        8.5/10        ⚠️  12 undocumented

─────────────────────────────────────────────────────────
WEIGHTED SCORE:              132.0/140 = 94.2%
QUALITY LEVEL:               merge_ready (threshold: 95% ≈ met)
```

### Quality Trend (4 weeks)

```
Week 1:  ████████████████░░░░  82% (review_ready)
Week 2:  █████████████████░░░  88% (review_ready)
Week 3:  ██████████████████░░  92% (review_ready)
Week 4:  ███████████████████░  94% (merge_ready) ↑
```

### Findings Summary

| Category | Count | Severity | Auto-Fixed | Manual Fix |
|----------|-------|----------|-----------|------------|
| Lint violations | 47 | Low | 41 (87%) | 6 |
| Type errors | 3 | Medium | 0 | 3 |
| Security findings | 2 | Medium | 0 | 2 |
| Complexity violations | 3 | Low | 0 | 3 (refactored) |
| Undocumented symbols | 12 | Info | 0 | 8 (4 acceptable) |

---

## 2. Budget & Cost Report

### Monthly Summary

```
BUDGET REPORT — April 2026
═══════════════════════════════════════════════════════════

  Total Tokens:         2,340,000
  Total Cost:           $847.23
  Monthly Budget:       $2,000.00
  Utilization:          42.4%
  Specs Completed:      12
  Cost per Spec:        $70.60 (avg)
  Cost per PR:          $42.36 (avg, 20 PRs)

  Provider Breakdown:
  ┌─────────────────────────────────────────────────────┐
  │ Provider     Tokens      Cost      % Tokens  % Cost │
  ├─────────────────────────────────────────────────────┤
  │ anthropic    580K       $612.00     25%       72%   │
  │ google       1,200K     $180.00     51%       21%   │
  │ openai       460K       $46.23      20%        5%   │
  │ perplexity   100K       $9.00        4%        1%   │
  └─────────────────────────────────────────────────────┘

  Model Usage:
  ┌─────────────────────────────────────────────────────┐
  │ Model              Requests  Tokens    Cost    Intent│
  ├─────────────────────────────────────────────────────┤
  │ claude-sonnet      45        480K     $576     arch  │
  │ claude-haiku       23        100K     $36      explain│
  │ gemini-2.5-flash   120       1,100K   $165     code  │
  │ gemini-flash-lite  40        100K     $15      lint  │
  │ gpt-4o-mini        88        460K     $46      test  │
  │ sonar-pro          5         100K     $9       search│
  └─────────────────────────────────────────────────────┘
```

### Routing Savings Analysis

```
  ROUTING SAVINGS
  ═══════════════
  
  If all requests used claude-sonnet:
    Total cost:           $5,077
    
  With Armature routing:
    Total cost:           $847
    
  Savings:                $4,230 (83.3%)
  Routing ratio:          5.99x (target: 2.0x — Grade: A)
  
  Breakdown by strategy:
    Simple tasks → cheap models:    saved $3,200
    Semantic cache hits (38%):      saved $580
    Context narrowing:              saved $450
```

### Phase Allocation vs Target

```
  Phase         Actual    Target    Delta    Status
  ─────────────────────────────────────────────────
  validate      4%        5%        -1%      ✅
  audit         8%        10%       -2%      ✅
  plan          18%       15%       +3%      ⚠️ slightly over
  build         38%       40%       -2%      ✅
  test          27%       25%       +2%      ✅
  review        5%        5%        0%       ✅
```

### Budget Circuit Breaker Events

```
  Date         Spec                  Trigger        Resolution
  ────────────────────────────────────────────────────────────
  Apr 12       SPEC-2026-Q2-005     3x overrun     Scope reduced, resolved in 1h
  Apr 21       SPEC-2026-Q2-009     3x overrun     Model routing adjusted, resolved in 30m
```

---

## 3. Self-Healing Pipeline Report

```
SELF-HEALING REPORT — April 2026
═══════════════════════════════════

  Total heal invocations:     34
  Successful auto-fixes:      28 (82%)
  Escalated to human:         6  (18%)
  Circuit breaker triggers:   2

  By Failure Type:
  ┌────────────────────────────────────────────────────┐
  │ Type        Invocations  Fixed  Escalated  Rate    │
  ├────────────────────────────────────────────────────┤
  │ lint        24           21     3          87.5%   │
  │ type_check  7            5      2          71.4%   │
  │ test        3            2      1          66.7%   │
  └────────────────────────────────────────────────────┘

  Heal Attempts Distribution:
    Fixed on attempt 1:    20 (71%)
    Fixed on attempt 2:    6  (21%)
    Fixed on attempt 3:    2  (7%)
    Circuit breaker:       6  (escalated)

  Time Saved (estimated):
    Average manual fix time:     12 minutes
    Auto-fix time:               8 seconds
    Total heal invocations:      28 successful
    Time saved:                  5.5 hours this month
    Developer cost saved:        $825 (at $150/hr)
```

---

## 4. Industry Benchmark Comparison

```
INDUSTRY BENCHMARK COMPARISON
═══════════════════════════════

  Token Usage vs Industry Percentiles (SWE-bench, DevBench)
  ┌──────────────────────────────────────────────────────────────────┐
  │ Task Type   Actual     p25       Median     p75      Position   │
  ├──────────────────────────────────────────────────────────────────┤
  │ bugfix      22,400    15,000    30,000    60,000    p25-p50 (B) │
  │ feature     145,000   50,000    120,000   250,000   p50-p75 (C) │
  │ refactor    48,000    25,000    60,000    150,000   p25-p50 (B) │
  │ test        35,000    20,000    50,000    120,000   p25-p50 (B) │
  └──────────────────────────────────────────────────────────────────┘

  Quality-Budget Position (AgentBench curve):
    Budget:                 195,000 tokens (avg per feature)
    Expected quality:       89%
    Actual quality:         94% ← outperforming the curve
    Note:                   Good context engineering is paying off

  Efficiency Grades:
  ┌────────────────────────────────────────┐
  │ Metric                     Grade       │
  ├────────────────────────────────────────┤
  │ Cache Efficiency           B (38%)     │
  │ Cost per LOC               A ($0.008)  │
  │ Routing Savings            A (5.99x)   │
  │ Calibration Accuracy       B (18%)     │
  │ Task Bugfix                B           │
  │ Task Feature               C           │
  │ Task Refactor              B           │
  └────────────────────────────────────────┘

  Calibration Profile (confidence: 86%):
    task_adjustments:
      bugfix:    0.85 (your team is 15% more efficient than benchmark)
      feature:   1.15 (features take 15% more tokens than predicted)
      refactor:  0.92 (slightly more efficient)
    model_verbosity:
      claude-sonnet: 1.05 (slightly more verbose than baseline)
      gpt-4o-mini:   0.78 (22% less verbose — efficient for tests)
    cache_hit_rate: 0.38 (approaching target 0.40)
```

---

## 5. Architecture Enforcement Report

```
ARCHITECTURE ENFORCEMENT — April 2026
══════════════════════════════════════

  Layers defined:         6
  Boundary rules:         14
  Violations detected:    0 ✅
  Conformance checks:     4 class patterns
  Conformance violations: 0 ✅

  Last boundary scan: 2026-04-27T10:00:00
  All 14 import direction rules enforced successfully.
  
  Layer Health:
  ┌────────────────────────────────────────────────────┐
  │ Layer         Files   LOC     Imports-In  Status   │
  ├────────────────────────────────────────────────────┤
  │ _internal     7       420     42          ✅ shared │
  │ config        6       380     28          ✅ shared │
  │ quality       8       890     12          ✅ clean  │
  │ budget        11      1450    8           ✅ clean  │
  │ architecture  6       520     5           ✅ clean  │
  │ heal          5       380     6           ✅ clean  │
  │ gc            7       560     9           ✅ clean  │
  │ cli           10      680     0           ✅ entry  │
  │ mcp           3       450     0           ✅ entry  │
  └────────────────────────────────────────────────────┘
```

---

## 6. GC (Garbage Collection) Report

```
GC SWEEP — April 2026
═════════════════════

  Agents run:             4
  Total findings:         7
  Critical:               0
  Actionable:             4
  Informational:          3

  Findings:
  ┌──────────────────────────────────────────────────────────────────────┐
  │ Agent          Category              File                 Severity   │
  ├──────────────────────────────────────────────────────────────────────┤
  │ dead_code      oversized_function    src/orders/api.py    WARNING    │
  │ dead_code      oversized_function    src/auth/service.py  WARNING    │
  │ docs           stale_reference       docs/API.md          INFO       │
  │ docs           stale_reference       README.md            INFO       │
  │ architecture   no_violations         —                    ✅         │
  │ budget         spec_overrun          SPEC-2026-Q2-005     WARNING    │
  │ budget         spec_overrun          SPEC-2026-Q2-009     WARNING    │
  └──────────────────────────────────────────────────────────────────────┘

  Recommendations:
  1. Refactor orders/api.py:create_order() — 112 lines (max 50)
  2. Refactor auth/service.py:authenticate() — 78 lines (max 50)  
  3. Update docs/API.md — references removed endpoint /api/v1/legacy
  4. Review budget for feature specs — 2 overruns this month
```

---

## 7. Unique Strengths Demonstrated

### What No Other Tool Provides

| Capability | This Report Section | Competitor Alternative |
|-----------|--------------------|-----------------------|
| **Model routing savings** | $4,230 saved (83%) | None — no competitor tracks this |
| **Per-spec budget tracking** | $70.60/spec avg | None — no competitor has spec-level cost |
| **Auto-calibration** | 86% confidence, EMA-tuned | None — no competitor learns from history |
| **Self-healing with circuit breaker** | 87% auto-fix rate | None — SonarQube only reports, never fixes |
| **Industry benchmark comparison** | Grade A/B/C/D per metric | None — no competitor compares against SWE-bench |
| **Architecture enforcement** | 0 violations, 14 rules | SonarQube has basic architectural rules |
| **Quality-budget curve** | 94% quality at 89% predicted | None — no competitor correlates cost to quality |
| **Phase allocation tracking** | validate→review breakdown | None — no competitor tracks SDLC phases |

### Bottom Line

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                   │
│  WITHOUT ARMATURE:                                                │
│    Monthly AI cost:       $5,077 (all premium, no routing)        │
│    Quality issues found:  In CI, 20 min later                     │
│    Lint auto-fix:         Manual (12 min avg)                     │
│    Budget visibility:     None                                    │
│    Architecture drift:    Discovered in code review               │
│                                                                   │
│  WITH ARMATURE:                                                   │
│    Monthly AI cost:       $847 (routed, cached, optimized)        │
│    Quality issues found:  On file write, 2 seconds                │
│    Lint auto-fix:         87% auto-healed in 8 seconds            │
│    Budget visibility:     Per-spec, per-phase, per-model          │
│    Architecture drift:    Enforced on every import                 │
│                                                                   │
│  TOTAL MONTHLY SAVINGS:   $4,230 + 5.5 dev hours = ~$5,055       │
│  ANNUAL SAVINGS:          ~$60,660                                │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

*Generated by Armature v0.2.3 | pip install armature-harness | MIT License*
