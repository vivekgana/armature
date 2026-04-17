# Benchmarking Module -- Design Document

## 1. Overview

Armature's benchmarking module (`src/armature/budget/`) provides a complete cost optimization system for AI coding agent sessions. It answers one question: **"How many tokens will this work cost, and how do we minimize that cost without degrading quality?"**

The module implements four composable optimization layers that produce multiplicative cost reduction:

```
raw_estimate x calibration_adj x routing_adj x cache_adj x prompt_cache_adj = final_cost
```

### Design Principles

1. **Uniform quality across all tasks.** Budget optimization is applied equally to every task from the start. Task 1 and task 10 get identical quality context -- no progressive degradation.

2. **Pre-plan, don't react.** All tasks are estimated upfront. One uniform strategy is selected that fits everything within budget. This prevents the "quality cliff" where early tasks get full context and late tasks get scraps.

3. **Composable and independently disableable.** Each optimization layer (routing, caching, calibration, monitoring) can be enabled or disabled independently. They read from a shared config block in `armature.yaml` under `budget:`.

4. **Deterministic routing.** Model selection happens at plan time, not runtime. Zero coordination tokens are spent on routing decisions.

5. **Learn from actuals.** After each spec completes, calibration compares actual usage against predictions and auto-adjusts multipliers using exponential moving average (EMA).

---

## 2. High-Level Architecture

```
                           armature.yaml
                               |
                        BudgetConfig (schema.py)
                               |
         +---------------------+---------------------+
         |                     |                     |
    CLI (budget_cmd.py)   MCP (server.py)     Python API
         |                     |                     |
         +----------+----------+----------+----------+
                    |                     |
              Entry Points          Entry Points
                    |                     |
    +===============+=====================+================+
    |           BENCHMARKING MODULE (budget/)               |
    |                                                       |
    |  +-----------+    +----------+    +-----------+       |
    |  | benchmark |    | optimizer|    |  planner  |       |
    |  | .py       |--->| .py      |--->|  .py      |       |
    |  +-----------+    +----------+    +-----------+       |
    |       |                |               |              |
    |       v                v               v              |
    |  +-----------+    +----------+    +-----------+       |
    |  | calibrator|    |  router  |    |   cache   |       |
    |  | .py       |    |  .py     |    |   .py     |       |
    |  +-----------+    +----------+    +-----------+       |
    |       |                                               |
    |       v                                               |
    |  +-----------+    +----------+    +-----------+       |
    |  |  tracker  |    | reporter |    |  circuit  |       |
    |  |  .py      |--->| .py      |    |  .py      |       |
    |  +-----------+    +----------+    +-----------+       |
    |       |                                               |
    |       v                                               |
    |  +-----------+                                        |
    |  |  budget   |  (core dataclass + phase allocation)   |
    |  |  .py      |                                        |
    |  +-----------+                                        |
    +===================================================+===+
                                                        |
                                                        v
                                              .armature/budget/
                                              (JSONL + JSON storage)
```

---

## 3. Module Dependency Graph

```
config/schema.py  (BudgetConfig, BudgetTier, ProviderRoutingConfig, ...)
       |
       +----> budget.py         (DevBudget, phase allocation, patterns)
       |
       +----> router.py         (PROVIDERS, CAPABILITIES, ModelRouter)
       |         |
       |         +----> optimizer.py  (AdaptiveOptimizer, TokenEstimate, BuildBudgetPlan)
       |         |         |
       |         |         +----> planner.py  (RequestPlanner, FileGroup, BuildRequestPlan)
       |         |         |
       |         |         +----> benchmark.py  (scan_project, calculate_benchmark)
       |         |
       |         +----> benchmark.py  (get_pricing for cost calculations)
       |
       +----> tracker.py        (SessionTracker -- JSONL logging)
       |         |
       |         +----> reporter.py   (generate_report, anomaly detection)
       |         |
       |         +----> calibrator.py (calibrate_from_spec, industry comparison)
       |                    |
       |                    +----> benchmark.py  (BudgetBenchmark for predictions)
       |
       +----> cache.py          (SemanticCache -- fingerprinting, storage)
       |
       +----> circuit.py        (BudgetCircuit -- circuit breaker)

Entry points:
  cli/budget_cmd.py  ---imports--->  all of the above
  mcp/server.py      ---imports--->  all of the above
```

Key constraints:
- `router.py` is standalone -- no imports from other budget modules
- `benchmark.py` imports from `router.py` and `optimizer.py` (constants only)
- `calibrator.py` imports from `benchmark.py` and `tracker.py`
- No circular dependencies exist in the import graph

---

## 4. Detailed Design -- The Four Optimization Layers

### Layer 1: Model Routing (`router.py`)

Routes each task to the cheapest model that meets a quality threshold for the task's intent.

```
                    Task Intent
                        |
                        v
              +-------------------+
              |   ModelRouter     |
              |                   |
              |  enabled_models[] |
              |  quality_floor    |
              |  premium_intents  |
              +-------------------+
                        |
          +-------------+-------------+
          |             |             |
    score >= floor  score < floor  context overflow
          |             |             |
          v             v             v
    Cheapest model   Fallback to   Skip model
    by cost          default
          |
          v
    RoutingDecision {
      model, reason,
      estimated_cost_usd,
      alternative
    }
```

