# Harness Engineering for Agentic Development

## Omnia AI -- Development Scaffold for Claude Code Sessions

**Version:** 1.0 | **Date:** April 2026
**Extends:** [SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md](SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md) (does not replace)
**Grounded in:** [OpenAI Harness Engineering](https://openai.com/index/harness-engineering/) | [Bockeler/Fowler Harness Engineering](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) | [Stripe Minions](https://stripe.com/blog/minions)

---

## 1. Philosophy

> "The hard problem isn't code generation -- it's the scaffolding."
> -- OpenAI Harness Engineering, Feb 2026

> "Agents are most effective in environments with strict boundaries and predictable structure."
> -- OpenAI Harness Engineering, Feb 2026

> "A well-built outer harness serves two goals: it increases the probability that the agent gets it right in the first place, and it provides a feedback loop that self-corrects as many issues as possible before they even reach human eyes."
> -- Birgitta Bockeler, Thoughtworks, Apr 2026

Harness engineering wraps the coding agent in a scaffold of **guides** (feedforward -- steer before the agent acts) and **sensors** (feedback -- observe after the agent acts and self-correct). Both can be **computational** (deterministic, fast, CPU) or **inferential** (LLM-based, semantic, slower).

```
                    THE HARNESS LIFECYCLE
                    =====================

  ┌─────────────────────────────────────────────────────────────┐
  │                    FEEDFORWARD (Guides)                       │
  │  CLAUDE.md rules, spec templates, narrow context, type hints │
  │  LLM audit, system prompts, design docs                      │
  └──────────────────────────┬──────────────────────────────────┘
                             │
                             v
  ┌──────────┐     ┌──────────────────┐     ┌──────────────┐
  │ PRE-DEV  │────>│  DEVELOPMENT     │────>│  POST-DEV    │
  │ Harness  │     │  (Agent coding)  │     │  Harness     │
  │          │     │                  │     │              │
  │ env check│     │ budget tracking  │     │ regression   │
  │ spec val │     │ in-loop quality  │     │ coverage     │
  │ baseline │     │ context mgmt    │     │ DDL sync     │
  │ branch   │     │ self-heal loop  │     │ traceability │
  └──────────┘     └────────┬─────────┘     └──────────────┘
                             │
                             v
  ┌─────────────────────────────────────────────────────────────┐
  │                    FEEDBACK (Sensors)                         │
  │  ruff, mypy, structural tests, GC sweeps (computational)     │
  │  LLM code review, eval judges, semantic dedup (inferential)  │
  └─────────────────────────────────────────────────────────────┘
                             │
                             v
  ┌─────────────────────────────────────────────────────────────┐
  │               GARBAGE COLLECTION (Continuous)                │
  │  Architecture drift, doc staleness, dead code, budget audit  │
  └─────────────────────────────────────────────────────────────┘
```

### 1.1 The Bockeler Model Applied to Omnia AI

| | **Computational** (fast, deterministic) | **Inferential** (LLM-based, semantic) |
|---|---|---|
| **Feedforward (guides)** | CLAUDE.md rules, spec templates, narrow context, type hints, `PHASE_STAGES` boundaries, `LLMLimits` budgets | LLM audit (Phase 3), system prompts, spec descriptions, design docs |
| **Feedback (sensors)** | ruff, mypy, structural tests, DDL sync, traceability check, GC sweeps, PostToolUse hooks | Eval judges (hallucination, reasoning, domain, safety), LLM self-review, GC doc semantic check |

### 1.2 Big Tech Benchmark

| Concept | Source | What They Do | Our Implementation |
|---------|--------|-------------|-------------------|
| Custom linters with fix instructions | OpenAI | Error messages inject remediation into agent context | `scripts/harness/lint_*.py` with actionable messages |
| Rigid layered architecture | OpenAI | Types->Config->Repo->Service->Runtime->UI, enforced mechanically | `PHASE_STAGES` (DATA->PLAN->TEST->COMPLY->INTEL->GOVERN) enforced by `lint_imports.py` + `test_layer_boundaries.py` |
| AGENTS.md as map, not encyclopedia | OpenAI | ~100 lines pointing to deeper docs | CLAUDE.md as entry point, deep docs in `docs/` |
| Garbage collection agents | OpenAI | Recurring agents scan for drift, open fix PRs | 4 GC scripts: `gc_architecture.py`, `gc_docs.py`, `gc_dead_code.py`, `gc_budget_audit.py` |
| Pre-push heuristic hooks | Stripe | Run relevant linters based on changed files | PostToolUse hook runs `post_write_check.py` on every file write |
| Shift feedback left | Stripe/Bockeler | Checks as far left as possible | In-the-loop ruff/mypy on every file write, not just CI |
| Harness templates | Bockeler/Ashby | Pre-defined topologies with bundled sensors | Spec templates with `harness:` section (budget, quality gates, constraints) |
| Approved fixtures | Thoughtworks | Pre-validated test data for verification | `conftest.py` (MockDeltaClient), golden set eval (`src/eval/scorers/golden_set.py`) |
| Ambient affordances | Letcher/TW | Structural properties that make codebase agent-friendly | Strong typing, clear module boundaries, 6-phase separation |
| Variety reduction (Ashby's Law) | Bockeler | Constrain what agent can produce | Spec constraints, scope declarations, narrow context per task |
| Agent observability access | OpenAI | Logs/metrics/traces queryable by agent | `src/observability/` (tracing, metrics, structured_logger) exposed in context |
| End-to-end agent loop | OpenAI | Validate->Fix->Verify->PR->Merge autonomously | Verify-fix loop (3 retries) + self-heal pipeline |

---

## 2. Pillar 1: Budgeted Development

### 2.1 Development Budget Model

Mirrors the `LLMLimits` pattern from `src/config/llm_limits.py`:

```python
@dataclass(frozen=True)
class DevBudget:
    """Development-time budget constraints per spec."""
    max_tokens_per_spec: int = 500_000
    max_tokens_per_phase: dict[str, float] = field(default_factory=lambda: {
        "validate": 0.05,   # 5% -- deterministic, minimal LLM
        "audit": 0.10,      # 10% -- LLM semantic review
        "plan": 0.15,       # 15% -- build plan generation
        "build": 0.40,      # 40% -- implementation
        "test": 0.25,       # 25% -- 3-tier test generation
        "review": 0.05,     # 5% -- self-review + cleanup
    })
    max_cost_per_spec_usd: float = 10.0
    max_requests_per_task: int = 15
    cache_hit_target_pct: float = 0.30
    complexity_multipliers: dict[str, float] = field(default_factory=lambda: {
        "low": 0.2,         # Simple bugfix, 1 file -- 100K tokens
        "medium": 1.0,      # New feature, 3-5 files -- 500K tokens
        "high": 2.0,        # Cross-cutting refactor -- 1M tokens
        "critical": 4.0,    # New pipeline stage -- 2M tokens
    })
```

### 2.2 Request Optimization Patterns

From OpenAI: *"Context is a scarce resource. A giant instruction file crowds out the task."*

| Pattern | What | Token Savings |
|---------|------|--------------|
| **Batch file reads** | Read 5 related files in one request, not 5 separate requests | ~40% |
| **Front-load context** | Put spec + relevant code in first message, not drip-fed | ~25% |
| **Narrow context per task** | Each task sees only its `spec_refs` + `context_files` | ~50% |
| **Use /compact** | Compress when context exceeds 60% of window | ~30% |
| **Progressive disclosure** | Start with map (CLAUDE.md), navigate deeper as needed | ~35% |

### 2.3 Session Cost Tracking

`scripts/harness/track_session_cost.py` emits `MetricPoint` via `MetricsCollector`:

```python
metrics.emit("harness.session_tokens", total_tokens, spec_id=spec_id, phase=phase)
metrics.emit("harness.session_cost_usd", total_cost, spec_id=spec_id, phase=phase)
metrics.emit("harness.budget_remaining_pct", remaining_pct, spec_id=spec_id)
```

Uses `CircuitBreaker(failure_threshold=3)`: if 3 consecutive tasks exceed per-task budget, pause and report.

---

## 3. Pillar 2: Internal Quality Assessment

### 3.1 Development Quality Gates

Extends the `QualityGate` pattern from `src/quality/quality_gate.py`:

```python
# Development-time quality thresholds
DEV_QUALITY_GATES = {
    "draft":        DevQualityGate("draft", threshold=0.70),
    "review_ready": DevQualityGate("review_ready", threshold=0.85),
    "merge_ready":  DevQualityGate("merge_ready", threshold=0.95),
}
```

### 3.2 In-the-Loop Checks (Shift Left)

Wired via `.claude/settings.local.json` PostToolUse hooks:

| Trigger | Check | Speed | What Catches |
|---------|-------|-------|-------------|
| Every file write | `ruff check {file}` | < 2s | Style, unused imports, complexity |
| Every file write | `mypy {file}` | < 3s | Type errors, missing annotations |
| Every 3 file writes | `pytest {affected_tests}` | < 30s | Regressions in related code |

This is what Stripe calls "pre-push heuristic hooks" and Bockeler calls "keeping quality left."

### 3.3 Quality Score Components

| Component | Weight | Tool | Target |
|-----------|--------|------|--------|
| Lint violations (ruff) | 25% | `ruff check --statistics` | 0 new violations |
| Type errors (mypy) | 25% | `mypy --no-error-summary` | 0 new errors |
| Test coverage (pytest-cov) | 20% | `pytest --cov` | >= 90% on new code |
| Cyclomatic complexity | 15% | `ruff` (C901 rule) | <= 10 per function |
| Pattern conformance | 15% | Structural tests | Matches adjacent code |

### 3.4 Custom Lint Messages with Remediation

From OpenAI: *"Because the lints are custom, we write the error messages to inject remediation instructions into agent context."*

Our custom linters (`scripts/harness/lint_*.py`) output messages like:

```
VIOLATION: src/agents/test/control_tester.py imports from src/agents/intel/opinion_drafter.py
  PHASE BOUNDARY CROSSED: TEST -> INTEL
  FIX: Move shared logic to src/config/ or src/data/ (shared infrastructure).
  If inter-phase communication is needed, use A2A protocol (src/agents/a2a_protocol.py).
```

---

## 4. Pillar 3: Context Engineering

### 4.1 CLAUDE.md as Living Documentation

From OpenAI: *"We treat AGENTS.md as the table of contents... structured docs/ directory as the system of record."*

CLAUDE.md serves as the **map** (~200 lines). Deep docs live in:
- `docs/SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md` -- full 12-phase workflow
- `docs/HARNESS_ENGINEERING.md` -- this document
- `Omnia_AI_HLD.md` -- high-level design
- `Omnia_AI_LLD.md` -- low-level design
- `specs/templates/` -- spec templates
- `.claude/memory/` -- cross-session learnings

### 4.2 Dynamic Context Sources

| Source | What Agent Sees | When Used |
|--------|----------------|-----------|
| Recent test results | Last pytest run: pass/fail counts, coverage map | Before writing code in a module |
| Recent errors | Last 50 structlog JSON lines from module | When debugging or modifying error-prone code |
| Coverage gaps | Modules below 90% coverage threshold | When planning test strategy |
| Observability data | OTel traces, MetricPoints from recent runs | When optimizing performance-critical paths |
| Spec dependency graph | Which specs block/depend on current work | During spec validation (Phase 2) |

### 4.3 Cross-Session Learning

`.claude/memory/` stores persistent learnings:
- `feedback_*.md` -- corrections and confirmations from user
- `project_*.md` -- ongoing work context, decisions, deadlines
- `reference_*.md` -- pointers to external resources
- `user_*.md` -- user preferences and expertise

GC agents prune stale memories and flag contradictions.

### 4.4 Progressive Disclosure (OpenAI Pattern)

```
Request arrives
  |
  v
CLAUDE.md (~200 lines) -- map, rules, commands
  |
  v
Agent reads spec YAML -- scoped context (spec_refs + context_files)
  |
  v
Agent reads relevant src/ files -- only what the task needs
  |
  v
Agent reads docs/ if needed -- deep architectural context
```

---

## 5. Pillar 4: Architectural Constraints

From OpenAI: *"We built the application around a rigid architectural model. Each business domain is divided into a fixed set of layers, with strictly validated dependency directions."*

### 5.1 Layer Boundary Enforcement

Omnia AI has 6 phases, each owning specific agent directories:

```
PHASE_STAGES (from src/config/constants.py):
  DATA:   src/agents/data/     (stages 1-4)
  PLAN:   src/agents/plan/     (stages 5-8)
  TEST:   src/agents/test/     (stages 9-12)
  COMPLY: src/agents/comply/   (stages 13-16)
  INTEL:  src/agents/intel/    (stages 17-20)
  GOVERN: src/agents/govern/   (stages 21-24)

ALLOWED cross-phase imports:
  src/config/        -- constants, settings, limits
  src/errors/        -- exception hierarchy
  src/observability/ -- tracing, metrics, logging
  src/memory/        -- agent memory
  src/data/          -- data access layer
  src/security/      -- auth, permissions
  src/api/           -- API layer
  src/mcp/           -- tool registry
  src/quality/       -- quality gates
  src/eval/          -- evaluation framework
  src/pipeline/      -- orchestration

DISALLOWED:
  src/agents/data/ cannot import from src/agents/test/
  src/agents/test/ cannot import from src/agents/intel/
  (any cross-phase agent directory import)
```

Enforced by:
- `scripts/harness/lint_imports.py` -- AST-based import graph analysis
- `tests/test_harness/test_layer_boundaries.py` -- pytest structural test

### 5.2 Agent Conformance

Every agent in `src/agents/` must:
1. Inherit from `BaseAgent`, `ReasoningAgent`, `ActionAgent`, or `EvaluationAgent`
2. Have a `config` class attribute of type `AgentConfig`
3. Implement `_execute_step(self, task: TaskContext, iteration: int) -> AgentResult`

Enforced by:
- `scripts/harness/lint_agents.py` -- AST-based conformance check
- `tests/test_harness/test_agent_conformance.py` -- pytest structural test

### 5.3 Exception Hierarchy

Every exception in `src/errors/exceptions.py` must:
1. Inherit from `OmniaError`
2. Have `status_code` and `error_code` class attributes

Enforced by `tests/test_harness/test_exception_hierarchy.py`.

### 5.4 Spec Schema Validation

Every YAML spec in `specs/` must:
1. Have `spec_id` matching pattern `SPEC-{YYYY}-Q{N}-{NNN}`
2. Have all required fields (description, scope, acceptance_criteria, constraints, human_gates, eval)
3. Have unique AC IDs
4. Reference only existing modules in `scope.modules`
5. Have an acyclic dependency graph

Enforced by:
- `scripts/harness/validate_specs.py` -- JSON schema validation
- `tests/test_harness/test_spec_schema.py` -- pytest structural test

### 5.5 DDL-to-Model Sync

Pydantic models in `src/` must match column definitions in `sql/ddl/001_core_tables.sql`.

Enforced by:
- `scripts/harness/validate_ddl.py` -- column name comparison
- `tests/test_harness/test_ddl_sync.py` -- pytest structural test

### 5.6 Pipeline Completeness

All 24 stages defined in `STAGE_NAMES` must:
1. Have a registered agent in the factory
2. Have dependency entries in `STAGE_DEPENDENCIES`
3. Form an acyclic dependency graph
4. Have no orphan stages (stages with no path from stage 1)

Enforced by `tests/test_harness/test_pipeline_completeness.py`.

---

## 6. Pillar 5: Garbage Collection Agents

From OpenAI: *"On a regular cadence, we have a set of background Codex tasks that scan for deviations, update quality grades, and open targeted refactoring pull requests."*

### 6.1 Architecture Drift Agent (`gc_architecture.py`)

| What | How | Cadence |
|------|-----|---------|
| Run all structural tests | `pytest tests/test_harness/ -v` | Daily |
| Run all custom linters | `lint_imports.py` + `lint_agents.py` | Daily |
| Compare against baseline | Diff new violations vs `.harness/baseline.json` | Daily |
| Report drift | Structured JSON: new violations, resolved violations | Daily |

### 6.2 Documentation Consistency Agent (`gc_docs.py`)

| What | How | Cadence |
|------|-----|---------|
| Parse CLAUDE.md for file paths | Regex extraction of paths | Weekly |
| Check referenced files exist | `pathlib.Path.exists()` | Weekly |
| Check referenced classes exist | grep for class definitions | Weekly |
| Flag stale sections | Report references to moved/deleted code | Weekly |

### 6.3 Dead Code / Entropy Agent (`gc_dead_code.py`)

| What | How | Cadence |
|------|-----|---------|
| Unused imports | AST parse + cross-reference (beyond ruff) | Weekly |
| Orphaned test files | Tests referencing spec IDs that don't exist | Weekly |
| Functions with zero callers | AST call graph analysis within modules | Weekly |
| Stale spec references | Specs referencing modules that moved | Weekly |

### 6.4 Budget Audit Agent (`gc_budget_audit.py`)

| What | How | Cadence |
|------|-----|---------|
| Aggregate session costs | Read `.harness/session_logs/*.json` | Per spec completion |
| Compare actual vs budgeted | Budget from spec YAML vs actual tokens/cost | Per spec completion |
| Recommend adjustments | Flag specs that exceeded budget and why | Per spec completion |
| Track trends | Per-phase cost distribution over time | Monthly |

---

## 7. Pillar 6: Pre/Post Development Harness + Self-Healing Pipeline

### 7.1 Pre-Development Checks (`pre_dev.py`)

```
$ python scripts/harness/pre_dev.py SPEC-2026-Q2-001

PRE-DEVELOPMENT CHECK: SPEC-2026-Q2-001
========================================
Environment:
  Python version    ✔  3.11.9
  ruff available    ✔  0.4.2
  mypy available    ✔  1.8.0
  pytest available  ✔  8.1.1

Spec Readiness:
  File exists       ✔  specs/SPEC-2026-Q2-001.yaml
  Schema valid      ✔  All required fields present
  Dependencies met  ✔  No unresolved depends_on
  Modules exist     ✔  src/quality, src/pipeline

Baseline Snapshot:
  ruff violations   42 (current count, saved to baseline)
  mypy errors       3  (current count, saved to baseline)
  pytest pass/fail  127/0 (current count, saved to baseline)
  coverage          87.3% (current, saved to baseline)

Branch:
  Created           spec/SPEC-2026-Q2-001-benford-analysis

RESULT: READY -- proceed to Phase 2 (Validation)
```

### 7.2 Post-Development Checks (`post_dev.py`)

```
$ python scripts/harness/post_dev.py SPEC-2026-Q2-001

POST-DEVELOPMENT CHECK: SPEC-2026-Q2-001
=========================================
Regression:
  ruff violations   42 -> 42  ✔  No new violations
  mypy errors       3  -> 3   ✔  No new errors
  pytest pass/fail  127/0 -> 134/0  ✔  7 new tests, all passing
  coverage          87.3% -> 89.1%  ✔  Increased (+1.8%)

New Code Quality:
  New file coverage  93.2%  ✔  Above 90% minimum
  Max complexity     7      ✔  Below 10 limit
  Type hint coverage 100%   ✔  All new functions annotated

Spec Compliance:
  ACs with tests    4/4     ✔  All acceptance criteria have tests
  DDL sync          ✔       No model-DDL drift detected
  Scope respected   ✔       Changes only in declared modules

Budget:
  Tokens used       312,000 / 500,000 (62.4%)
  Cost              $6.24 / $10.00 (62.4%)
  Phase distribution: validate=3%, audit=8%, plan=12%, build=45%, test=27%, review=5%

RESULT: PASS -- proceed to human review
```

### 7.3 Self-Healing Pipeline (`self_heal.py`)

From OpenAI: *"When something failed, the fix was almost never 'try harder'... human engineers always asked: 'what capability is missing?'"*

```
SELF-HEAL PIPELINE
==================

  Failure detected (lint / type / test)
    |
    v
  Read error output
    |
    v
  Attempt targeted fix (not "try harder")
    |
    v
  Re-verify
    |
    ├── Pass -> Continue
    |
    └── Fail -> Increment circuit breaker
                  |
                  ├── Under threshold (3) -> Retry with different approach
                  |
                  └── Threshold reached -> STOP + escalate to human
                                            with structured failure report
```

Uses `CircuitBreaker` from `src/errors/circuit_breaker.py`:
- `failure_threshold=3` per failure type (lint, type, test)
- On circuit open: dump failures to `.harness/failure_reports/{spec_id}.json`
- Human reviews failure report and adjusts harness

### 7.4 CI/CD Integration

| Stage | What Runs | Blocking? |
|-------|-----------|-----------|
| **Pre-commit** (PostToolUse hook) | ruff + mypy on changed file | Yes -- fix before next task |
| **Pre-merge** (PR check) | Full `post_dev.py` + structural tests | Yes -- no merge with regressions |
| **Nightly** (databricks.yml) | Eval pipeline (deterministic + golden set + judges) | No -- report only |
| **Weekly** (databricks.yml) | Adversarial eval + full GC sweep | No -- report + fix PRs |

---

## 8. Integration Map: Harness x Spec-Driven Workflow

```
SPEC-DRIVEN PHASE          HARNESS LAYER
=====================       =====================
1. Spec Authoring     <-->  Spec templates with harness: section
2. Validate           <-->  validate_specs.py (deterministic)
3. LLM Audit          <-->  Budget tracking starts
4. Build Plan         <-->  pre_dev.py baseline snapshot
5. Build              <-->  PostToolUse hooks (ruff/mypy)
                            self_heal.py on failures
                            Budget enforcement per task
6. Test Plan          <-->  Quality score check (review_ready?)
7. Unit Tests         <-->  In-loop pytest, traceability check
8. Integration Tests  <-->  DDL sync validation
9. E2E Tests          <-->  Full quality score evaluation
10. Traceability      <-->  test_traceability.py (automated matrix)
11. Self-Review       <-->  post_dev.py (full regression check)
12. Final Review      <-->  Human reviews harness report
13. Merge             <-->  gc_budget_audit.py (session cost log)
CONTINUOUS            <-->  GC agents (architecture, docs, dead code)
```

---

## 9. Controls Testing Robustness Matrix

### 9.1 Computational Sensors (deterministic, run on every change)

| Control | Script | Test | What It Catches | Speed |
|---------|--------|------|----------------|-------|
| Layer boundaries | `lint_imports.py` | `test_layer_boundaries.py` | Cross-phase imports in agents/ | < 5s |
| Agent conformance | `lint_agents.py` | `test_agent_conformance.py` | Agents bypassing BaseAgent framework | < 3s |
| Exception hierarchy | -- | `test_exception_hierarchy.py` | Exceptions not inheriting OmniaError | < 1s |
| Spec schema | `validate_specs.py` | `test_spec_schema.py` | Invalid/incomplete spec YAML | < 2s |
| DDL sync | `validate_ddl.py` | `test_ddl_sync.py` | Pydantic model drift from Delta tables | < 3s |
| Pipeline completeness | -- | `test_pipeline_completeness.py` | Missing agents, orphan stages, cycles | < 2s |
| AC traceability | -- | `test_traceability.py` | Untested acceptance criteria | < 5s |
| Ruff (style/complexity) | PostToolUse hook | CI | Style violations, high complexity | < 2s |
| Mypy (types) | PostToolUse hook | CI | Type errors, missing annotations | < 3s |

### 9.2 Inferential Sensors (LLM-based, run selectively)

| Control | When | What It Catches | Cost |
|---------|------|----------------|------|
| LLM Audit (Phase 3) | Before planning | Spec ambiguities, gaps, contradictions | ~10K tokens |
| Eval judges | Nightly | Hallucination, reasoning quality, domain accuracy | ~50K tokens |
| LLM self-review | Phase 11 | Scope creep, pattern violations, missing edge cases | ~15K tokens |
| GC doc semantic check | Weekly | Documentation contradicting implementation | ~20K tokens |

### 9.3 Feedforward Guides (prevent issues before they occur)

| Guide | Type | What It Prevents |
|-------|------|-----------------|
| CLAUDE.md rules (18 total) | Computational + Inferential | Workflow violations, scope creep |
| Spec templates with `harness:` section | Computational | Missing budgets, quality gates |
| Narrow context per task | Computational | Context pollution, drift |
| `PHASE_STAGES` boundaries | Computational | Architectural erosion |
| `LLMLimits` budgets | Computational | Token waste, runaway costs |
| Type hints (required) | Computational | Runtime type errors |
| Spec `constraints:` section | Inferential | Performance, dependency violations |

---

## 10. Implementation Sequence

| Phase | Week | Deliverable | Files |
|-------|------|-------------|-------|
| 1 | 1 | Structural tests + custom linters | `tests/test_harness/`, `scripts/harness/lint_*.py` |
| 2 | 1-2 | Pre/post dev scripts + hooks | `scripts/harness/pre_dev.py`, `post_dev.py`, `post_write_check.py`, `.claude/settings.local.json` |
| 3 | 2 | Budget tracking + spec templates | `scripts/harness/track_session_cost.py`, `specs/templates/*` |
| 4 | 3 | GC agents + self-healing | `scripts/harness/gc_*.py`, `self_heal.py` |
| 5 | 3-4 | Full documentation + CLAUDE.md | This doc, CLAUDE.md harness rules |

---

## 11. Industry References

| Source | Key Concept | URL |
|--------|------------|-----|
| **OpenAI Harness Engineering** | 0 manual code, custom linters with fix instructions, GC agents, rigid architecture, AGENTS.md as map | [openai.com/index/harness-engineering](https://openai.com/index/harness-engineering/) |
| **Bockeler/Fowler Harness Engineering** | Guides/Sensors x Computational/Inferential matrix, steering loop, harness templates, keep quality left | [martinfowler.com/articles/exploring-gen-ai/harness-engineering.html](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) |
| **Stripe Minions** | Pre-push heuristic hooks, blueprints, shift feedback left | Stripe Engineering Blog |
| **Ossature** | Validate/Audit/Build pipeline, narrow context per task, verify-fix loop | [ossature.dev](https://ossature.dev) |
| **Ashby's Law** | Variety reduction -- constrain what agent produces to make harness achievable | Via Bockeler |
| **Ned Letcher (Thoughtworks)** | Ambient affordances -- structural properties that make codebase agent-friendly | Via Bockeler |
