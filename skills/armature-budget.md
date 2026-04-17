# /armature-budget

Pre-plan, track, and report development session costs with multi-provider
model routing, semantic caching, and auto-calibration.

## Usage

```
/armature-budget benchmark                              # Scan project scope + check budget fit
/armature-budget benchmark --model gemini-flash          # Benchmark with any supported model
/armature-budget benchmark --industry                    # Compare against SWE-bench/DevBench targets
/armature-budget report SPEC-ID --industry               # Industry comparison for a spec's actuals
/armature-budget pre-plan build-plan.json                # Pre-plan ALL tasks with model routing
/armature-budget report SPEC-2026-Q2-001                 # Generate cost report
/armature-budget report SPEC-ID --by-provider            # Per-provider cost breakdown
/armature-budget trends                                  # Cross-spec cost trends
/armature-budget log SPEC-ID build 50000                 # Log token usage
/armature-budget estimate file1.py,file2.py              # Pre-request token estimate
/armature-budget plan file1.py,file2.py,file3.py         # Plan request batching
/armature-budget progress build-plan.json SPEC-ID        # Check progress vs. pre-plan
/armature-budget calibrate SPEC-ID                       # Calibrate from completed spec
/armature-budget calibration-status                      # Show calibration profile
/armature-budget cache-stats --spec SPEC-ID              # Semantic cache statistics
```

## Design principle: UNIFORM QUALITY ACROSS ALL TASKS

**No progressive tightening.** Budget optimization is applied equally to every
task from the start. Task 1 and task 10 get identical quality context.

The pre-planner:
1. Reads all tasks from the build plan
2. Estimates total tokens needed across the entire build
3. Picks ONE uniform strategy that fits all tasks within budget
4. Allocates proportional per-task budgets
5. Reserves 15% for verify/fix cycles

If the estimate exceeds budget, optimizations (narrow context, batch reads,
interface-only deps) are applied to ALL tasks equally -- never just the last few.

## Instructions

For `pre-plan`: Run `armature budget --pre-plan <build-plan.json> --complexity <tier>`.
Show the uniform strategy, per-task budgets with routed models, optimizations
applied, execution order, and feasibility. Each task shows which model it's
routed to based on intent and quality floor.

Build plan JSON format:
```json
{
  "spec_id": "SPEC-2026-Q2-001",
  "tasks": [
    {
      "task_id": "task-1",
      "description": "Implement user model",
      "context_files": ["src/models/user.py", "src/models/base.py"],
      "spec_refs": ["specs/SPEC-2026-Q2-001.yaml"],
      "output_files": ["src/models/user.py"],
      "verify_command": "pytest tests/test_models/ -x"
    }
  ]
}
```

For `benchmark`: Run `armature budget --benchmark`.
Show project scope (LOC, files, layers), cost benchmarks per task type
(bugfix/feature/refactor/spike/test), and budget fit check. Supports all
models: sonnet, opus, haiku, gpt-4o, gemini-flash, etc.

For `report`: Run `armature budget --report <SPEC-ID>` and show the cost
breakdown. Add `--by-provider` for per-provider/model breakdown with
anomaly detection.

For `trends`: Run `armature budget --trends` to see cross-spec cost trends
showing calibration and caching impact over time.

For `log`: Run `armature budget --spec <ID> --phase <phase> --tokens <N> --cost <USD>`.

For `estimate`: Run `armature budget --estimate <file1,file2,...>`.
Show estimated tokens per file and total, estimated cost, and cacheability.

For `plan`: Run `armature budget --plan <file1,file2,...>`.
Show how files should be grouped into batched requests.

For `progress`: Run `armature budget --progress <build-plan.json> --spec <SPEC-ID>`.
Show completed vs. remaining tasks, whether on track, and reserve status.
Remaining task budgets are NEVER reduced -- overruns come from the reserve.

For `calibrate`: Run `armature budget --calibrate <SPEC-ID>` after a spec
completes. Compares actual usage vs benchmark predictions and auto-adjusts
multipliers (task type, model verbosity, cache hit rate) using EMA.

For `calibration-status`: Run `armature budget --calibration-status`.
Shows current calibration profile: task adjustments, model verbosity,
cache hit rate, confidence level, and any manual overrides.

For `cache-stats`: Run `armature budget --cache-stats --spec <SPEC-ID>`.
Shows semantic cache hit rate, tokens saved, and breakdown by intent.

## Model Routing

Tasks are automatically routed to the cheapest model meeting a quality
threshold for the task's intent. Configure in armature.yaml:

```yaml
budget:
  providers:
    strategy: cost_optimized     # cost_optimized | quality_first | single_model
    default_model: claude-sonnet
    enabled_models:
      - claude-sonnet
      - gpt-4o-mini
      - gemini-2.5-flash
      - sonar
    quality_floor: 0.75
```

Supported providers: Anthropic (claude-opus/sonnet/haiku), OpenAI (gpt-4o/mini),
Google (gemini-2.5-pro/flash/flash-lite), Perplexity (sonar-pro/sonar).

## Calibration

After 3+ completed specs, calibration auto-adjusts budget multipliers from
actual usage data. Confidence ramps from 0.0 to 0.95 over 10 specs.
Manual overrides in armature.yaml always take precedence.

## Industry Benchmarks

Compare your project's token usage against published research targets:
- **SWE-bench** (Jimenez et al., 2024): per-task-type token percentiles (bugfix, feature, refactor)
- **DevBench** (Li et al., 2024): per-phase token/LOC targets (validate, plan, build, test)
- **AgentBench** (Liu et al., 2024): quality-budget curve (diminishing returns analysis)
- **HumanEval+/MHPP** (Liu et al., 2024): per-language token benchmarks

Output includes percentile positioning (p25/median/p75), efficiency grades
(A/B/C/D), phase allocation deviations, and quality-budget position.

## Semantic Caching

Caches LLM responses by structural fingerprint (file checksums + intent).
Returns cached responses for identical requests, saving 40-70% on
repetitive tasks. Invalidates when context files change.