**Provider Catalog** (10 models across 4 providers):

```
+------------------+--------+--------+-----------+---------+-----------+
| Model            | Input  | Output | Cache Rd  | Context | Provider  |
+------------------+--------+--------+-----------+---------+-----------+
| claude-opus      | $15.00 | $75.00 | $1.50     | 200K    | Anthropic |
| claude-sonnet    |  $3.00 | $15.00 | $0.30     | 200K    | Anthropic |
| claude-haiku     |  $0.25 |  $1.25 | $0.03     | 200K    | Anthropic |
| gpt-4o           |  $2.50 | $10.00 | $1.25     | 128K    | OpenAI    |
| gpt-4o-mini      |  $0.15 |  $0.60 | $0.075    | 128K    | OpenAI    |
| gemini-2.5-pro   |  $1.25 | $10.00 | $0.315    | 1M      | Google    |
| gemini-2.5-flash |  $0.15 |  $0.60 | $0.0375   | 1M      | Google    |
| gemini-flash-lite|  $0.075|  $0.30 | --        | 1M      | Google    |
| sonar-pro        |  $3.00 | $15.00 | --        | 200K    | Perplexity|
| sonar            |  $1.00 |  $1.00 | --        | 128K    | Perplexity|
+------------------+--------+--------+-----------+---------+-----------+
                                        (Pricing per 1M tokens)
```

**Capability Matrix** (scores 0.0-1.0 per dimension):

```
+------------------+----------+-----------+--------+---------+----------+
| Model            | Code Gen | Reasoning | Search | Explain | Test Gen |
+------------------+----------+-----------+--------+---------+----------+
| claude-opus      |    0.98  |    0.97   |  0.70  |  0.95   |   0.95   |
| claude-sonnet    |    0.93  |    0.90   |  0.70  |  0.90   |   0.90   |
| claude-haiku     |    0.75  |    0.70   |  0.60  |  0.80   |   0.70   |
| gpt-4o           |    0.90  |    0.88   |  0.70  |  0.88   |   0.85   |
| gpt-4o-mini      |    0.72  |    0.65   |  0.60  |  0.78   |   0.68   |
| gemini-2.5-pro   |    0.91  |    0.92   |  0.80  |  0.88   |   0.85   |
| gemini-2.5-flash |    0.80  |    0.75   |  0.70  |  0.82   |   0.75   |
| gemini-flash-lite|    0.60  |    0.50   |  0.50  |  0.70   |   0.55   |
| sonar-pro        |    0.50  |    0.70   |  0.95  |  0.80   |   0.40   |
| sonar            |    0.35  |    0.50   |  0.90  |  0.65   |   0.30   |
+------------------+----------+-----------+--------+---------+----------+
```

**Routing Decision Table:**

| Intent | Quality Floor | Typical Route | Fallback |
|--------|--------------|---------------|----------|
| complex_code_gen | >= 0.90 | claude-sonnet | claude-opus |
| code_gen | >= 0.75 | gpt-4o-mini / gemini-flash | claude-haiku |
| explain | >= 0.75 | gemini-flash / gpt-4o-mini | claude-haiku |
| test_gen | >= 0.80 | claude-sonnet | gpt-4o |
| research | >= 0.75 | sonar-pro | gemini-pro |
| lint_fix | >= 0.75 | gemini-flash-lite | gpt-4o-mini |

---

### Layer 2: Semantic Caching (`cache.py`)

Caches LLM responses by structural fingerprint. Returns cached responses for functionally equivalent requests, skipping the API call entirely.

```
    Request (task_type, intent, context_files)
                        |
                        v
              +-------------------+
              |   fingerprint()   |
              |                   |
              | SHA256(           |
              |   task_type +     |
              |   intent +        |
              |   sorted(         |
              |     file_checksums|
              |   )               |
              | )[:32]            |
              +-------------------+
                        |
                        v
              +-------------------+
              |    lookup(fp)     |
              +-------------------+
                   /         \
                  /           \
            HIT               MISS
             |                   |
             v                   v
    Check TTL (7d)         Call LLM API
    Check file checksums        |
             |                   v
        +----+----+        store(fp, response)
        |         |              |
    VALID    INVALIDATED         v
        |         |         Write to
        v         v         index.json +
    Return     Evict +      responses/{fp}.txt
    cached     re-call
    response
```

**Invalidation Rules:**
- Context file checksum changes -> invalidate
- Entry age > TTL (default 7 days) -> invalidate
- Max cache size exceeded -> LRU eviction (oldest first)
- `cache.invalidate_file(path)` -> evict all entries referencing that file

**Storage Layout:**
```
.armature/cache/
  index.json              # fingerprint -> {created_at, context_checksums,
                          #                 task_type, intent, tokens_saved,
                          #                 model, hit_count}
  responses/
    a1b2c3d4e5f6....txt   # cached LLM response text
    f7e8d9c0b1a2....txt
```

---

