# /armature-gc

Run Armature garbage collection agents to detect drift and entropy.

## Usage

```
/armature-gc                    # Run all GC agents
/armature-gc architecture       # Run only architecture drift check
/armature-gc docs               # Run only documentation staleness check
/armature-gc dead_code          # Run only dead code detection
/armature-gc budget             # Run only budget audit
```

## What it does

1. **Architecture**: Detects boundary violations and conformance drift
2. **Docs**: Finds stale file/class references in documentation
3. **Dead code**: Finds oversized functions, orphaned tests, unused patterns
4. **Budget**: Audits cost data across specs, flags over-budget work

## Instructions

Run `armature gc` (or with a specific agent name) and present findings.
For each finding, suggest concrete fixes.
