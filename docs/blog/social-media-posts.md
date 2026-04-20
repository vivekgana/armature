# Social Media Posts for Armature Launch

Copy-paste these for each platform.

---

## LinkedIn

**Introducing Armature — Governance for AI Coding Agents**

AI coding agents generate code fast. But speed without governance is a liability.

We built Armature to solve the governance gap: budget control, quality gates, architectural boundaries, and spec-to-test traceability — all running automatically during development.

Key features:
- Per-spec token & cost tracking with circuit breakers
- Quality gates (lint + type-check + test scoring)
- Architecture boundary enforcement
- Spec-driven development with YAML contracts
- MCP integration with Claude Code, Cursor, and more
- Ossature compatibility bridge for migration

The framework enforces that every acceptance criterion has a test, every feature stays within budget, and every merge passes quality thresholds.

Open source (MIT) with full examples: Python FastAPI, TypeScript Next.js, Python Monorepo.

GitHub: https://github.com/vivekgana/armature
Blog: https://vivekgana.github.io/armature/blog/2026-04-20-introducing-armature.html

#AIEngineering #DevTools #ClaudeCode #MCP #OpenSource #HarnessEngineering #SpecDriven

---

## Twitter/X (Thread)

**Tweet 1:**
Introducing Armature — the governance framework for AI coding agents.

AI agents write code fast. But who's checking the quality, budget, and architecture?

Armature does. Automatically. During development, not after.

Open source: github.com/vivekgana/armature

**Tweet 2:**
How it works:

1. Write a spec (YAML contract)
2. `armature pre-dev` captures baseline
3. AI agent writes code (armature checks every file write)
4. `armature post-dev` detects regressions
5. Budget report shows token/cost spend

Every AC traced to a test.

**Tweet 3:**
Six pillars:
- Budget: per-spec token tracking + circuit breakers
- Quality: lint/type-check/test scoring + merge gates
- Architecture: layer boundaries enforced
- Context: progressive disclosure for agents
- GC: background drift detection
- Self-Heal: auto-fix lint + type errors

**Tweet 4:**
Ships as an MCP server — connects directly to Claude Code, Cursor, or any MCP-compatible agent.

11 tools: check_quality, get_budget_status, check_architecture, capture_baseline, detect_regressions...

`pip install armature && armature init`

**Tweet 5:**
Full examples included:
- Python FastAPI: JWT auth + pagination fix
- TypeScript Next.js: dark mode + middleware refactor
- Python Monorepo: shared auth + GraphQL spike

Each with spec files, generated output, and test traceability.

github.com/vivekgana/armature

---

## Hacker News

**Title:** Armature: Governance framework for AI coding agents (budget, quality gates, spec traceability)

**Comment:**
Hi HN — I built Armature to solve a problem I kept hitting: AI coding agents write great code, but there's no governance layer. No budget tracking, no quality gates, no architectural boundary enforcement.

Armature wraps around your existing workflow and adds:
- Per-spec token/cost tracking (JSONL, circuit breakers)
- Quality gates (lint + type-check + test scoring → draft/review_ready/merge_ready)
- Architectural boundary enforcement
- Spec-driven development with YAML contracts
- Automatic traceability (acceptance criteria → test docstrings)
- MCP server integration (works with Claude Code, Cursor)

It's not a code generator — it governs what your existing agents produce. Think CI/CD, but running *during* development instead of after push.

Full examples with generated output for Python FastAPI, TypeScript Next.js, and Python Monorepo.

MIT licensed. Would love feedback on what governance features teams actually need.

---

## Dev.to / Hashnode (short version)

**Title:** Stop Flying Blind with AI Coding Agents

**Subtitle:** Armature adds budget control, quality gates, and spec traceability to AI-assisted development.

Use the Medium article content (docs/blog/medium-article.md) with Dev.to/Hashnode formatting (their markdown parsers handle it natively).