### Layer 3: Auto-Calibration (`calibrator.py`)

Compares actual token usage against benchmark predictions after each spec completes. Updates multipliers using exponential moving average (EMA).

```
    Completed Spec
         |
         v
+------------------------+
| calibrate_from_spec()  |
|                        |
|  1. Load profile       |     CalibrationProfile
|  2. Get actual usage   |     +-------------------+
|  3. Compare vs bench   |     | task_adjustments  |  {"bugfix": 0.73, ...}
|  4. EMA update tasks   |---->| model_verbosity   |  {"opus": 1.38, ...}
|  5. EMA update models  |     | cache_hit_rate    |  0.45
|  6. EMA update cache   |     | specs_calibrated  |  7
|  7. Recalc confidence  |     | confidence        |  0.83
|  8. Save profile       |     +-------------------+
+------------------------+              |
                                        v
                              .armature/calibration.json
```

**Three Calibration Axes:**

```
Axis 1: Historical (per task type)
  adjustment = actual_tokens / predicted_tokens
  EMA: new = 0.3 * this_spec + 0.7 * previous
  Clamped to [0.2, 5.0] to prevent outlier skew

Axis 2: Model Verbosity (per model)
  Defaults: opus=1.4, sonnet=1.0, haiku=0.7
  Calibrated from actual output token counts per model

Axis 3: Cache Hit Rate
  observed_rate = cache_hits / total_requests
  EMA: new = 0.3 * observed + 0.7 * previous
```

**Confidence Ramp:**

```
confidence = min(0.95, 1 - e^(-0.25 * specs_calibrated))

  Specs   Confidence   Behavior
  -----   ----------   --------
  0       0.00         Use hardcoded defaults only
  1       0.22         Mostly defaults, slight blend
  3       0.53         Blend: conf * calibrated + (1-conf) * default
  5       0.71         Calibrated values dominate
  10      0.92         Near full auto-calibration
  10+     0.95         Capped -- never 100% (safety margin)
```

**Priority Chain:**
```
manual override (armature.yaml) > calibrated value > hardcoded default
```

---

### Layer 4: Cross-Provider Monitoring (`tracker.py` + `reporter.py`)

Extended JSONL schema tracks provider, model, cache, latency, and intent per request.

**JSONL Entry Schema:**

```json
{
  "timestamp": "2026-04-16T10:30:00Z",
  "spec_id": "SPEC-2026-Q2-001",
  "phase": "build",
  "tokens": 15700,
  "cost_usd": 0.086,
  "task_id": "task-3",
  "model": "claude-sonnet",
  "provider": "anthropic",
  "input_tokens": 12500,
  "output_tokens": 3200,
  "cache_hit_tokens": 8000,
  "latency_ms": 2400,
  "semantic_cache_hit": false,
  "intent": "code_gen"
}
```

Fields `task_id` through `intent` are optional -- old entries missing them are treated as `model=unknown, provider=unknown`. Backward-compatible.

**Aggregation Views:**
- `get_usage(spec_id)` -- total tokens, cost, per-phase breakdown
- `get_usage_by_provider(spec_id)` -- per-provider with model sub-breakdown
- `get_usage_by_intent(spec_id)` -- per-intent with cost list for anomaly detection
- `get_semantic_cache_stats(spec_id)` -- hit/miss counts, tokens saved
- `get_cross_spec_trends(limit)` -- cost trend across recent N specs

**Anomaly Detection:**
```
anomaly = cost > threshold * avg_cost_for_intent   (default threshold = 3.0)
```

---

## 5. Low-Level Class Diagrams

### 5.1 Core: budget.py

```
+----------------------------------+
|          DevBudget               |
|  (frozen dataclass)              |
+----------------------------------+
| complexity: str                  |
| max_tokens_per_spec: int         |
| max_cost_per_spec_usd: float     |
| max_requests_per_task: int       |
| cache_hit_target_pct: float      |
| phase_allocation: dict[str,float]|
+----------------------------------+
| for_complexity(str) -> DevBudget |
| tokens_for_phase(str) -> int     |
| cost_for_phase(str) -> float     |
+----------------------------------+

+--------------------------------------+
| REQUEST_OPTIMIZATION_PATTERNS: dict  |
+--------------------------------------+
| batch_file_reads        (40% save)   |
| front_load_context      (25% save)   |
| narrow_context          (50% save)   |
| use_compact             (30% save)   |
| progressive_disclosure  (35% save)   |
+--------------------------------------+
```

### 5.2 Benchmark: benchmark.py

