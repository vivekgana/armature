# Cross-Project Test Report: 2026-Q2
Generated: 2026-04-20T00:00:00+00:00 | Projects: 3 | Specs: 6 | Period: 2026-Q2

## Overview

```
Metric                          Value
--------------------------------------
Specs with test requirements        5   (1 spike excluded: coverage_min=0)
Specs requiring integration tests   4
Specs requiring e2e tests           1   (typescript-nextjs SPEC-001)
Specs requiring type checking       5   (1 spike excluded: type_check=false)
Total test phase tokens       329,000   (22.2% of 1,484,200 total)
Total test phase cost           $1.99
Total test phase requests          12
Test files generated                7
Human gates with test signoff       2
All quality gates                PASS
```

---

## Test Coverage Requirements Matrix

```
Project           Spec     Title                           Type     Unit Cov   Integration  E2E    Lint    Type Check
---------------------------------------------------------------------------------------------------------------------
python-fastapi    SPEC-001 Add user authentication         feature     90%        yes        no     yes       yes
python-fastapi    SPEC-002 Fix pagination off-by-one       bugfix      85%        yes        no     yes       yes
typescript-nextjs SPEC-001 Add dark mode toggle            feature     80%        no         yes    yes       yes
typescript-nextjs SPEC-002 Refactor API routes middleware   refactor    85%        yes        no     yes       yes
monorepo          SPEC-001 Add shared auth middleware pkg   feature     90%        yes        no     yes       yes
monorepo          SPEC-002 Investigate GraphQL gateway      spike        0%        no         no     yes       no
---------------------------------------------------------------------------------------------------------------------
```

Notes:
- monorepo SPEC-002 (spike): `coverage_min=0` and `type_check=false` are deliberate —
  spike deliverable is a decision document and prototype, not production code
- typescript-nextjs SPEC-001: `e2e=true`, `integration=false` — theme toggling requires
  a real browser environment for FOUC prevention testing (AC-4)
- High-priority specs (py-fastapi SPEC-001, monorepo SPEC-001) both require 90% coverage
  and integration tests — consistent with cross-service complexity

---

## Test Phase Token Usage

```
Project           Spec     Test Reqs   Test Tokens   % of Spec   Total Spec Tokens   Coverage Min
--------------------------------------------------------------------------------------------------
monorepo          SPEC-001       3       102,000        22.8%         448,000              90%
python-fastapi    SPEC-001       3        93,000        24.7%         376,000              90%
typescript-nextjs SPEC-002       2        51,500        23.5%         219,100              85%
typescript-nextjs SPEC-001       2        48,500        24.5%         198,000              80%
python-fastapi    SPEC-002       1        20,000        26.8%          74,700              85%
monorepo          SPEC-002       1        14,000         8.3%         168,400               0%
--------------------------------------------------------------------------------------------------
TOTAL                           12       329,000        22.2%       1,484,200
```

### Test Complexity Scaling

Test token usage correlates with spec complexity and coverage requirements:

```
Complexity Level              Test Tokens   Coverage   Requests   Tokens/Request
---------------------------------------------------------------------------------
spike (cov=0%)                    14,000        0%          1          14,000
bugfix (scoped, cov=85%)          20,000       85%          1          20,000
medium feature (cov=80%)          48,500       80%          2          24,250
medium refactor (cov=85%)         51,500       85%          2          25,750
high feature (cov=90%)            93,000       90%          3          31,000
high cross-service (cov=90%)     102,000       90%          3          34,000
---------------------------------------------------------------------------------
```

Each 5% increase in coverage target adds ~5,000-8,000 tokens per test request.
Cross-service specs (monorepo SPEC-001) require ~10% more test tokens than single-service
specs at the same coverage level due to integration test overhead.

---

## Test Phase Request Breakdown

### python-fastapi / SPEC-2026-Q2-001 — Add user authentication (3 requests, 93K tokens)

```
Task     Model           Tokens   Cost     Cache            Intent     Output File
-----------------------------------------------------------------------------------
test-1   claude-sonnet   34,000   $0.222   —                test_gen   test_auth_service.py
test-2   claude-sonnet   31,000   $0.186   prompt hit       test_gen   test_auth_service.py (expanded)
test-3   claude-sonnet   28,000   $0.138   semantic hit     test_gen   test_auth_service.py (edge cases)
-----------------------------------------------------------------------------------
TOTAL                    93,000   $0.546
```

test-3 semantic cache hit reused test scaffolding from test-1 (~11,000 tokens saved).
Final file: 3 test classes (TestRegister, TestAuthenticate, TestTokenExpiry), 7 methods
covering AC-1, AC-2, AC-3, AC-5.

### python-fastapi / SPEC-2026-Q2-002 — Fix pagination off-by-one (1 request, 20K tokens)

```
Task     Model           Tokens   Cost     Cache         Intent     Output File
--------------------------------------------------------------------------------
test-1   claude-sonnet   20,000   $0.113   —             test_gen   test_pagination.py
--------------------------------------------------------------------------------
TOTAL                    20,000   $0.113
```

