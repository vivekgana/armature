# Spec-Driven Development with Claude Code
## End-to-End Automation with Fewer Defects and Human-in-the-Loop

**Version:** 2.0 | **Date:** April 2026
**Applies to:** Omnia AI and any spec-driven codebase
**Inspired by:** [Ossature](https://ossature.dev/blog/introducing-ossature/) (validate/audit/build), [OpenAI Harness Engineering](https://openai.com/index/harness-engineering/), [Martin Fowler's Exploring Gen AI series](https://martinfowler.com/articles/exploring-gen-ai.html)

---

## 1. Philosophy

Spec-driven development treats a **structured specification** as the single source of truth that drives code generation, testing, validation, and deployment. Claude Code acts as the execution engine -- but humans remain the decision authority at critical gates.

**Core principles:**
- The spec is the contract. Code is a derivative. Tests prove the derivative matches the contract.
- **Validate deterministically, audit with LLM, build with narrow context** (from Ossature).
- **Constrain the solution space** -- trading "generate anything" flexibility for reliability (from OpenAI Harness Engineering).
- **On the loop, not in the loop** -- invest in the harness that produces correct output, don't just review every line (from Kief Morris).
- **Verify after every task, not just at the end** -- catch breakage at generation time.

```
 SPEC (human writes intent)
   |
   v
 VALIDATE (no LLM -- check deps, cycles, schema)     <-- Instant, deterministic
   |
   v
 AUDIT (LLM finds ambiguities, gaps, contradictions)  <-- Human reviews findings
   |
   v
 BUILD PLAN (task graph with narrow context per task)  <-- Human approves / edits
   |
   v
 TEST PLAN (3-tier: unit, integration, e2e)            <-- Human validates strategy
   |
   v
 BUILD (task-by-task with verify + self-fix loop)      <-- Human reviews each diff
   |                                                       (verify runs after each task;
   |                                                        on failure: self-fix up to 3x)
   v
 UNIT TESTS (Claude writes + runs)                     <-- Human validates logic + coverage
   |
   v
 INTEGRATION TESTS (Claude writes + runs)              <-- Human validates boundaries
   |
   v
 E2E / PLAYWRIGHT (Claude writes + runs)               <-- Human validates user journeys
   |
   v
 TRACEABILITY + SELF-REVIEW                            <-- Human final sign-off
   |
   v
 DEPLOY
```

---

## 2. The Spec Format

### 2.1 Spec Structure

Every feature, bugfix, or pipeline stage starts with a spec file. Use a structured format that Claude Code can parse deterministically.

```yaml
# specs/SPEC-2026-Q2-001.yaml
spec_id: "SPEC-2026-Q2-001"
title: "Add Benford Analysis to Data Quality Stage"
type: feature  # feature | bugfix | refactor | spike
priority: high
author: "your-username"
date: "2026-04-14"

# WHAT -- the requirement
description: |
  Add Benford's Law first-digit analysis to the data quality
  pipeline (Stage 4). Should flag accounts where the first-digit
  distribution deviates from the expected Benford curve by more
  than a configurable threshold.

# SCOPE -- what files/modules are affected
scope:
  modules: ["src/quality", "src/pipeline"]
  touches_api: false
  touches_ui: false
  new_files_expected:
    - "src/quality/benford.py"
  modified_files_expected:
    - "src/quality/__init__.py"
    - "src/pipeline/stage_quality.py"

# ACCEPTANCE CRITERIA -- testable conditions
acceptance_criteria:
  - id: AC-1
    description: "Benford analysis runs on all numeric columns"
    testable: true
  - id: AC-2
    description: "Chi-squared test with configurable p-value threshold (default 0.05)"
    testable: true
  - id: AC-3
    description: "Results stored in Unity Catalog quality_results table"
    testable: true
  - id: AC-4
    description: "Anomalous accounts surfaced in dashboard Stage 6"
    testable: true

# CONSTRAINTS
constraints:
  - "Must process 1M+ rows in under 60 seconds on a Standard_DS3_v2 cluster"
  - "No new dependencies outside of scipy and numpy (already in requirements.txt)"
  - "Must emit OpenTelemetry traces for observability"

# HUMAN GATES -- where human approval is required
human_gates:
  - gate: "plan_review"
    approver: "your-username"
    description: "Review implementation plan before coding starts"
  - gate: "test_plan_review"
    approver: "your-username"
    description: "Review test plan (unit/integration/e2e cases) before writing tests"
  - gate: "code_review"
    approver: "your-username"
    description: "Review generated code diff"
  - gate: "unit_test_review"
    approver: "your-username"
    description: "Validate unit test logic, edge cases, and coverage"
  - gate: "integration_test_review"
    approver: "your-username"
    description: "Validate integration tests exercise real boundaries"
  - gate: "e2e_test_review"
    approver: "your-username"
    description: "Validate Playwright tests match real user journeys"
  - gate: "final_test_signoff"
    approver: "your-username"
    description: "Approve full traceability matrix before merge"

# DEPENDENCIES
depends_on: []
blocks: ["SPEC-2026-Q2-003"]

# EVALUATION CRITERIA (for Claude's self-check)
eval:
  unit_test_coverage_min: 90
  integration_test_required: true
  e2e_test_required: false
  linting_must_pass: true
  type_check_must_pass: true
```

### 2.2 Spec Templates by Type

| Type | Required Sections | Optional |
|------|------------------|----------|
| **feature** | description, scope, acceptance_criteria, constraints, human_gates, eval | depends_on |
| **bugfix** | description, root_cause, reproduction_steps, acceptance_criteria, eval | scope |
| **refactor** | description, scope, constraints, eval, before_after_examples | acceptance_criteria |
| **spike** | question, scope, time_box, deliverable | eval |

---

## 3. The Development Workflow

### 3.1 Phase 1: Spec Authoring (Human)

The human writes the spec. Claude Code can assist:

```
You: "Help me write a spec for adding Benford analysis to data quality"
Claude: [Generates spec template, asks clarifying questions]
You: [Reviews, edits, approves the spec]
```

**Key rule:** The human owns the spec. Claude can draft, but the human finalizes.

---

### 3.2 Phase 2: Spec Validation (Deterministic -- No LLM)

*Inspired by [Ossature's `validate` stage](https://ossature.dev/blog/introducing-ossature/#three-stages-validate-audit-build) -- instant, deterministic checks with no LLM involved.*

Before any LLM touches the spec, run deterministic structural checks:

```
You: "Validate specs/SPEC-2026-Q2-001.yaml"
```

**Claude runs these checks without using LLM reasoning:**

```yaml
# Structural Validation Checklist (deterministic, instant)
schema_check:
  - [ ] spec_id follows naming convention: SPEC-{YEAR}-Q{Q}-{NNN}
  - [ ] All required fields present (description, scope, acceptance_criteria, constraints, human_gates, eval)
  - [ ] type is one of: feature | bugfix | refactor | spike
  - [ ] priority is one of: high | medium | low
  - [ ] date is valid ISO format

dependency_check:
  - [ ] All specs in depends_on[] exist in specs/ directory
  - [ ] All specs in blocks[] exist in specs/ directory
  - [ ] No circular dependencies (A depends on B depends on A)
  - [ ] Dependency graph is a DAG (no cycles)

scope_check:
  - [ ] All modules in scope.modules[] exist as directories in src/
  - [ ] All files in modified_files_expected[] exist on disk
  - [ ] No files listed in both new_files_expected and modified_files_expected
  - [ ] If touches_api is true, scope includes src/api/

acceptance_criteria_check:
  - [ ] Every AC has a unique id (AC-1, AC-2, ...)
  - [ ] Every AC has testable: true (or explicit justification for false)
  - [ ] At least one AC exists

eval_check:
  - [ ] unit_test_coverage_min is between 0 and 100
  - [ ] If scope.touches_api or scope.touches_ui, e2e_test_required should be true
```

**Output format:**

```
SPEC VALIDATION: SPEC-2026-Q2-001
══════════════════════════════════
Schema     ✔  All required fields present
Deps       ✔  No circular dependencies
Scope      ✔  All modules exist
ACs        ✔  4 acceptance criteria, all testable
Eval       ⚠  touches_api=false but has API-facing AC-4 — consider setting to true
──────────────────────────────────
RESULT: PASS with 1 warning
```

**No human gate here** -- validation is instant. If it fails, fix the spec and re-validate. If it passes with warnings, address them before proceeding.

---

### 3.3 Phase 3: LLM Audit (Claude Finds Gaps -- Human Reviews)

*Inspired by [Ossature's `audit` stage](https://ossature.dev/blog/introducing-ossature/#three-stages-validate-audit-build) -- LLM catches ambiguities, contradictions, and gaps that structural validation can't.*

After validation passes, Claude performs a semantic audit of the spec:

```
You: "Audit specs/SPEC-2026-Q2-001.yaml for ambiguities and gaps"
```

**Claude audits for:**

| Check | What It Catches | Example |
|-------|----------------|---------|
| **Ambiguity** | Vague requirements that could be interpreted multiple ways | "Should handle large datasets" -- how large? |
| **Contradiction** | Two ACs or constraints that conflict | AC-2 says "default 0.05" but constraint says "default 0.01" |
| **Gaps** | Missing error paths, edge cases, or boundary behaviors | What happens when all values are zero? What if the table doesn't exist? |
| **Scope leaks** | Requirements that imply changes outside declared scope | AC-4 mentions dashboard but scope doesn't include `src/pipeline/stage_dashboard.py` |
| **Testability** | ACs that sound testable but aren't practically testable | "Results should be intuitive" -- how do you test that? |
| **Interface mismatches** | Spec assumes APIs/schemas that don't exist yet | AC-3 writes to `quality_results` table but no DDL is referenced |

**Audit output format:**

```
SPEC AUDIT: SPEC-2026-Q2-001 — Benford Analysis
═══════════════════════════════════════════════════

AMBIGUITIES (2 found):
  A1. AC-1 says "all numeric columns" — does this include integer IDs and
      foreign keys, or only financial amounts? Recommend: add exclusion list
      or column-type filter.
  A2. Constraint says "1M+ rows in under 60 seconds" — is this wall-clock
      time or CPU time? On what cluster size?

CONTRADICTIONS (0 found):
  None.

GAPS (3 found):
  G1. No error handling specified: what if the input DataFrame has no
      numeric columns at all?
  G2. AC-3 writes to quality_results table but no schema/DDL is
      referenced. What columns? What types?
  G3. No behavior specified for columns with all-null values.

SCOPE LEAKS (1 found):
  S1. AC-4 requires changes to dashboard (Stage 6) but scope only
      declares src/quality and src/pipeline. Should scope include
      src/pipeline/stage_dashboard.py?

TESTABILITY (0 issues):
  All ACs are testable as written.

INTERFACE MISMATCHES (1 found):
  I1. AC-3 assumes quality_results table exists. Verify DDL in
      src/data/ or add table creation to this spec's scope.

═══════════════════════════════════════════════════
TOTAL: 2 ambiguities, 0 contradictions, 3 gaps, 1 scope leak, 1 interface mismatch
RECOMMENDATION: Address A1, G1-G3, S1, I1 before planning.
```

**HUMAN GATE -- Audit Review:**

The human reviews the audit findings and decides:
- Which findings require spec updates (fix the spec, re-validate, re-audit)
- Which findings are acceptable as-is (document the decision)
- Which findings reveal the spec is fundamentally wrong (rewrite)

**Critical: Do not proceed to planning until audit findings are resolved.** This is the cheapest place to catch problems -- fixing a spec costs minutes; fixing code costs hours.

---

### 3.4 Phase 4: Build Plan with Narrow Context (Claude + Human Gate)

*Inspired by [Ossature's build plan](https://ossature.dev/blog/introducing-ossature/#narrow-context-and-deterministic-boundaries) -- structured task graph where each task sees ONLY the spec sections and files it needs, not a 128K token dump of everything.*

Claude reads the spec and produces a **structured build plan** (not a freeform list):

```
You: "Read specs/SPEC-2026-Q2-001.yaml and create a build plan"
```

**Build plan format** (adapted from Ossature's TOML plan):

```yaml
# .plans/SPEC-2026-Q2-001-build-plan.yaml
spec_id: "SPEC-2026-Q2-001"
generated_by: "Claude Code"
date: "2026-04-14"

tasks:
  - id: "T001"
    title: "Create BenfordAnalyzer class skeleton"
    spec_refs:
      - "AC-1: Benford analysis runs on all numeric columns"
      - "AC-2: Chi-squared test with configurable threshold"
    context_files:                  # What this task CAN see
      - "src/quality/__init__.py"   # Existing patterns
      - "src/quality/isolation_forest.py"  # Adjacent module for convention reference
    outputs:                        # What this task produces
      - "src/quality/benford.py"
    verify: "mypy src/quality/benford.py && ruff check src/quality/benford.py"
    depends_on: []

  - id: "T002"
    title: "Implement chi-squared Benford analysis logic"
    spec_refs:
      - "AC-1: all numeric columns"
      - "AC-2: chi-squared with configurable p-value"
      - "Constraint: 1M rows < 60s"
    context_files:
      - "src/quality/benford.py"    # From T001
      - "src/quality/isolation_forest.py"  # Pattern reference
    outputs:
      - "src/quality/benford.py"    # Modify
    verify: "mypy src/quality/benford.py && pytest tests/ -x -k benford --tb=short"
    depends_on: ["T001"]

  - id: "T003"
    title: "Integrate Benford into Stage 4 pipeline"
    spec_refs:
      - "AC-1: runs on all numeric columns"
      - "AC-3: results stored in UC quality_results table"
    context_files:
      - "src/quality/benford.py"         # From T001+T002
      - "src/pipeline/stage_quality.py"  # Existing pipeline stage
      - "src/quality/__init__.py"        # Module exports
    outputs:
      - "src/pipeline/stage_quality.py"  # Modify
      - "src/quality/__init__.py"        # Modify exports
    verify: "mypy src/pipeline/stage_quality.py && pytest tests/ -x --tb=short"
    depends_on: ["T002"]

  - id: "T004"
    title: "Add Delta write for Benford results"
    spec_refs:
      - "AC-3: results stored in Unity Catalog quality_results table"
    context_files:
      - "src/quality/benford.py"
      - "src/data/"                      # Delta client patterns
    outputs:
      - "src/quality/benford.py"         # Add write_results method
    verify: "mypy src/quality/benford.py"
    depends_on: ["T002"]

# Task dependency graph:
#   T001 (skeleton) --> T002 (logic) --> T003 (pipeline integration)
#                                    --> T004 (Delta write)
```

**Key differences from our previous freeform plan:**
- **`spec_refs`**: Only the relevant AC sections go into context for each task (Ossature principle: narrow context)
- **`context_files`**: Explicit list of what Claude can read for each task -- nothing else
- **`outputs`**: What files this task creates or modifies
- **`verify`**: Command that runs immediately after each task (Ossature principle: verify in the loop)
- **`depends_on`**: Task dependency graph ensures correct ordering

**Why narrow context matters:** Ossature found that less context means less room for the model to get confused or drift. Each task gets assembled from scratch with only what it needs. In Claude Code, we simulate this by explicitly listing what files to read and what ACs to focus on for each task.

**Human gate:** Review the build plan. Check:
- Is the task decomposition logical?
- Does each task have the right context (not too much, not too little)?
- Are verify commands appropriate?
- Is the dependency graph correct?
- Can you reorder, skip, or add tasks?

---

### 3.5 Phase 5: Build Execution with Verify-Fix Loop (Claude + Human Gate)

*Inspired by [Ossature's build loop](https://ossature.dev/blog/introducing-ossature/#verification-in-the-loop) -- verify after every task, self-fix on failure (up to 3 attempts).*

After build plan approval, Claude executes tasks one at a time:

```
You: "Execute the approved build plan for SPEC-2026-Q2-001"
```

**For each task in dependency order:**

```
┌─────────────────────────────────────────────────┐
│  TASK T002: Implement chi-squared Benford logic │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. Read ONLY context_files for this task       │
│  2. Focus on ONLY spec_refs for this task       │
│  3. Generate/modify the output files            │
│  4. Run verify command                          │
│     ┌──────────────────────────┐                │
│     │ verify passes? ──YES──> proceed to next   │
│     │       │                  task              │
│     │      NO                                   │
│     │       v                                   │
│     │ Self-fix attempt 1/3                      │
│     │   Read error output                       │
│     │   Fix the specific issue                  │
│     │   Re-run verify                           │
│     │       │                                   │
│     │ Still failing after 3 attempts?           │
│     │       v                                   │
│     │ STOP → escalate to human                  │
│     └──────────────────────────┘                │
│                                                 │
│  5. Present diff for this task to human         │
└─────────────────────────────────────────────────┘
```

**Verify-fix loop rules:**
- After each file edit, run the task's `verify` command immediately
- If verify fails, Claude reads the error output and attempts a fix
- Maximum 3 self-fix attempts per task
- If still failing after 3 attempts, **STOP and escalate to human** -- don't guess
- Each fix attempt must address the specific error, not rewrite the whole file
- Log every attempt: what failed, what was tried, what the result was

**Task execution output:**

```
BUILD EXECUTION: SPEC-2026-Q2-001
══════════════════════════════════

T001 [Create BenfordAnalyzer skeleton]
  Context: src/quality/__init__.py, src/quality/isolation_forest.py
  Output:  src/quality/benford.py (new, 45 lines)
  Verify:  mypy ✔ | ruff ✔
  Status:  ✔ PASS (1st attempt)

T002 [Implement chi-squared logic]
  Context: src/quality/benford.py, src/quality/isolation_forest.py
  Output:  src/quality/benford.py (modified, +89 lines)
  Verify:  mypy ✔ | pytest ✔
  Status:  ✔ PASS (1st attempt)

T003 [Integrate into Stage 4]
  Context: src/quality/benford.py, src/pipeline/stage_quality.py
  Output:  src/pipeline/stage_quality.py (+12 lines), src/quality/__init__.py (+1 line)
  Verify:  mypy ✔ | pytest ✘ (ImportError: BenfordAnalyzer)
  Fix 1/3: Added missing import in __init__.py
  Verify:  mypy ✔ | pytest ✔
  Status:  ✔ PASS (2nd attempt)

T004 [Delta write for results]
  Context: src/quality/benford.py, src/data/
  Output:  src/quality/benford.py (+34 lines)
  Verify:  mypy ✔
  Status:  ✔ PASS (1st attempt)

══════════════════════════════════
RESULT: 4/4 tasks passed | 1 self-fix applied | 0 escalations
```

**HUMAN GATE -- Build Review:**

After all build tasks complete, the human reviews:
- [ ] Each task's diff matches the build plan intent
- [ ] Self-fix attempts were reasonable (not papering over deeper issues)
- [ ] No files were modified outside the declared outputs
- [ ] Verify commands all pass
- [ ] The combined diff makes sense as a whole

### 3.6 Phase 6: Test Plan Design (Claude + Human Gate)

Before writing any test code, Claude produces a **test plan** that the human must approve. This prevents wasted effort writing tests that miss the point or test the wrong thing.

```
You: "Design a test plan for SPEC-2026-Q2-001 covering unit, integration, and e2e"
```

Claude produces a test plan document with three tiers:

```yaml
# Test Plan for SPEC-2026-Q2-001
test_plan_version: 1
spec_id: "SPEC-2026-Q2-001"
generated_by: "Claude Code"
date: "2026-04-14"

# --- TIER 1: UNIT TESTS ---
unit_tests:
  location: "tests/test_quality/test_benford.py"
  fixtures_needed: ["mock_delta", "sample_gl_dataframe"]
  cases:
    - id: UT-1
      maps_to: AC-1
      name: "test_all_numeric_columns_analyzed"
      description: "Verify Benford runs on every numeric column in the dataframe"
      input: "DataFrame with 5 numeric cols + 3 string cols"
      expected: "Result contains entries for exactly 5 columns"
      edge_cases:
        - "Empty dataframe returns empty result (no crash)"
        - "Single-row dataframe returns result with low confidence flag"
        - "DataFrame with all-zero column skips that column"

    - id: UT-2
      maps_to: AC-2
      name: "test_chi_squared_default_threshold"
      description: "Verify default p-value threshold is 0.05"
      input: "DataFrame following Benford distribution"
      expected: "No anomalies flagged (p > 0.05)"

    - id: UT-3
      maps_to: AC-2
      name: "test_chi_squared_custom_threshold"
      description: "Verify configurable p-value threshold"
      input: "DataFrame with known deviation, threshold=0.10"
      expected: "Anomaly flagged at 0.10 but not at 0.01"

    - id: UT-4
      maps_to: AC-2
      name: "test_chi_squared_known_fraud_distribution"
      description: "Verify known non-Benford data is flagged"
      input: "Uniform random first digits (known non-Benford)"
      expected: "Anomaly flagged with p < 0.05"

    - id: UT-5
      maps_to: AC-1
      name: "test_large_dataset_performance"
      description: "Verify 1M rows processes under 60s (constraint)"
      input: "Synthetic 1M-row DataFrame"
      expected: "Completes in < 60 seconds"

# --- TIER 2: INTEGRATION TESTS ---
integration_tests:
  location: "tests/test_quality/test_benford_integration.py"
  requires: ["MockDeltaClient from conftest.py"]
  cases:
    - id: IT-1
      maps_to: AC-3
      name: "test_results_written_to_quality_results_table"
      description: "Verify Benford results are persisted to UC quality_results table"
      setup: "Run Benford on sample data with MockDeltaClient"
      expected: "mock_delta.tables['quality_results'] contains Benford entries"
      validates: "Write path through pipeline stage to Delta"

    - id: IT-2
      maps_to: [AC-1, AC-3]
      name: "test_pipeline_stage4_invokes_benford"
      description: "Verify stage_quality.py calls Benford as part of Stage 4"
      setup: "Run Stage 4 pipeline with mock dependencies"
      expected: "Benford results appear in stage output alongside other quality checks"
      validates: "Integration between pipeline orchestrator and Benford module"

    - id: IT-3
      maps_to: AC-3
      name: "test_results_schema_matches_uc_table"
      description: "Verify output schema matches Unity Catalog table DDL"
      setup: "Generate Benford result dict"
      expected: "All required columns present, types match"
      validates: "Schema contract between code and UC"

# --- TIER 3: E2E / PLAYWRIGHT TESTS ---
e2e_tests:
  location: "e2e/tests/23-benford-quality.spec.ts"
  requires: ["auth fixture", "api-helper", "sample-gl.csv"]
  base_url: "OMNIA_BASE_URL (deployed Databricks App)"
  cases:
    - id: E2E-1
      maps_to: [AC-1, AC-3]
      name: "Benford analysis runs via audit submission API"
      description: "Submit audit with Stage 4, verify Benford in quality results"
      steps:
        - "Upload sample-gl.csv via /v1/files/upload"
        - "Submit audit via /v1/audit/run with stages_to_run=[1,2,3,4]"
        - "Poll /v1/audit/{id}/status until stage 4 completes"
        - "GET /v1/audit/{id}/quality-results"
        - "Assert response contains benford_analysis entries"
      timeout: 120_000

    - id: E2E-2
      maps_to: AC-4
      name: "Benford anomalies appear in dashboard endpoint"
      description: "Verify flagged accounts surface in dashboard data"
      steps:
        - "Run audit with known anomalous data"
        - "GET /v1/audit/{id}/dashboards"
        - "Assert quality dashboard includes benford anomaly cards"
      timeout: 120_000

# --- COVERAGE SUMMARY ---
traceability:
  AC-1: [UT-1, UT-5, IT-2, E2E-1]
  AC-2: [UT-2, UT-3, UT-4]
  AC-3: [IT-1, IT-2, IT-3, E2E-1]
  AC-4: [E2E-2]

gaps: []  # No uncovered ACs
risks:
  - "E2E tests require deployed Databricks App -- skip in local CI"
  - "Performance test (UT-5) may be flaky on low-resource CI runners"
```

**HUMAN GATE -- Test Plan Approval:**

The human reviews the test plan BEFORE any test code is written. Checklist:

- [ ] Every acceptance criterion has tests at the appropriate tier(s)
- [ ] Edge cases are sensible and complete
- [ ] Integration tests validate real boundaries (not just mocking everything)
- [ ] E2E tests cover the critical user journey
- [ ] No redundant tests (testing the same thing at multiple tiers without reason)
- [ ] Performance and timeout values are realistic
- [ ] Fixtures and test data requirements are feasible
- [ ] Gaps and risks are acknowledged

**If the human rejects the test plan**, Claude revises and resubmits. No test code is written until the plan is approved.

---

### 3.7 Phase 7: Unit Test Generation (Claude + Human Gate)

After test plan approval, Claude writes unit tests first.

```
You: "Write the unit tests from the approved test plan for SPEC-2026-Q2-001"
```

**Claude follows these rules:**

1. **One test file per module** in `tests/test_{module}/` mirroring `src/{module}/`
2. **Use conftest.py fixtures** -- never inline test data or mock setup
3. **Follow the existing patterns** from [test_fraud_scorer.py](tests/test_agents/test_fraud_scorer.py):
   - `@pytest.mark.asyncio` for async functions
   - Import from `src.` paths
   - Use `TaskContext` pattern for agent tests
4. **Each test function maps to exactly one test plan case** (UT-1, UT-2, etc.)
5. **Docstring references the spec ID and AC**: `"""SPEC-2026-Q2-001 / AC-1: Benford on all numeric cols."""`

**Test structure:**

```python
"""Unit tests for Benford analysis — SPEC-2026-Q2-001."""

import pytest
import pandas as pd
from src.quality.benford import BenfordAnalyzer


@pytest.fixture
def sample_benford_df():
    """DataFrame whose first digits follow Benford's law."""
    # ... factory generating realistic data ...


@pytest.fixture
def sample_uniform_df():
    """DataFrame with uniform first digits (non-Benford, known anomaly)."""
    # ...


class TestBenfordAnalyzer:
    """Maps to SPEC-2026-Q2-001 acceptance criteria."""

    # UT-1 → AC-1
    @pytest.mark.asyncio
    async def test_all_numeric_columns_analyzed(self, sample_benford_df):
        """SPEC-2026-Q2-001 / AC-1: runs on every numeric column."""
        analyzer = BenfordAnalyzer()
        result = await analyzer.analyze(sample_benford_df)
        numeric_cols = sample_benford_df.select_dtypes(include="number").columns
        assert set(result.columns_analyzed) == set(numeric_cols)

    # UT-1 edge case: empty dataframe
    @pytest.mark.asyncio
    async def test_empty_dataframe_returns_empty(self):
        """SPEC-2026-Q2-001 / AC-1 edge: no crash on empty input."""
        analyzer = BenfordAnalyzer()
        result = await analyzer.analyze(pd.DataFrame())
        assert result.columns_analyzed == []
        assert result.anomalies == []

    # UT-2 → AC-2
    @pytest.mark.asyncio
    async def test_chi_squared_default_threshold(self, sample_benford_df):
        """SPEC-2026-Q2-001 / AC-2: default p=0.05, Benford data passes."""
        analyzer = BenfordAnalyzer()
        result = await analyzer.analyze(sample_benford_df)
        assert all(a.flagged is False for a in result.anomalies)

    # UT-3 → AC-2
    @pytest.mark.asyncio
    async def test_chi_squared_custom_threshold(self, sample_uniform_df):
        """SPEC-2026-Q2-001 / AC-2: configurable threshold."""
        analyzer = BenfordAnalyzer(p_value_threshold=0.10)
        result_loose = await analyzer.analyze(sample_uniform_df)
        analyzer_strict = BenfordAnalyzer(p_value_threshold=0.001)
        result_strict = await analyzer_strict.analyze(sample_uniform_df)
        # Uniform data should flag at 0.10 but maybe not at 0.001
        assert any(a.flagged for a in result_loose.anomalies)

    # UT-4 → AC-2
    @pytest.mark.asyncio
    async def test_known_fraud_distribution_flagged(self, sample_uniform_df):
        """SPEC-2026-Q2-001 / AC-2: uniform digits reliably detected."""
        analyzer = BenfordAnalyzer()
        result = await analyzer.analyze(sample_uniform_df)
        assert any(a.flagged for a in result.anomalies)

    # UT-5 → AC-1 (constraint)
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_dataset_under_60s(self):
        """SPEC-2026-Q2-001 / constraint: 1M rows < 60s."""
        import time
        large_df = pd.DataFrame({"amount": range(1, 1_000_001)})
        analyzer = BenfordAnalyzer()
        start = time.monotonic()
        await analyzer.analyze(large_df)
        elapsed = time.monotonic() - start
        assert elapsed < 60, f"Took {elapsed:.1f}s, limit is 60s"
```

**HUMAN GATE -- Unit Test Review:**

Claude presents the unit test code and runs it. The human validates:

- [ ] Each test maps to a test plan case (UT-1 through UT-N)
- [ ] Edge cases from the test plan are all implemented
- [ ] Test logic is correct (not just asserting `True`)
- [ ] Fixtures use realistic data, not trivial/hardcoded values
- [ ] No tests that simply re-implement the production logic
- [ ] Tests would actually FAIL if the feature were broken
- [ ] `pytest tests/test_quality/test_benford.py -v` output shown and all pass

```
Claude presents:
  UNIT TEST RESULTS: 8 passed, 0 failed, 0 skipped
  Coverage: src/quality/benford.py — 94% line coverage

  Traceability:
  UT-1 → AC-1  ✔ pass
  UT-2 → AC-2  ✔ pass
  UT-3 → AC-2  ✔ pass
  UT-4 → AC-2  ✔ pass
  UT-5 → AC-1  ✔ pass (23.4s)

  [Awaiting your approval to proceed to integration tests]
```

---

### 3.8 Phase 8: Integration Test Generation (Claude + Human Gate)

After unit tests are approved, Claude writes integration tests.

```
You: "Write the integration tests from the approved test plan for SPEC-2026-Q2-001"
```

**Integration tests validate boundaries between components:**
- Module-to-Delta writes (using `MockDeltaClient` from [conftest.py](tests/conftest.py))
- Pipeline stage orchestration (Stage 4 calling Benford)
- Schema contracts between code output and UC table DDL

**Claude follows these rules:**

1. **Suffix files with `_integration.py`**: `tests/test_quality/test_benford_integration.py`
2. **Use `MockDeltaClient`** from conftest.py for Delta operations -- never mock at the function level when an in-memory client exists
3. **Test through the pipeline boundary**, not just the module in isolation
4. **Validate data shapes and schemas**, not just "did it not crash"

**Test structure:**

```python
"""Integration tests for Benford → Delta → Pipeline — SPEC-2026-Q2-001."""

import pytest
from src.quality.benford import BenfordAnalyzer
from src.pipeline.stage_quality import StageQuality


class TestBenfordIntegration:
    """Validates Benford integrates correctly with Delta and Pipeline."""

    # IT-1 → AC-3
    @pytest.mark.asyncio
    async def test_results_written_to_quality_results_table(self, mock_delta):
        """SPEC-2026-Q2-001 / AC-3: results persisted to UC."""
        analyzer = BenfordAnalyzer(delta_client=mock_delta)
        # ... run analysis, then verify mock_delta.tables ...
        rows = mock_delta.tables.get("quality_results", [])
        assert len(rows) > 0
        assert all("benford" in r.get("method", "") for r in rows)

    # IT-2 → AC-1, AC-3
    @pytest.mark.asyncio
    async def test_pipeline_stage4_invokes_benford(self, mock_delta):
        """SPEC-2026-Q2-001 / AC-1+AC-3: Stage 4 includes Benford."""
        stage = StageQuality(delta_client=mock_delta)
        result = await stage.execute(audit_id="test-001", data={...})
        methods_run = [r["method"] for r in result.quality_checks]
        assert "benford_analysis" in methods_run

    # IT-3 → AC-3
    @pytest.mark.asyncio
    async def test_results_schema_matches_uc_table(self, mock_delta):
        """SPEC-2026-Q2-001 / AC-3: schema contract validation."""
        analyzer = BenfordAnalyzer(delta_client=mock_delta)
        # ... run analysis ...
        rows = mock_delta.tables.get("quality_results", [])
        required_cols = {"audit_id", "column_name", "method",
                         "p_value", "flagged", "timestamp"}
        for row in rows:
            assert required_cols.issubset(set(row.keys()))
```

**HUMAN GATE -- Integration Test Review:**

Claude presents the integration test code, runs it, and the human validates:

- [ ] Tests exercise real boundaries (module → Delta, pipeline → module)
- [ ] Uses `MockDeltaClient` correctly (not over-mocking or under-mocking)
- [ ] Schema assertions match the actual UC table DDL
- [ ] Tests would catch integration regressions (not just happy-path passthrough)
- [ ] No duplicate coverage of what unit tests already verify
- [ ] `pytest tests/test_quality/test_benford_integration.py -v` output shown

```
Claude presents:
  INTEGRATION TEST RESULTS: 3 passed, 0 failed, 0 skipped

  Traceability:
  IT-1 → AC-3  ✔ pass
  IT-2 → AC-1  ✔ pass
  IT-3 → AC-3  ✔ pass

  [Awaiting your approval to proceed to E2E tests]
```

---

### 3.9 Phase 9: E2E / Playwright Test Generation (Claude + Human Gate)

After integration tests are approved, Claude writes Playwright E2E tests.

```
You: "Write the E2E Playwright tests from the approved test plan for SPEC-2026-Q2-001"
```

**E2E tests validate the full user journey against the deployed Databricks App:**
- API requests through the real HTTP layer
- Authentication flow via the [auth fixture](e2e/fixtures/auth.ts)
- Audit submission → pipeline execution → result retrieval
- Dashboard data availability

**Claude follows the established Playwright patterns from the existing e2e suite:**

1. **File naming**: `e2e/tests/{NN}-{feature-name}.spec.ts` (next sequential number)
2. **Use existing helpers**: `submitAudit`, `uploadFile`, `pollAuditStatus` from [api-helper.ts](e2e/utils/api-helper.ts)
3. **Use the auth fixture**: `import { test, expect } from "../fixtures/auth"`
4. **Sequential execution**: `workers: 1` as configured in [playwright.config.ts](e2e/playwright.config.ts)
5. **120s timeout** for pipeline-dependent tests

**Test structure:**

```typescript
import * as path from "path";
import { test, expect } from "../fixtures/auth";
import { submitAudit, uploadFile, pollAuditStatus } from "../utils/api-helper";

const FIXTURES = path.resolve(__dirname, "../fixtures");

test.describe("Omnia AI — Benford Analysis E2E (SPEC-2026-Q2-001)", () => {

  // E2E-1 → AC-1, AC-3
  test("Benford analysis runs via audit submission API", async ({ authRequest }) => {
    // Step 1: Upload sample GL
    const fileId = await uploadFile(
      authRequest,
      path.join(FIXTURES, "sample-gl.csv"),
      "benford-e2e-001"
    );
    expect(fileId).toBeTruthy();

    // Step 2: Submit audit targeting stages 1-4
    const auditId = await submitAudit(authRequest, {
      engagement_name: "Benford E2E Test",
      client_name: "Benford Corp",
      audit_type: "financial",
      fiscal_year: "2025",
      materiality_threshold: 50000.0,
      erp_system: "sap_s4",
      knowledge_areas: ["finance"],
      stages_to_run: [1, 2, 3, 4],
      documents: [fileId],
      budget_usd: 10.0,
      language: "en",
      metadata: { test_run: true },
    });

    // Step 3: Poll until stage 4 completes
    const status = await pollAuditStatus(authRequest, auditId, 4);
    expect(status.stages_completed).toContain(4);

    // Step 4: Verify Benford results in quality output
    const qualityRes = await authRequest.get(
      `/v1/audit/${auditId}/quality-results`
    );
    expect(qualityRes.status()).toBe(200);
    const quality = await qualityRes.json();

    const benfordResults = quality.checks.filter(
      (c: any) => c.method === "benford_analysis"
    );
    expect(benfordResults.length).toBeGreaterThan(0);
    expect(benfordResults[0]).toHaveProperty("p_value");
    expect(benfordResults[0]).toHaveProperty("flagged");
  });

  // E2E-2 → AC-4
  test("Benford anomalies appear in dashboard endpoint", async ({ authRequest }) => {
    // Submit audit with known anomalous data
    const auditId = await submitAudit(authRequest, {
      engagement_name: "Benford Dashboard Test",
      client_name: "Anomaly Corp",
      audit_type: "financial",
      fiscal_year: "2025",
      materiality_threshold: 25000.0,
      erp_system: "sap_s4",
      knowledge_areas: ["finance"],
      stages_to_run: [1, 2, 3, 4, 5, 6],
      documents: [],
      budget_usd: 10.0,
      language: "en",
      metadata: { test_run: true, inject_anomalies: true },
    });

    const status = await pollAuditStatus(authRequest, auditId, 6);
    expect(status.stages_completed).toContain(6);

    // Verify dashboard includes Benford findings
    const dashRes = await authRequest.get(`/v1/audit/${auditId}/dashboards`);
    expect(dashRes.status()).toBe(200);
    const dashboards = await dashRes.json();

    const qualityDash = dashboards.find(
      (d: any) => d.type === "data_quality"
    );
    expect(qualityDash).toBeTruthy();
    expect(qualityDash.cards.some(
      (c: any) => c.analysis_type === "benford"
    )).toBe(true);
  });
});
```

**HUMAN GATE -- E2E Test Review:**

Claude presents the Playwright tests and the human validates:

- [ ] Tests use the established patterns from existing specs (auth fixture, api-helper)
- [ ] API endpoints called match the actual deployed routes
- [ ] Assertions verify meaningful business outcomes, not just HTTP 200
- [ ] Timeouts are appropriate for pipeline execution time
- [ ] Test data and fixtures are realistic
- [ ] Tests are idempotent (can run repeatedly without side effects)
- [ ] **Critical: human verifies the user journey matches how a real auditor would use the feature**

```
Claude presents:
  E2E TEST PLAN (not yet executed — requires deployed app):

  E2E-1 → AC-1, AC-3  📋 ready (needs OMNIA_BASE_URL)
  E2E-2 → AC-4        📋 ready (needs OMNIA_BASE_URL)

  To run:  cd e2e && OMNIA_BASE_URL=https://... npx playwright test 23-benford-quality.spec.ts

  [Awaiting your approval before marking tests as complete]
```

---

### 3.10 Phase 10: Test Execution and Full Traceability (Claude + Human Gate)

After all three test tiers are approved, Claude runs the full suite and produces the final traceability report.

```
Claude presents:
  ═══════════════════════════════════════════════════════════════
  FULL TEST REPORT — SPEC-2026-Q2-001: Benford Analysis
  ═══════════════════════════════════════════════════════════════

  UNIT TESTS (tests/test_quality/test_benford.py)
  ────────────────────────────────────────────────
  ✔ test_all_numeric_columns_analyzed          0.02s
  ✔ test_empty_dataframe_returns_empty          0.01s
  ✔ test_single_row_low_confidence             0.01s
  ✔ test_all_zero_column_skipped               0.01s
  ✔ test_chi_squared_default_threshold          0.03s
  ✔ test_chi_squared_custom_threshold           0.02s
  ✔ test_known_fraud_distribution_flagged       0.02s
  ✔ test_large_dataset_under_60s              23.40s
  Result: 8 passed | Coverage: 94%

  INTEGRATION TESTS (tests/test_quality/test_benford_integration.py)
  ──────────────────────────────────────────────────────────────────
  ✔ test_results_written_to_quality_results_table   0.05s
  ✔ test_pipeline_stage4_invokes_benford            0.12s
  ✔ test_results_schema_matches_uc_table            0.03s
  Result: 3 passed | All Delta writes verified

  E2E TESTS (e2e/tests/23-benford-quality.spec.ts)
  ─────────────────────────────────────────────────
  ✔ Benford analysis runs via audit submission API    45.2s
  ✔ Benford anomalies appear in dashboard endpoint    62.1s
  Result: 2 passed | Full pipeline validated

  TRACEABILITY MATRIX
  ───────────────────
  AC-1 │ UT-1 ✔  UT-5 ✔  IT-2 ✔  E2E-1 ✔  │ COVERED ✔
  AC-2 │ UT-2 ✔  UT-3 ✔  UT-4 ✔            │ COVERED ✔
  AC-3 │ IT-1 ✔  IT-2 ✔  IT-3 ✔  E2E-1 ✔  │ COVERED ✔
  AC-4 │ E2E-2 ✔                            │ COVERED ✔

  GAPS: None
  RISKS: Performance test (UT-5) at 23.4s — well within 60s limit

  ═══════════════════════════════════════════════════════════════
```

**HUMAN GATE -- Final Test Sign-Off:**

This is the last human gate before code can be merged. The human verifies:

- [ ] All acceptance criteria show COVERED in the traceability matrix
- [ ] No test failures or skips that were not pre-approved in the test plan
- [ ] Coverage meets the minimum threshold from the spec (90%)
- [ ] E2E tests ran against the actual deployed environment
- [ ] Performance constraints are met with margin
- [ ] The test suite can run in CI without manual intervention (except E2E)

---

### 3.11 Phase 11: Self-Review (Claude)

Before presenting to the human, Claude runs a self-review checklist:

```markdown
## Self-Review Checklist for SPEC-2026-Q2-001

- [ ] All acceptance criteria have passing tests at appropriate tier(s)
- [ ] Unit tests: all pass, coverage >= 90%
- [ ] Integration tests: all pass, Delta writes verified
- [ ] E2E tests: all pass (or pre-approved skip with reason)
- [ ] Traceability matrix: no gaps
- [ ] No new linting errors introduced
- [ ] Type checks pass
- [ ] No hardcoded secrets or credentials
- [ ] OpenTelemetry traces emitted (per constraints)
- [ ] Performance constraint met (1M rows < 60s)
- [ ] No files modified outside of declared scope
- [ ] Git diff is clean -- only intentional changes
- [ ] CHANGELOG or commit messages reference the spec ID
```

### 3.12 Phase 12: Human Final Review

The human does a final review of:
1. The complete diff (code + tests at all three tiers)
2. The full traceability matrix (AC -> unit -> integration -> e2e)
3. The self-review checklist
4. Test execution output for all tiers
5. Coverage report

Only after human approval does the code get merged.

---

## 4. CLAUDE.md Configuration for Spec-Driven Development

Add these instructions to your project's `CLAUDE.md` to enforce the workflow automatically:

```markdown
# Spec-Driven Development Rules

## Mandatory Workflow
1. NEVER write code without a spec. If the user asks for a change without a spec,
   help them write one first.
2. ALWAYS enter plan mode before implementing a spec. Get human approval on the plan.
3. ALWAYS create a feature branch named `spec/{SPEC-ID}-{short-description}`.
4. ALWAYS map tests to acceptance criteria. Every AC must have at least one test.
5. ALWAYS run the self-review checklist before presenting code to the human.

## Code Conventions
- Follow existing patterns in adjacent files
- Use type hints for all function signatures
- Emit OpenTelemetry spans for any function that takes > 1 second
- Log at INFO level for stage transitions, DEBUG for internals
- Raise domain-specific exceptions from src/errors/

## Testing Conventions
- Unit tests in tests/test_{module}/ mirroring src/{module}/
- Integration tests suffixed with _integration.py
- E2E tests in e2e/tests/
- Use conftest.py fixtures, never inline test data
- Minimum 90% line coverage for new code

## Human Gates (ALL Blocking)
- Plan approval: REQUIRED before implementation
- Test plan approval: REQUIRED before writing any test code
- Code review: REQUIRED before commit
- Unit test review: REQUIRED before proceeding to integration tests
- Integration test review: REQUIRED before proceeding to E2E tests
- E2E test review: REQUIRED before final sign-off
- Final test sign-off: REQUIRED before merge (full traceability matrix)
- Never force-push, never skip pre-commit hooks
- Never proceed to the next test tier without human approval

## Spec Location
- All specs live in specs/ directory
- Follow the YAML format defined in docs/SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md
```

---

## 5. Prompt Patterns for Each Phase

### 5.1 Spec Authoring Prompt

```
Read the HLD (Omnia_AI_HLD.md) and LLD (Omnia_AI_LLD.md) for context.
I need a spec for: [describe the feature].
Generate a YAML spec following the template in docs/SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md.
Ask me clarifying questions before finalizing.
```

### 5.2 Spec Validation Prompt

```
Validate specs/SPEC-{ID}.yaml deterministically:
  - Check all required fields are present
  - Verify depends_on targets exist (no cycles)
  - Verify scope modules exist on disk
  - Verify all ACs have unique IDs and are testable
  - Flag scope mismatches (e.g., touches_api but no API module in scope)
Report PASS/FAIL with any warnings. No LLM reasoning needed.
```

### 5.3 LLM Audit Prompt

```
Audit specs/SPEC-{ID}.yaml for semantic issues:
  - Ambiguities: vague requirements with multiple interpretations
  - Contradictions: conflicting ACs or constraints
  - Gaps: missing error paths, edge cases, boundary behaviors
  - Scope leaks: requirements implying changes outside declared scope
  - Testability: ACs that sound testable but aren't practically
  - Interface mismatches: assumed APIs/schemas that don't exist
Report findings with severity. Recommend whether to proceed or revise spec.
```

### 5.4 Build Plan Prompt

```
Read specs/SPEC-{ID}.yaml and create a structured build plan.
For EACH task specify:
  - id, title, spec_refs (only relevant ACs)
  - context_files (only files this task needs to see)
  - outputs (files created or modified)
  - verify (command to run after this task)
  - depends_on (task IDs)
Use narrow context: each task sees ONLY what it needs.
Present the task dependency graph for my review.
```

### 5.5 Build Execution Prompt

```
Execute the approved build plan for SPEC-{ID}.
For each task in dependency order:
  1. Read ONLY the context_files listed for that task
  2. Focus on ONLY the spec_refs for that task
  3. Generate/modify the output files
  4. Run the verify command immediately
  5. If verify fails: self-fix up to 3 attempts, then escalate
  6. Present the task diff before moving to the next task
Create branch spec/SPEC-{ID}-{short-name}.
Follow the coding conventions in CLAUDE.md.
```

### 5.6 Test Plan Design Prompt

```
Design a test plan for SPEC-{ID} covering all three tiers:
  - Unit tests: isolated logic, edge cases, performance constraints
  - Integration tests: module boundaries, Delta writes, pipeline orchestration
  - E2E / Playwright: full API journeys against the deployed app

For each test case specify: ID, maps_to (AC), name, input, expected output.
Include edge cases: empty input, single row, max scale, invalid data, error paths.
Generate a traceability matrix showing AC -> test case mapping at each tier.
Present the plan for my review BEFORE writing any test code.
```

### 5.7 Unit Test Prompt

```
Write unit tests from the approved test plan for SPEC-{ID}.
Follow patterns in tests/conftest.py and existing test files.
Use fixtures, not inline data. Map each test to a test plan case (UT-N).
Run pytest and show results with coverage.
Present for my review before proceeding to integration tests.
```

### 5.8 Integration Test Prompt

```
Write integration tests from the approved test plan for SPEC-{ID}.
Use MockDeltaClient from conftest.py for Delta operations.
Test through pipeline boundaries, not just module internals.
Validate schemas match UC table DDL.
Suffix files with _integration.py.
Run pytest and show results.
Present for my review before proceeding to E2E tests.
```

### 5.9 E2E / Playwright Test Prompt

```
Write Playwright E2E tests from the approved test plan for SPEC-{ID}.
Follow patterns from existing e2e/tests/*.spec.ts files.
Use auth fixture, api-helper utilities (submitAudit, uploadFile, pollAuditStatus).
File name: e2e/tests/{next-number}-{feature}.spec.ts.
Test the full user journey: upload → submit → poll → verify results.
Present for my review. Note which tests require the deployed app.
```

### 5.10 Full Test Execution Prompt

```
Run all tests for SPEC-{ID} across all three tiers.
Generate the full traceability matrix (AC → unit → integration → e2e).
Report: pass/fail per test, coverage %, any gaps or risks.
Present the final test report for sign-off.
```

### 5.11 Self-Review Prompt

```
Run the self-review checklist for SPEC-{ID}.
Check: tests pass, lint clean, types clean, no scope creep,
no secrets, constraints met. Report any failures.
```

---

## 6. Defect Prevention Strategies

### 6.1 Shift-Left with Spec Validation

Catch defects at the spec level before any code is written:

| Defect Type | Prevention at Spec Level |
|-------------|-------------------------|
| Missing requirements | Acceptance criteria checklist |
| Scope creep | Explicit `scope.modules` declaration |
| Performance regression | `constraints` with measurable thresholds |
| Security vulnerabilities | `constraints` requiring input validation |
| Integration failures | `depends_on` and `blocks` declarations |

### 6.2 Claude Code Self-Checks During Implementation

Configure Claude to run these checks automatically:

```
After EVERY file edit:
  1. Re-read the file to verify the edit applied correctly
  2. Run linting on the changed file
  3. Run type checking on the changed file
  4. Run existing tests to catch regressions

After ALL implementation is complete:
  1. Run full test suite
  2. Check git diff against spec scope -- flag any out-of-scope changes
  3. Verify all acceptance criteria are covered by tests
  4. Generate the self-review checklist
```

### 6.3 Common Defect Patterns and Mitigations

| Pattern | Cause | Mitigation |
|---------|-------|------------|
| **Works locally, fails in pipeline** | Environment differences | Spec must declare runtime constraints; integration tests run in CI |
| **Missing error handling** | Happy-path-only implementation | Spec includes error scenarios in acceptance criteria |
| **Breaking adjacent features** | Insufficient regression testing | Run full test suite, not just new tests |
| **Incorrect data types** | Implicit type coercion | Type hints + runtime validation at boundaries |
| **Stale test data** | Hardcoded values | Use fixtures and factories from conftest.py |
| **Over-engineering** | Claude adding "improvements" | CLAUDE.md rule: implement exactly what spec says |

### 6.4 The Defect Feedback Loop

When a defect is found post-implementation:

```
1. Document the defect as a bugfix spec (specs/SPEC-{ID}-bugfix.yaml)
2. Include root_cause and reproduction_steps
3. Add a regression test FIRST (red-green-refactor)
4. Fix the code
5. Update the original spec if requirements were ambiguous
6. Save a Claude Code memory: what went wrong and how to prevent it
```

---

## 7. Human-in-the-Loop Gate Design

### 7.1 Gate Taxonomy

| Gate | Phase | Trigger | Blocker? | Timeout Action |
|------|-------|---------|----------|----------------|
| **Spec Approval** | 1 | New spec created | Yes | Cannot proceed |
| **Spec Validation** | 2 | Deterministic checks run | No | Fix and re-run (instant) |
| **Audit Review** | 3 | LLM audit findings presented | Yes | Cannot proceed to planning |
| **Build Plan Approval** | 4 | Structured task graph presented | Yes | Cannot write code |
| **Build Review** | 5 | Task diffs + verify results | Yes | Cannot proceed to testing |
| **Test Plan Approval** | 6 | 3-tier test plan presented | Yes | Cannot write tests |
| **Unit Test Review** | 7 | Unit tests + results presented | Yes | Cannot proceed to integration |
| **Integration Test Review** | 8 | Integration tests + results presented | Yes | Cannot proceed to E2E |
| **E2E Test Review** | 9 | Playwright tests presented | Yes | Cannot proceed to final |
| **Final Test Sign-Off** | 10 | Full traceability matrix | Yes | Cannot merge |
| **Deploy Approval** | 12 | All checks pass | Yes | Cannot deploy |
| **Self-Fix Escalation** | 5 | Verify fails 3x during build | Yes | Cannot continue task |
| **Anomaly Review** | Any | Unusual pattern detected | No | Auto-flag, continue |

### 7.2 When to Escalate to Human

Claude should pause and ask the human when:

- The spec is ambiguous or contradictory
- Implementation requires changes outside the declared scope
- A test fails and the fix isn't obvious
- Performance constraints can't be met with the current approach
- Security-sensitive code is involved (auth, encryption, PII handling)
- A design decision has multiple valid approaches with different trade-offs

### 7.3 When NOT to Escalate

Claude should proceed autonomously when:

- The change is within declared scope and follows existing patterns
- Tests pass and coverage meets the threshold
- Linting and type checks are clean
- The change is a straightforward mapping from spec to code

---

## 8. Project Directory Structure

```
omnia_ai/
  specs/                          # All spec files (YAML)
    SPEC-2026-Q2-001.yaml
    SPEC-2026-Q2-002.yaml
    templates/                    # Spec templates by type
      feature.yaml
      bugfix.yaml
      refactor.yaml
      spike.yaml
  docs/
    SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md   # This file
    stages/                       # Per-stage documentation
  src/                            # Source code
    agents/
    api/
    auth/
    config/
    data/
    errors/
    eval/
    pipeline/
    quality/
    ...
  tests/                          # Test code (mirrors src/)
    test_agents/
    test_api/
    test_eval/
    ...
  e2e/                            # End-to-end tests (Playwright)
    tests/
    fixtures/
    utils/
  CLAUDE.md                       # Claude Code project instructions
```

---

## 9. Metrics and Continuous Improvement

### 9.1 Track These Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Spec-to-code fidelity | 100% AC covered | Traceability matrix |
| Defect escape rate | < 5% of specs need bugfix | Bugfix specs / total specs |
| Human gate rejection rate | < 20% | Rejected plans / total plans |
| Test coverage on new code | > 90% | pytest-cov |
| Time from spec to merge | Trending down | Git timestamps |
| Out-of-scope changes | 0 per spec | Diff vs. scope declaration |

### 9.2 Retrospective Process

After every 10 specs completed:

1. Review defect escape rate -- what slipped through?
2. Review gate rejection reasons -- are specs unclear?
3. Update spec templates if patterns emerge
4. Update CLAUDE.md if Claude keeps making the same mistake
5. Save learnings as Claude Code feedback memories

---

## 10. Quick Reference: One-Page Cheat Sheet

```
SPEC-DRIVEN DEVELOPMENT WITH CLAUDE CODE (v2 — with Ossature patterns)
========================================================================

 1. WRITE SPEC       Human writes YAML spec with acceptance criteria
 2. VALIDATE         Deterministic checks (no LLM): deps, cycles, schema
 3. AUDIT            LLM finds ambiguities, gaps, contradictions  --> HUMAN REVIEWS
 4. BUILD PLAN       Structured task graph with narrow context     --> HUMAN APPROVES
 5. BUILD            Task-by-task with verify + self-fix loop      --> HUMAN REVIEWS
 6. TEST PLAN        Claude designs 3-tier tests                   --> HUMAN APPROVES
 7. UNIT TESTS       Claude writes + runs units                    --> HUMAN VALIDATES
 8. INTEGRATION      Claude writes + runs integ.                   --> HUMAN VALIDATES
 9. E2E / PLAYWRIGHT Claude writes + runs e2e                      --> HUMAN VALIDATES
10. FULL REPORT      Traceability matrix + report                  --> HUMAN SIGN-OFF
11. SELF-CHECK       Claude runs lint, types, scope check
12. MERGE            Code merged to main
13. RETRO            Track metrics, update templates, save memories

KEY RULES:
  - No code without a spec
  - Validate before audit, audit before plan
  - Each build task sees ONLY its spec_refs + context_files (narrow context)
  - Verify after EVERY build task, self-fix up to 3x, then escalate
  - No test code without an approved test plan
  - Human validates tests at EVERY tier (unit, integration, e2e)
  - Every acceptance criterion must have tests at appropriate tier(s)
  - Claude implements exactly what the spec says -- no more
  - When in doubt, Claude asks the human

OSSATURE-INSPIRED CONCEPTS:
  Validate     Deterministic schema/dep checks — instant, no LLM
  Audit        LLM semantic review — ambiguities, gaps, contradictions
  Narrow ctx   Each task sees only its spec sections + needed files
  Verify loop  Run verify after each task; self-fix up to 3 attempts
  Interface    Downstream tasks see only public interface, not implementation

TEST TIERS:
  Unit        tests/test_{module}/                    Fast, isolated, edge cases
  Integration tests/test_{module}/*_integration.py    Real boundaries, Delta, pipeline
  E2E         e2e/tests/{NN}-{name}.spec.ts           Full API journey, Playwright

PROMPT PATTERN:
  "Read specs/SPEC-{ID}.yaml and [validate|audit|build-plan|build|
   test-plan|unit-test|integration-test|e2e-test|full-report|review]
   following docs/SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md"
```

---

## 11. Industry References and Influences

This process synthesizes ideas from across the AI-assisted development landscape:

### Core Frameworks

| Source | Key Concept Adopted | URL |
|--------|-------------------|-----|
| **Ossature** | Validate/Audit/Build pipeline, narrow context per task, verify-fix loop, SMD spec format | [ossature.dev/blog/introducing-ossature](https://ossature.dev/blog/introducing-ossature/) |
| **OpenAI Harness Engineering** | 5 months building constraints, not code; agents work best in strict, predictable environments | [openai.com/index/harness-engineering](https://openai.com/index/harness-engineering/) |
| **Martin Fowler / Birgitta Bockeler -- Harness Engineering** | Constrain solution space; trade flexibility for reliability | [martinfowler.com/articles/exploring-gen-ai/harness-engineering.html](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) |
| **Martin Fowler / Kief Morris -- Humans and Agents** | "On the loop" vs "in the loop" -- invest in the harness, not line-by-line review | [martinfowler.com/articles/exploring-gen-ai/humans-and-agents.html](https://martinfowler.com/articles/exploring-gen-ai/humans-and-agents.html) |
| **Martin Fowler / Bockeler -- SDD Tools** | Spec-driven dev tools comparison (Kiro, spec-kit, Tessl); risk of "Verschlimmbesserung" | [martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) |

### Additional Resources to Study

| Resource | What It Covers | Why It Matters |
|----------|---------------|----------------|
| **Kiro (AWS)** | AI IDE with spec-driven workflows; auto-generates specs, plans, and code | Comparison: heavier workflow with user stories, may be overkill per Bockeler |
| **spec-kit** | Lightweight spec files for Claude Code / Cursor | Comparison: simpler than our approach, may under-constrain |
| **Tessl** | Autonomous spec-to-code with multi-agent architecture | Comparison: less human-in-the-loop than our approach |
| **Anthropic Claude Code Best Practices** | Official patterns for CLAUDE.md, plan mode, hooks, and memory | [docs.anthropic.com/en/docs/claude-code](https://docs.anthropic.com/en/docs/claude-code) |
| **Ossature Examples** | Real projects generated with Ossature (Python, Zig, Rust, Lua) | [github.com/ossature/ossature-examples](https://github.com/ossature/ossature-examples) |
| **Ossature Docs** | Full documentation for the validate/audit/build workflow | [docs.ossature.dev](https://docs.ossature.dev) |
| **Martin Fowler Exploring Gen AI (full series)** | Comprehensive multi-author series on AI-assisted software engineering | [martinfowler.com/articles/exploring-gen-ai.html](https://martinfowler.com/articles/exploring-gen-ai.html) |

### Key Principles Distilled from Industry

1. **"The hard problem isn't code generation -- it's the scaffolding"** (OpenAI) -- Our harness IS the spec + build plan + verify loop + human gates.
2. **"Agents work best in strict, predictable environments"** (OpenAI) -- Narrow context per task, explicit outputs, verify commands.
3. **"Constrain the solution space"** (Bockeler) -- Specs with explicit ACs, scope declarations, and constraints.
4. **"On the loop, not in the loop"** (Morris) -- Human reviews harness output at gates, doesn't watch every keystroke.
5. **"Less context means less drift"** (Ossature) -- Each task assembled from scratch with only what it needs.
6. **"Verify at generation time, not after"** (Ossature) -- Catch breakage immediately, not during integration.
7. **"The spec describes behavior, the plan describes tasks"** (Ossature) -- Keep concerns separated.