```
+------------------------------+      +------------------------------+
|       ProjectScope           |      |       TaskEstimate           |
|  (dataclass)                 |      |  (dataclass)                 |
+------------------------------+      +------------------------------+
| language: str                |      | task_type: str               |
| framework: str               |      | estimated_tokens: int        |
| total_source_files: int      |      | estimated_cost_usd: float    |
| total_loc: int               |      | model: str                   |
| total_test_files: int        |      +------------------------------+
| test_loc: int                |
| architectural_layers: int    |      +------------------------------+
| boundary_rules: int          |      |     BudgetBenchmark          |
| conformance_rules: int       |      |  (dataclass)                 |
| spec_count: int              |      +------------------------------+
| ac_count: int                |      | scope: ProjectScope          |
+------------------------------+      | estimates: dict[str,          |
                                      |               TaskEstimate]  |
+------------------------------+      | recommended_tier: str        |
|       ScopeWarning           |      | recommended_tokens: int      |
|  (dataclass)                 |      | recommended_cost_usd: float  |
+------------------------------+      +------------------------------+
| level: str                   |
| message: str                 |
| configured_tokens: int       |
| benchmark_tokens: int        |
| recommended_tier: str        |
+------------------------------+

Functions:
  scan_project(root, config) -> ProjectScope
  calculate_benchmark(scope, model, calibration?) -> BudgetBenchmark
  check_budget_fit(config, scope, complexity, model) -> ScopeWarning
  format_benchmark(benchmark, industry_comparison?) -> str
  format_warning(warning) -> str
```

**Benchmark Calculation Formula:**
```
base_tokens = LOC * 15 (tokens per line)

task_tokens = base_tokens
            * TASK_MULTIPLIER[task_type]        (bugfix=1.5, feature=3.0, ...)
            * LANGUAGE_MULTIPLIER[language]      (python=1.0, typescript=1.1, ...)
            * FRAMEWORK_MULTIPLIER[framework]    (django=1.3, fastapi=1.0, ...)
            * ARCH_MULTIPLIER(layer_count)       (<=2: 1.0, <=4: 1.2, <=7: 1.4, 8+: 1.6)
            * calibration_adjustment             (from CalibrationProfile)

input_tokens  = task_tokens
output_tokens = input_tokens * OUTPUT_TO_INPUT_RATIO * model_verbosity

cost = (input/1M * price_input + output/1M * price_output) * (1 - cache_rate * 0.9)
```

### 5.3 Optimizer: optimizer.py

```
+--------------------------------------+
|         TokenEstimate                |
|  (frozen dataclass)                  |
+--------------------------------------+
| input_tokens: int                    |
| estimated_output_tokens: int         |
| total: int                           |
| context_files_tokens: int            |
| spec_tokens: int                     |
| conversation_tokens: int             |
| cacheable_pct: float                 |
| estimated_cost_usd: float            |
+--------------------------------------+

+--------------------------------------+
|       OptimizationAction             |
|  (dataclass)                         |
+--------------------------------------+
| strategy: str                        |
| description: str                     |
| estimated_savings_pct: int           |
| priority: int  (1=highest)           |
| applies_to: str  ("all_tasks")       |
+--------------------------------------+

+--------------------------------------+      +--------------------------------------+
|          TaskSpec                     |      |         TaskBudget                   |
|  (dataclass)                         |      |  (dataclass)                         |
+--------------------------------------+      +--------------------------------------+
| task_id: str                         |      | task_id: str                         |
| description: str                     |      | max_input_tokens: int                |
| context_files: list[str]             |      | max_output_tokens: int               |
| spec_refs: list[str]                 |      | context_files: list[str]             |
| output_files: list[str]              |      | optimization_applied: list[str]      |
| verify_command: str                  |      | model: str                           |
| estimated_tokens: int                |      | intent: str                          |
| phase: str                           |      +--------------------------------------+
+--------------------------------------+

+--------------------------------------+
|       BuildBudgetPlan                |
|  (dataclass)                         |
+--------------------------------------+
| spec_id: str                         |
| strategy: str                        |
| total_budget_tokens: int             |
| total_estimated_tokens: int          |
| budget_utilization_pct: float        |
| per_task_max_input: int              |
| per_task_max_output: int             |
| task_budgets: list[TaskBudget]       |
| optimizations: list[OptimizationAction]|
| warnings: list[str]                  |
| feasible: bool                       |
| reserve_pct: float  (0.15)           |
+--------------------------------------+

+--------------------------------------+
|       AdaptiveOptimizer              |
+--------------------------------------+
| config: BudgetConfig                 |
| root: Path                           |
+--------------------------------------+
| estimate_tokens(files, ...) -> TokenEstimate  |
| estimate_task(TaskSpec) -> int                |
| plan_build(spec_id, tasks, complexity)        |
|                          -> BuildBudgetPlan   |
| plan_phase(spec_id, phase, tasks, complexity) |
|                          -> BuildBudgetPlan   |
| check_task_progress(plan, completed, actuals) |
|                          -> dict              |
| format_build_plan(plan) -> str                |
+--------------------------------------+
```

**Optimization Strategy Levels:**
```
Level 0: full_context       -- no optimization needed, raw total <= budget
Level 1: optimized          -- batch_file_reads (15%) + front_load_context (20%)
Level 2: narrow             -- + narrow_context (35%) + compress_between_tasks (30%)
Level 3: minimal            -- + interface_only (50%) + spec_summary (15%)
Level X: infeasible         -- all optimizations applied, still over budget

Savings are NOT additive. Diminishing returns formula:
  combined = 1 - PRODUCT(1 - savings_i) for each optimization
```

### 5.4 Router: router.py

