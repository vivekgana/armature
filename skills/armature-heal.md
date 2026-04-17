# /armature-heal

Run the Armature self-healing pipeline to auto-fix quality issues.

## Usage

```
/armature-heal                        # Heal all failure types
/armature-heal lint                   # Heal only lint violations
/armature-heal lint,type              # Heal lint and type errors
```

## What it does

1. **Lint healer**: Runs `ruff check --fix` to auto-fix lint violations
2. **Type healer**: Reports mypy errors with fix suggestions
3. **Test healer**: Runs failing tests and reports diagnostics

Each healer has a circuit breaker (max 3 attempts). If the circuit opens,
it stops retrying and escalates with a structured failure report.

## Instructions

Run `armature heal --failures <types>` and show the results. If any failures
are escalated (circuit open), read the failure report and help the user fix
the remaining issues manually.
