# /armature-check

Run all Armature quality sensors on the current project.

## Usage

```
/armature-check              # Check entire project
/armature-check src/api.py   # Check a single file
```

## What it does

1. Runs configured lint tool (ruff, eslint, etc.)
2. Runs configured type checker (mypy, tsc, etc.)
3. Checks architectural layer boundaries
4. Checks class conformance rules
5. Calculates quality score (draft/review_ready/merge_ready)

## Instructions

Run `armature check` and show the user the results. If there are violations, suggest fixes using the remediation messages from each violation.

If a file path is provided, run `armature check --file <path>` instead.