```
+--------------------------------------+
|        ProviderModel                 |
|  (frozen dataclass)                  |
+--------------------------------------+
| input: float         ($/1M tokens)   |
| output: float        ($/1M tokens)   |
| cache_read: float|None               |
| cache_write: float|None              |
| context: int         (max tokens)    |
| provider: str                        |
+--------------------------------------+

+--------------------------------------+
|      ModelCapabilities               |
|  (frozen dataclass)                  |
+--------------------------------------+
| code_gen: float      (0.0-1.0)       |
| reasoning: float                     |
| search: float                        |
| explain: float                       |
| test_gen: float                      |
+--------------------------------------+
| score_for(intent: str) -> float      |
+--------------------------------------+

+--------------------------------------+
|      RoutingDecision                 |
|  (dataclass)                         |
+--------------------------------------+
| model: str                           |
| reason: str                          |
| estimated_cost_usd: float            |
| alternative: str|None                |
+--------------------------------------+

+--------------------------------------+
|        ModelRouter                   |
+--------------------------------------+
| enabled: list[str]                   |
| quality_floor: float                 |
| premium_intents: set[str]            |
+--------------------------------------+
| route(intent, input, output)         |
|                  -> RoutingDecision   |
| route_task(type, intent, in, out)    |
|                  -> RoutingDecision   |
| cost_for_model(model, in, out,       |
|                cache_hit) -> float   |
| compare_models(intent, in, out)      |
|                  -> list[dict]       |
| format_comparison(...) -> str        |
+--------------------------------------+

Constants:
  PROVIDERS: dict[str, ProviderModel]     -- 10 models
  CAPABILITIES: dict[str, ModelCapabilities]
  PREMIUM_INTENT_FLOORS: dict[str, float] -- complex_code_gen=0.90, architecture=0.90
  DEFAULT_QUALITY_FLOOR = 0.75

Compat:
  get_pricing(model) -> dict[str, float]  -- backward compat for PRICING dict
```

### 5.5 Planner: planner.py

```
+--------------------------------------+
|         FileGroup                    |
|  (dataclass)                         |
+--------------------------------------+
| files: list[str]                     |
| estimated_tokens: int                |
| reason: str                          |
+--------------------------------------+

+--------------------------------------+
|       TaskRequestPlan                |
|  (dataclass)                         |
+--------------------------------------+
| task_id: str                         |
| groups: list[FileGroup]              |
| total_estimated_tokens: int          |
| total_requests: int                  |
| savings_vs_sequential: int           |
| shared_files: list[str]              |
+--------------------------------------+

+--------------------------------------+
|      BuildRequestPlan                |
|  (dataclass)                         |
+--------------------------------------+
| spec_id: str                         |
| task_plans: list[TaskRequestPlan]    |
| total_estimated_tokens: int          |
| total_requests: int                  |
| total_savings: int                   |
| shared_context_files: list[str]      |
| execution_order: list[str]           |
+--------------------------------------+

+--------------------------------------+
|       RequestPlanner                 |
+--------------------------------------+
| root: Path                           |
| max_tokens_per_request: int (100K)   |
+--------------------------------------+
| estimate_file_tokens(path) -> int    |
| plan_build(spec_id, tasks)           |
|               -> BuildRequestPlan    |
| plan_task(TaskContext) -> TaskReqPlan |
| analyze_imports(file) -> list[str]   |
| expand_context(task, depth) -> Task  |
| format_build_plan(plan) -> str       |
| format_plan(plan) -> str             |
+--------------------------------------+
```

**Execution Order Algorithm:**
```
Greedy nearest-neighbor for cache locality:

1. Start with the task that has the most context files
2. Pick next task that shares the most files with current task
3. Repeat until all tasks are ordered

Goal: consecutive tasks share files, maximizing prompt cache hits
      (Anthropic prompt cache has 5-minute TTL)
```

**File Grouping Strategy:**
```
Group 1: shared_context -- files used by 2+ tasks (cache-friendly, read first)
Group 2+: same_module  -- remaining files grouped by directory
Each group stays under max_tokens_per_request (100K)

Savings = (files * context_overhead) - (groups * context_overhead)
  where context_overhead = 2000 tokens per request
```

### 5.6 Tracker: tracker.py

```
+--------------------------------------+
|       SessionTracker                 |
+--------------------------------------+
| config: BudgetConfig                 |
| root: Path                           |
| storage_dir: Path                    |
+--------------------------------------+
| log(spec_id, phase, tokens, cost,    |
|     *, task_id, model, provider,     |
|     input_tokens, output_tokens,     |
|     cache_hit_tokens, latency_ms,    |
|     semantic_cache_hit, intent)      |
| get_usage(spec_id) -> dict           |
| get_usage_by_provider(spec_id)       |
|                   -> dict[str, dict] |
| get_usage_by_intent(spec_id)         |
|                   -> dict[str, dict] |
| get_semantic_cache_stats(spec_id)    |
|                   -> dict            |
| get_cross_spec_trends(limit) -> list |
| is_over_budget(spec_id, complexity)  |
|                   -> bool            |
| get_optimization_suggestions(        |
|   spec_id, complexity) -> list[str]  |
| list_specs() -> list[str]            |
+--------------------------------------+
```

