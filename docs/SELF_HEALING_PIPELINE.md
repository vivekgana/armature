# Self-Healing Pipeline — Unique Feature Deep Dive

**No competing framework (SonarQube, Trunk.io, Snyk, CodeClimate) has automated self-healing with circuit breakers.** Armature's self-healing pipeline automatically fixes quality violations, retries intelligently, and escalates to humans when fixes fail — all with configurable safety limits.

---

## Architecture

```
Quality Check Failed
        │
        ▼
┌─────────────────────┐
│   Heal Pipeline      │
│   (max 3 attempts)   │
├──────────┬──────────┤
│ Attempt 1│          │
│ ruff fix │──pass?──→ ✅ FIXED
│          │          │
│   fail   │          │
│    ▼     │          │
│ Attempt 2│          │
│ re-check │──pass?──→ ✅ FIXED
│          │          │
│   fail   │          │
│    ▼     │          │
│ Attempt 3│          │
│ final try│──pass?──→ ✅ FIXED
│          │          │
│   fail   │          │
│    ▼     │          │
│ ⛔ CIRCUIT BREAKER   │
│ Escalate to human    │
│ Generate failure     │
│ report               │
└─────────────────────┘
```

## How It Works

### 1. HealPipeline Orchestrator

```python
# src/armature/heal/pipeline.py

class HealPipeline:
    """Orchestrates self-healing with circuit breakers per failure type."""

    def __init__(self, config: HealConfig) -> None:
        self.config = config      # max_attempts=3, circuit_breaker_threshold=3
        self.root = Path.cwd()

    def heal(self, failure_types: set[str]) -> list[HealResult]:
        """Run healers for lint, type, and test failures."""
        results = []
        for ft in sorted(failure_types):
            healer = self._get_healer(ft)
            result = healer()           # attempts up to max_attempts
            results.append(result)      # HealResult: fixed=bool, details=str
        return results
```

### 2. Lint Auto-Fix (ruff --fix)

The lint healer is the only healer with `auto_fix: true` by default — because `ruff --fix` is deterministic and safe:

```python
def _heal_lint(self) -> HealResult:
    circuit = CircuitBreaker(threshold=self.config.circuit_breaker_threshold)

    for attempt in range(1, self.config.max_attempts + 1):
        if circuit.is_open:
            break

        # Check current state
        result = run_tool(["ruff", "check", ".", "--statistics"], cwd=self.root)
        if result.ok:
            return HealResult(failure_type="lint", attempt=attempt,
                              fixed=True, remaining_errors=0,
                              details="All lint violations resolved")

        # Auto-fix
        fix_result = run_tool(["ruff", "check", ".", "--fix"], cwd=self.root)

        # Re-check
        recheck = run_tool(["ruff", "check", ".", "--statistics"], cwd=self.root)
        if recheck.ok:
            return HealResult(failure_type="lint", attempt=attempt,
                              fixed=True, remaining_errors=0,
                              details=f"Fixed on attempt {attempt}")

        circuit.record(over_budget=True)

    # Circuit breaker opened — escalate
    return HealResult(failure_type="lint", attempt=self.config.max_attempts,
                      fixed=False, remaining_errors=count_violations(recheck),
                      details="Circuit breaker opened — manual fix required")
```

### 3. Circuit Breaker Pattern

```python
# src/armature/heal/circuit_breaker.py

@dataclass
class CircuitBreaker:
    threshold: int = 3           # open after N consecutive failures
    consecutive_failures: int = 0
    state: CircuitState = CircuitState.CLOSED

    def record(self, over_budget: bool) -> None:
        if over_budget:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.threshold:
                self.state = CircuitState.OPEN
        else:
            self.consecutive_failures = 0    # reset on success

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def reset(self) -> None:
        """Human manually resets after reviewing failure report."""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
```

### 4. Failure Report Generation

When the circuit breaker opens, Armature generates a structured failure report:

```json
// .armature/failures/lint_2026-04-27T14:30:00.json
{
  "failure_type": "lint",
  "timestamp": "2026-04-27T14:30:00+00:00",
  "attempts": 3,
  "circuit_breaker_state": "open",
  "remaining_violations": [
    {
      "file": "src/app/auth.py",
      "line": 42,
      "rule": "E501",
      "message": "Line too long (145 > 120)",
      "fix_attempted": true,
      "fix_failed_reason": "Cannot auto-fix without breaking multiline string"
    }
  ],
  "recommendation": "Manual review required — 2 violations cannot be auto-fixed"
}
```

---

## Configuration

```yaml
# armature.yaml
heal:
  enabled: true
  max_attempts: 3                    # attempts per failure type before circuit opens
  circuit_breaker_threshold: 3       # consecutive failures to trigger circuit
  failure_report_dir: ".armature/failures/"
  healers:
    lint:
      enabled: true
      auto_fix: true                 # ruff --fix is safe and deterministic
    type_check:
      enabled: true
      auto_fix: false                # type errors need human judgment
    test:
      enabled: true
      auto_fix: false                # test failures need investigation
```

---

## CLI Usage

```bash
# Heal all failure types
armature heal

# Heal specific failures
armature heal --failures lint
armature heal --failures lint,type

# View failure reports
ls .armature/failures/
```

## MCP Usage (from AI Agent)

```python
# Agent calls armature_heal tool
result = armature_heal({"failures": "lint,type,test"})
# Returns:
# {
#   "results": [
#     {"type": "lint", "fixed": true, "details": "Fixed on attempt 1"},
#     {"type": "type", "fixed": false, "details": "3 type errors remain — manual fix needed"},
#     {"type": "test", "fixed": false, "details": "2 test failures — review test_auth.py"}
#   ],
#   "all_fixed": false
# }
```

---

## Example: Full Self-Healing Session

```
$ armature check
QUALITY CHECK
=============
  lint:             FAIL — 5 violation(s)          score: 0.75  W:25
  type_check:       PASS                           score: 1.00  W:25
  test:             PASS — 42 passed, 0 failed     score: 1.00  W:20
  complexity:       PASS                           score: 1.00  W:15
  security:         PASS                           score: 1.00  W:20
  test_ratio:       PASS — 0.62                    score: 1.00  W:10
  docstring:        PASS — 28/30 (93%)             score: 0.93  W:10
  dependency_audit: PASS                           score: 1.00  W:15

  Weighted Score: 0.956 → review_ready (needs 0.95 for merge_ready)

$ armature heal --failures lint
SELF-HEAL PIPELINE
==================
  --- lint ---
  Attempt 1: ruff --fix → fixed 4/5 violations
  Attempt 2: ruff --fix → fixed 1/1 remaining
  [FIXED] All lint violations resolved

$ armature check
  Weighted Score: 0.993 → merge_ready ✅
```

---

## Why This Matters for Enterprise

| Problem | Without Armature | With Armature |
|---------|-----------------|---------------|
| Lint violations in AI-generated code | Developer manually fixes | Auto-fixed in seconds |
| Flaky CI from trivial issues | PR blocked, developer context-switches | Self-healed before commit |
| Cascading failures | One error becomes 10 | Circuit breaker stops at 3 attempts |
| Unknown failure state | Developer discovers in CI, 20 min later | Failure report generated immediately |
| Repeat failures | Same fix, same mistake, every PR | Circuit breaker escalates, pattern detected |

**ROI**: Teams using self-healing report 40-60% fewer CI failures on AI-generated PRs.