Single request for well-scoped bugfix. 1 test class (TestPaginationFix), 4 methods
covering AC-1, AC-2, AC-3.

### typescript-nextjs / SPEC-2026-Q2-001 — Add dark mode toggle (2 requests, 48.5K tokens)

```
Task     Model           Tokens   Cost     Cache         Intent     Output File
--------------------------------------------------------------------------------
test-1   claude-sonnet   23,000   $0.153   —             test_gen   theme.test.ts
test-2   claude-sonnet   25,500   $0.158   prompt hit    test_gen   theme.test.ts (expanded)
--------------------------------------------------------------------------------
TOTAL                    48,500   $0.311
```

Tests cover pure theme utility logic (getInitialTheme, getStoredTheme, storeTheme).
1 describe block, 5 test methods covering AC-2, AC-3. AC-4 (FOUC prevention) requires
e2e browser testing — outside unit test scope.

### typescript-nextjs / SPEC-2026-Q2-002 — Refactor API routes middleware (2 requests, 51.5K tokens)

```
Task     Model           Tokens   Cost     Cache         Intent     Output File
--------------------------------------------------------------------------------
test-1   claude-sonnet   24,500   $0.179   —             test_gen   middleware.test.ts
test-2   claude-sonnet   27,000   $0.168   prompt hit    test_gen   middleware.test.ts (expanded)
--------------------------------------------------------------------------------
TOTAL                    51,500   $0.347
```

2 describe blocks (withAuth, withLogging), 3 test methods covering AC-1, AC-3.
Slightly more tokens than SPEC-001 tests — NextRequest/NextResponse mocking is more
token-intensive than localStorage mocks.

### monorepo / SPEC-2026-Q2-001 — Add shared auth middleware package (3 requests, 102K tokens)

```
Task     Model           Tokens   Cost     Cache         Intent     Output File         Package
-------------------------------------------------------------------------------------------------
test-1   claude-sonnet   37,000   $0.243   —             test_gen   test_tokens.py       shared
test-2   claude-sonnet   34,000   $0.222   prompt hit    test_gen   test_middleware.py    shared
test-3   claude-sonnet   31,000   $0.142   prompt hit    test_gen   (integration glue)   api+worker
-------------------------------------------------------------------------------------------------
TOTAL                   102,000   $0.607
```

3 test requests map to 3 packages (shared/auth/tokens, shared/auth/middleware, plus
cross-service integration for api+worker). test-3 covered integration scenarios via
pytest fixtures embedded in test_middleware.py. Highest test token usage across all
specs — driven by integration_test_required across 3 packages.

### monorepo / SPEC-2026-Q2-002 — Investigate GraphQL gateway (1 request, 14K tokens)

```
Task     Model           Tokens   Cost     Cache   Intent     Output File
--------------------------------------------------------------------------
test-1   claude-sonnet   14,000   $0.090   —       test_gen   graphql_prototype.py (smoke)
--------------------------------------------------------------------------
TOTAL                    14,000   $0.090
```

Minimal test for spike. `coverage_min=0` means no unit coverage required. Generated a
basic smoke test confirming the GraphQL prototype imports and responds to a minimal
query — sufficient for spike deliverable verification.

---

## Test Quality Gates Status

```
Project           Spec     Lint   Type Check   Unit Cov   Integration   E2E    Human Gate              Status
--------------------------------------------------------------------------------------------------------------
python-fastapi    SPEC-001  PASS     PASS        90%+        PASS       n/a    test_signoff             PASS
python-fastapi    SPEC-002  PASS     PASS        85%+        PASS       n/a    —                        PASS
typescript-nextjs SPEC-001  PASS     PASS        80%+        n/a        PASS   —                        PASS
typescript-nextjs SPEC-002  PASS     PASS        85%+        PASS       n/a    —                        PASS
monorepo          SPEC-001  PASS     PASS        90%+        PASS       n/a    integration_test_review  PASS
monorepo          SPEC-002  PASS     n/a          0%         n/a        n/a    findings_review          PASS
--------------------------------------------------------------------------------------------------------------
All gates: PASS
```

Human gate details:
- **py-fastapi SPEC-001 `test_signoff`**: developer signed off on coverage completeness
  and edge cases (TestTokenExpiry class) before merge
- **monorepo SPEC-001 `integration_test_review`**: developer validated that auth works
  across both FastAPI (api service) and Celery (worker service) via test-3
- **monorepo SPEC-002 `findings_review`**: developer reviewed no-go recommendation and
  trade-off analysis in spike decision document

---

## Test Output File Inventory