**Storage Layout:**
```
.armature/budget/
  SPEC-2026-Q2-001_cost.jsonl    # one line per logged request
  SPEC-2026-Q2-002_cost.jsonl
  ...
```

### 5.7 Reporter: reporter.py

```
Functions:
  generate_report(tracker, spec_id, config)
    -- Phase breakdown table with % of total
    -- Budget comparison per tier
    -- Optimization suggestions

  generate_provider_report(tracker, spec_id, config)
    -- Per-provider table with model sub-rows
    -- Semantic cache line
    -- Anomaly detection

  generate_trend_report(tracker, limit=10)
    -- Cross-spec cost trend table
    -- Trend direction (% up/down)

  detect_anomalies(tracker, spec_id, threshold=3.0) -> list[str]
    -- Flags requests costing > threshold * avg for their intent
```

### 5.8 Cache: cache.py

```
+--------------------------------------+
|         CacheEntry                   |
|  (dataclass)                         |
+--------------------------------------+
| fingerprint: str                     |
| response: str                        |
| created_at: str                      |
| context_checksums: dict[str, str]    |
| task_type: str                       |
| intent: str                          |
| tokens_saved: int                    |
| model: str                           |
| hit_count: int                       |
+--------------------------------------+

+--------------------------------------+
|       SemanticCache                  |
+--------------------------------------+
| storage_dir: Path                    |
| index_path: Path                     |
| responses_dir: Path                  |
| max_size_bytes: int                  |
| ttl_seconds: int                     |
| root: Path                           |
+--------------------------------------+
| fingerprint(task_type, intent,       |
|   context_files, output_schema)      |
|                   -> str (32-char)   |
| lookup(fingerprint) -> CacheEntry?   |
| store(fingerprint, response, ...)    |
| invalidate_file(path) -> int         |
| clear() -> int                       |
| stats() -> dict                      |
+--------------------------------------+
```

### 5.9 Calibrator: calibrator.py

```
+--------------------------------------+
|     CalibrationProfile               |
|  (dataclass)                         |
+--------------------------------------+
| task_adjustments: dict[str, float]   |
| model_verbosity: dict[str, float]    |
| cache_hit_rate: float                |
| specs_calibrated: int                |
| last_calibrated: str                 |
| confidence: float                    |
+--------------------------------------+

+--------------------------------------+
|     CalibrationStore                 |
+--------------------------------------+
| storage_dir: Path                    |
| profile_path: Path                   |
+--------------------------------------+
| load() -> CalibrationProfile         |
| save(profile)                        |
+--------------------------------------+

+--------------------------------------+
|     IndustryComparison               |
|  (dataclass)                         |
+--------------------------------------+
| task_positions: dict[str, dict]      |
| budget_tokens: int                   |
| estimated_quality_pct: float         |
| quality_ceiling_note: str            |
| cost_per_loc: float|None             |
| cache_hit_rate: float                |
| routing_savings_ratio: float|None    |
| calibration_drift: float|None        |
| phase_comparison: dict[str, dict]    |
| grades: dict[str, str]               |
+--------------------------------------+

+--------------------------------------+
|     EfficiencyTargets                |
|  (frozen dataclass)                  |
+--------------------------------------+
| target_cost_per_loc_standard: 0.01   |
| target_cost_per_loc_premium: 0.05    |
| target_cache_hit_rate: 0.40          |
| target_routing_savings_ratio: 2.0    |
| target_calibration_drift: 0.20       |
| target_tokens_per_bugfix: 30000      |
| target_tokens_per_feature: 120000    |
+--------------------------------------+

Functions:
  calibrate_from_spec(spec_id, tracker, benchmark, store) -> CalibrationProfile
  apply_calibration(profile, config_overrides?, min_confidence?) -> dict
  compare_against_industry(benchmark, tracker, spec_id, ...) -> IndustryComparison
  assess_quality_budget_position(budget_tokens) -> (float, str)
  compute_efficiency_grades(comparison) -> dict[str, str]
  format_industry_comparison(comparison) -> str
```

### 5.10 Circuit Breaker: circuit.py

```
+--------------------------------------+
|       BudgetCircuit                  |
|  (dataclass)                         |
+--------------------------------------+
| threshold: int  (default 3)          |
| consecutive_over: int                |
| _open: bool                          |
+--------------------------------------+
| record(over_budget: bool)            |
| is_open: bool  (property)            |
| reset()                              |
+--------------------------------------+

State machine:
  CLOSED -> record(over=True) x 3 -> OPEN
  OPEN -> reset() -> CLOSED
  CLOSED -> record(over=False) -> resets consecutive count
```

---

## 6. Data Flow Diagrams

### 6.1 Pre-Plan Build (Primary Flow)