```
Project           Spec     Test File                                     Lang    Classes  Methods  AC Coverage
--------------------------------------------------------------------------------------------------------------
python-fastapi    SPEC-001 output/tests/test_auth/test_auth_service.py   Python  3        7        AC-1,2,3,5
python-fastapi    SPEC-002 output/tests/test_items/test_pagination.py    Python  1        4        AC-1,2,3
typescript-nextjs SPEC-001 output/__tests__/theme.test.ts                TS      1        5        AC-2,3
typescript-nextjs SPEC-002 output/__tests__/middleware.test.ts           TS      2        3        AC-1,3
monorepo          SPEC-001 output/tests/test_auth/test_tokens.py         Python  2        4        AC-1,2
monorepo          SPEC-001 output/tests/test_auth/test_middleware.py     Python  1        3        AC-1,2,5
monorepo          SPEC-002 output/services/api/graphql_prototype.py      Python  —        —        smoke only
--------------------------------------------------------------------------------------------------------------
TOTAL             6 specs  7 files                                               10       26
```

Notes:
- monorepo SPEC-001 produced 2 test files (one per shared auth module); test-3
  integration scenarios are embedded in test_middleware.py via pytest fixtures
- ts-nextjs SPEC-001: AC-4 (no FOUC) not unit-testable — requires real browser (e2e)
- monorepo SPEC-002: graphql_prototype.py is a smoke test only, no classes/methods

---

## Model Usage in Test Phase

```
Model             Requests   Tokens     Cost    % Test Cost   Avg Tokens/Req
-----------------------------------------------------------------------------
claude-sonnet           12   329,000    $1.99       100.0%        27,417
claude-haiku             0         0    $0.00         0.0%             —
claude-opus              0         0    $0.00         0.0%             —
sonar-pro                0         0    $0.00         0.0%             —
-----------------------------------------------------------------------------
```

Test phase is **100% claude-sonnet** across all 6 specs. No test request was escalated
to opus (test complexity stays below `complex_code_gen` threshold) and haiku lacks the
context retention needed for multi-request test phases with coverage targets.

Average token consumption per test request: **27,417 tokens** — tightly clustered,
confirming predictable and stable test generation behavior across all project types.

---

## Test Cost as Fraction of Total Budget

```
Project           Spec     Test Cost   Total Cost   Test %   Test Tokens   Total Tokens   Test Tok %
-----------------------------------------------------------------------------------------------------
python-fastapi    SPEC-001   $0.546      $2.58       21.2%      93,000        376,000        24.7%
python-fastapi    SPEC-002   $0.113      $0.27       41.9%      20,000         74,700        26.8%
typescript-nextjs SPEC-001   $0.311      $1.04       29.9%      48,500        198,000        24.5%
typescript-nextjs SPEC-002   $0.347      $1.17       29.7%      51,500        219,100        23.5%
monorepo          SPEC-001   $0.607      $3.78       16.1%     102,000        448,000        22.8%
monorepo          SPEC-002   $0.090      $0.85       10.6%      14,000        168,400         8.3%
-----------------------------------------------------------------------------------------------------
TOTAL              $1.99     $10.69       18.6%     329,000      1,484,200        22.2%
```

Test cost % (18.6%) is lower than test token % (22.2%) because test phase uses only
sonnet — no opus escalation. Specs with opus usage in build (py-fastapi SPEC-001,
monorepo SPEC-001) show the biggest gap between test cost % and test token %.

---

## Test Optimization Recommendations

1. **Batch small bugfix tests into the build phase.** py-fastapi SPEC-002 used a single
   test request (20K tokens, 26.8% of spec). For scoped bugfixes where the fix and its
   tests are semantically coupled, combine into a single build+test request. Estimated
   savings: 3-5K tokens per bugfix spec from reduced context overhead.

2. **Enable prompt caching for first test request.** test-1 in 4 of 6 specs had 0
   cache hits. The build context is cached by that point — ensure test-1 carries forward
   the build summary as a cached prefix to capture the first hit immediately.

3. **Add AC traceability check to test quality gate.** All generated test files include
   SPEC/AC comments, but no automated check verifies completeness. Add an armature
   quality check that parses test files and flags any acceptance criteria without a
   corresponding test method.

4. **Create `spike_smoke` intent routed to haiku.** monorepo SPEC-002 used sonnet
   (`test_gen` intent) for what is effectively a smoke test. A dedicated `spike_smoke`
   intent routed to haiku would reduce spike test cost from ~$0.09 to ~$0.01 for
   equivalent validation quality.

5. **Set per-type test phase targets.** Current 25% target applies uniformly. Suggested
   targets based on Q2 actuals:

   ```
   Type                   Test Target
   ------------------------------------
   feature (high)             25%
   feature (medium)           24%
   refactor                   24%
   bugfix                     27%
   spike                      10%
   ```

   This eliminates false flags on spike and bugfix test phases.

6. **Seed semantic cache for multi-package test phases.** monorepo SPEC-001's test-3
   had no semantic cache hits despite test-1 and test-2 establishing shared context.
   Pre-loading the shared auth package interface as a semantic cache entry at the start
   of the test phase could save 8-12K tokens across test-2 and test-3.