```
User: armature budget --pre-plan build-plan.json --complexity medium

  build-plan.json
       |
       v
  Parse tasks: [TaskSpec, TaskSpec, ...]
       |
       +-----> AdaptiveOptimizer.plan_build()
       |           |
       |           +---> estimate_task() for each task
       |           |       |
       |           |       +---> estimate_tokens(context_files)
       |           |       |       reads each file, counts chars * 0.25
       |           |
       |           +---> _select_uniform_strategy()
       |           |       tries Level 1, 2, 3 until fits in budget
       |           |       combined savings = 1 - product(1 - each)
       |           |
       |           +---> ModelRouter.route() for each task
       |           |       _infer_intent(task) -> intent
       |           |       cheapest model where cap[intent] >= floor
       |           |
       |           +---> Proportional allocation
       |                   task_share = task_tokens / raw_total
       |                   task_budget = usable_budget * task_share
       |
       +-----> RequestPlanner.plan_build()
       |           |
       |           +---> Find shared files across tasks
       |           +---> Optimize execution order (cache locality)
       |           +---> Group files within each task
       |
       v
  BuildBudgetPlan + BuildRequestPlan
       |
       v
  Formatted output (table per task with model, tokens, optimizations)
```

### 6.2 Benchmark + Industry Comparison

```
User: armature budget --benchmark --industry

  scan_project(root, config)
       |
       v
  ProjectScope {LOC, files, layers, specs}
       |
       v
  calculate_benchmark(scope, model, calibration?)
       |
       +---> For each task type (bugfix, feature, refactor, spike, test):
       |       base * task_mult * lang_mult * fw_mult * arch_mult * cal_adj
       |
       v
  BudgetBenchmark {estimates, recommended_tier}
       |
       v
  compare_against_industry(benchmark, tracker, spec_id)
       |
       +---> Position each task type vs INDUSTRY_TASK_TARGETS (p25/median/p75)
       +---> Interpolate QUALITY_BUDGET_CURVE for budget -> quality %
       +---> Compare phase allocation vs INDUSTRY_PHASE_TARGETS
       +---> Compute calibration drift
       +---> compute_efficiency_grades() -> A/B/C/D per metric
       |
       v
  IndustryComparison
       |
       v
  format_benchmark(benchmark, industry_comparison) -> formatted text
```

### 6.3 Calibration Loop

```
User: armature budget --calibrate SPEC-ID

  CalibrationStore.load()
       |
       v
  CalibrationProfile (existing or defaults)
       |
       v
  tracker.get_usage(spec_id)     --+
  tracker.get_usage_by_provider()  |
  tracker.get_semantic_cache_stats()
       |
       v
  For each phase in usage:
    ratio = actual_tokens / predicted_tokens
    ratio = clamp(ratio, 0.2, 5.0)
    profile.task_adjustments[type] = EMA(previous, ratio)
       |
       v
  profile.cache_hit_rate = EMA(previous, observed_rate)
       |
       v
  profile.confidence = min(0.95, 1 - e^(-0.25 * n))
       |
       v
  CalibrationStore.save(profile)
       |
       v
  Next benchmark run uses apply_calibration():
    effective = confidence * calibrated + (1-confidence) * default
```

---

## 7. Configuration Schema

All budget configuration lives in `armature.yaml` under the `budget:` key.

```yaml
budget:
  enabled: true
  storage: ".armature/budget/"

  # Complexity tiers
  defaults:
    low:      { max_tokens: 100000,   max_cost_usd: 2.0 }
    medium:   { max_tokens: 500000,   max_cost_usd: 10.0 }
    high:     { max_tokens: 1000000,  max_cost_usd: 20.0 }
    critical: { max_tokens: 2000000,  max_cost_usd: 40.0 }

  # SDLC phase budget allocation (%)
  phase_allocation:
    validate: 5
    audit: 10
    plan: 15
    build: 40
    test: 25
    review: 5

  # Circuit breaker
  circuit_breaker:
    consecutive_over_budget: 3

  # Layer 1: Multi-provider model routing
  providers:
    strategy: cost_optimized       # cost_optimized | quality_first | single_model
    default_model: claude-sonnet
    enabled_models:
      - claude-sonnet
      - gpt-4o-mini
      - gemini-2.5-flash
      - sonar
    quality_floor: 0.75
    premium_intents:
      - complex_code_gen
      - architecture

  # Layer 2: Semantic caching
  cache:
    enabled: true
    storage: ".armature/cache/"
    max_size_mb: 100
    ttl_days: 7

  # Layer 3: Auto-calibration
  calibration:
    enabled: true
    auto_calibrate: true
    min_specs: 3
    task_overrides: {}              # Manual override: {"bugfix": 0.8}
    model_verbosity_overrides: {}   # Manual override: {"claude-opus": 1.5}
    cache_hit_rate_override: null    # Manual override: 0.5

  # Layer 4: Monitoring
  monitoring:
    track_provider: true
    track_latency: true
    track_cache_hits: true
    anomaly_threshold: 3.0
```

**Pydantic Config Classes** (`config/schema.py`):

```
BudgetConfig
  +-- defaults: dict[str, BudgetTier]
  +-- phase_allocation: dict[str, int]
  +-- circuit_breaker: BudgetCircuitConfig
  +-- providers: ProviderRoutingConfig
  +-- cache: SemanticCacheConfig
  +-- calibration: CalibrationConfig
  +-- monitoring: MonitoringConfig
```

---

## 8. Industry Benchmark Integration

The calibrator includes benchmark targets derived from published research:

**Sources:**
- SWE-bench (Jimenez et al., 2024) -- real-world GitHub issue resolution
- DevBench (Li et al., 2024) -- full SDLC coverage (req -> design -> code -> test)
- AgentBench (Liu et al., 2024) -- multi-environment agent evaluation
- HumanEval+ / MHPP (Liu et al., 2024) -- multi-language code generation
- RepoBench (Liu et al., 2023) -- repository-level code completion

### Per-Task-Type Token Targets (tokens per resolved issue)

```
+----------+--------+--------+--------+
| Type     | p25    | Median | p75    |
+----------+--------+--------+--------+
| bugfix   | 15,000 | 30,000 | 60,000 |
| feature  | 50,000 |120,000 |250,000 |
| refactor | 25,000 | 60,000 |150,000 |
| spike    |  5,000 | 15,000 | 40,000 |
| test     | 20,000 | 50,000 |120,000 |
+----------+--------+--------+--------+
(Source: SWE-bench leaderboards, DevBench reports)
```

### Per-Phase Token Targets (tokens per LOC of touched code)

```
+----------+-----------+------------+-------------------------------+
| Phase    | Read/LOC  | Write/LOC  | Source                        |
+----------+-----------+------------+-------------------------------+
| validate |     3.5   |      2.0   | DevBench (Li et al., 2024)    |
| audit    |     7.5   |      5.5   | DevBench (Li et al., 2024)    |
| plan     |     7.5   |      5.5   | DevBench (Li et al., 2024)    |
| build    |    15.0   |     10.0   | SWE-bench (Jimenez, 2024)     |
| test     |    11.5   |     14.0   | HumanEval+ (Liu et al., 2024) |
| review   |    20.0   |      2.0   | Industry consensus            |
+----------+-----------+------------+-------------------------------+
```

### Quality-Budget Curve (diminishing returns)

```
Quality %
  100|
   96|                                            ___________
   90|                                    _______/
   82|                            _______/
   70|                    _______/
   55|            _______/
   40|    _______/
     |___/
     +----+------+------+-------+--------+----------+---------+
     10K  25K    50K    100K    200K     500K       1M       2M
                         Token Budget
```

**Efficiency Grading Rubric:**

| Grade | Meaning |
|-------|---------|
| A | Meets or exceeds industry target |
| B | Within 1.5x of target |
| C | Within 2.5x of target |
| D | Worse than 2.5x target |

Graded metrics: cache_efficiency, cost_per_loc, routing_savings, calibration_accuracy, task_{type} per task type.

---

## 9. Storage Layout

```
project-root/
  armature.yaml                       # Configuration (all budget settings)
  .armature/
    budget/
      SPEC-001_cost.jsonl             # Usage log per spec (append-only)
      SPEC-002_cost.jsonl
      calibration.json                # Learned calibration profile
    cache/
      index.json                      # Fingerprint -> metadata index
      responses/
        a1b2c3d4....txt               # Cached LLM responses
        e5f6a7b8....txt
```

---

## 10. CLI and MCP Entry Points

### CLI Commands (`cli/budget_cmd.py`)

| Command | Handler | Modules Used |
|---------|---------|--------------|
| `--benchmark` | `_handle_benchmark` | benchmark, router |
| `--benchmark --industry` | `_handle_benchmark` | benchmark, calibrator, tracker |
| `--pre-plan FILE` | `_handle_preplan` | optimizer, planner, router |
| `--report SPEC` | `generate_report` | tracker, reporter |
| `--report SPEC --by-provider` | `generate_provider_report` | tracker, reporter |
| `--report SPEC --industry` | `_handle_industry_report` | benchmark, calibrator, tracker |
| `--trends` | `generate_trend_report` | tracker, reporter |
| `--estimate FILES` | `_handle_estimate` | optimizer |
| `--plan FILES` | `_handle_plan` | planner |
| `--progress FILE --spec ID` | `_handle_progress` | optimizer, tracker |
| `--calibrate SPEC` | `_handle_calibrate` | calibrator, tracker, benchmark |
| `--calibration-status` | `_handle_calibration_status` | calibrator |
| `--cache-stats --spec ID` | `_handle_cache_stats` | tracker |
| `--spec ID --phase P --tokens N` | direct `tracker.log()` | tracker |

### MCP Tools (`mcp/server.py`)

| Tool | Function | Description |
|------|----------|-------------|
| `armature_benchmark` | `_tool_benchmark` | Scope analysis + budget fit + optional industry comparison |
| `armature_preplan` | `_tool_preplan` | Pre-plan entire build with routing |
| `armature_budget` | `_tool_budget` | Log usage or get report |
| `armature_estimate` | `_tool_estimate` | Pre-request token estimate |
| `armature_route` | `_tool_route` | Route single task to cheapest model |
| `armature_calibrate` | `_tool_calibrate` | Calibrate from spec or show status |
| `armature_cache_stats` | `_tool_cache_stats` | Cache hit rate and savings |
