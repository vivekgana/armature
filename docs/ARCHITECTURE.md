# Armature Architecture

## Repository Structure

```
armature/
├── src/                        # Source code (flat package layout)
│   ├── __init__.py             # Package root
│   ├── py.typed                # PEP 561 typing marker
│   ├── _internal/              # Shared utilities (AST, subprocess, types)
│   ├── architecture/           # Pillar: Architecture enforcement
│   │   ├── boundary.py         #   Layer boundary rules
│   │   ├── conformance.py      #   Class conformance checks
│   │   └── linters/            #   Class & import linters
│   ├── budget/                 # Pillar: Token/cost tracking
│   │   ├── benchmark.py        #   Performance benchmarking
│   │   ├── budget.py           #   Core budget logic
│   │   ├── cache.py            #   Caching layer
│   │   ├── calibrator.py       #   Cost calibration
│   │   ├── circuit.py          #   Circuit breaker for budgets
│   │   ├── optimizer.py        #   Usage optimization
│   │   ├── planner.py          #   Budget planning
│   │   ├── reporter.py         #   Cost reports
│   │   ├── router.py           #   Request routing
│   │   └── tracker.py          #   Usage tracking
│   ├── cli/                    # CLI commands (Click-based)
│   │   ├── main.py             #   CLI entrypoint
│   │   ├── baseline_cmd.py     #   `armature baseline`
│   │   ├── budget_cmd.py       #   `armature budget`
│   │   ├── check_cmd.py        #   `armature check`
│   │   ├── gc_cmd.py           #   `armature gc`
│   │   ├── heal_cmd.py         #   `armature heal`
│   │   ├── hooks_cmd.py        #   `armature hooks`
│   │   ├── init_cmd.py         #   `armature init`
│   │   └── report_cmd.py       #   `armature report`
│   ├── config/                 # Configuration loading & schema
│   │   ├── defaults.py         #   Default config values
│   │   ├── discovery.py        #   Config file discovery
│   │   ├── loader.py           #   YAML config loader
│   │   └── schema.py           #   Pydantic config schema
│   ├── context/                # Pillar: Context management
│   ├── gc/                     # Pillar: Garbage collection
│   │   ├── baseline.py         #   Baseline snapshots
│   │   ├── runner.py           #   GC sweep runner
│   │   └── agents/             #   GC agents (arch, budget, dead code, docs)
│   ├── harness/                # Session harness lifecycle
│   │   ├── pre_dev.py          #   Pre-development hooks
│   │   ├── post_dev.py         #   Post-development hooks
│   │   └── session.py          #   Session management
│   ├── heal/                   # Pillar: Self-healing
│   │   ├── circuit_breaker.py  #   Escalation circuit breaker
│   │   ├── pipeline.py         #   Healing pipeline
│   │   └── healers/            #   Pluggable healers
│   ├── integrations/           # IDE & CI integrations
│   │   ├── claude_code.py      #   Claude Code hooks
│   │   ├── copilot.py          #   GitHub Copilot
│   │   ├── cursor.py           #   Cursor IDE
│   │   ├── github_actions.py   #   GitHub Actions workflow
│   │   ├── pre_commit.py       #   pre-commit hooks
│   │   └── windsurf.py         #   Windsurf IDE
│   ├── mcp/                    # MCP server
│   │   └── server.py           #   Model Context Protocol server
│   ├── quality/                # Pillar: Quality gates
│   │   ├── gate.py             #   Quality gate logic
│   │   ├── post_write.py       #   Shift-left post-write checks
│   │   ├── scorer.py           #   Quality scoring
│   │   └── runners/            #   Tool runners (ruff, mypy, pytest)
│   └── spec/                   # Spec-driven development
├── tests/                      # Test suite (mirrors src/ structure)
│   ├── conftest.py
│   ├── test_architecture/
│   ├── test_budget/
│   ├── test_cli/
│   ├── test_config/
│   ├── test_gc/
│   ├── test_heal/
│   ├── test_integrations/
│   ├── test_internal/
│   ├── test_mcp/
│   └── test_quality/
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md         #   This file
│   ├── GITHUB_SETUP.md         #   Repository setup guide
│   ├── HARNESS_ENGINEERING.md  #   Harness engineering theory
│   ├── BENCHMARKING_DESIGN.md  #   Benchmarking design doc
│   ├── SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md
│   ├── examples/               #   Config examples
│   ├── integrations/           #   Integration guides
│   └── pillars/                #   Pillar deep-dives
├── examples/                   # Example projects
│   ├── monorepo/
│   ├── python-django/
│   ├── python-fastapi/
│   └── typescript-nextjs/
├── skills/                     # Claude Code slash commands
│   ├── armature-budget.md
│   ├── armature-check.md
│   ├── armature-gc.md
│   └── armature-heal.md
├── pyproject.toml              # Project config (hatchling build)
├── LICENSE                     # MIT
└── README.md
```

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI (Click)                              │
│  main.py ─► init | check | heal | gc | budget | hooks | report │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ Quality  │ │  Heal  │ │   GC   │ │ Budget │ │  Arch  │
│          │ │        │ │        │ │        │ │        │
│ gate     │ │pipeline│ │baseline│ │tracker │ │boundary│
│ scorer   │ │circuit │ │runner  │ │planner │ │conform.│
│ post_wrt │ │breaker │ │agents/ │ │cache   │ │linters/│
│ runners/ │ │healers/│ │  arch  │ │router  │ └────────┘
└────┬─────┘ └───┬────┘ │  budg  │ │optimiz.│
     │           │      │  dead  │ │calibr. │
     │           │      │  docs  │ │benchm. │
     │           │      └────────┘ │reporter│
     │           │                 │circuit │
     │           │                 └────────┘
     ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Config Layer                             │
│          schema.py  ◄──  loader.py  ◄──  discovery.py           │
│                          defaults.py                            │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     _internal (shared utils)                    │
│              ast_utils.py | subprocess_utils.py | types.py      │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Integrations                               │
│   claude_code | cursor | copilot | windsurf | github_actions    │
│                      pre_commit                                 │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Server                               │
│              Model Context Protocol interface                   │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Harness Lifecycle                            │
│            pre_dev.py  ──►  session  ──►  post_dev.py           │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
                    armature.yaml
                         │
                         ▼
             ┌───── Config Layer ─────┐
             │   discovery ► loader   │
             │   schema validation    │
             └──────────┬────────────┘
                        │
          ┌─────────────┼─────────────────┐
          ▼             ▼                 ▼
    ┌──────────┐  ┌──────────┐     ┌──────────┐
    │ Pre-Dev  │  │  Agent   │     │ Post-Dev │
    │  Hooks   │  │ Session  │     │  Hooks   │
    │          │  │          │     │          │
    │ context  │  │ quality  │     │ gc sweep │
    │ baseline │  │ budget   │     │ report   │
    │ budget   │  │ heal     │     │ baseline │
    └──────────┘  └──────────┘     └──────────┘
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
         ┌────────┐┌───────┐┌───────┐
         │Quality ││Budget ││ Heal  │
         │ Gate   ││Track  ││ Fix   │
         └───┬────┘└───┬───┘└───┬───┘
             │         │        │
             ▼         ▼        ▼
         Pass/Fail   Report   Auto-fix
                              or Escalate
```

## The 6 Pillars

| Pillar | Module | Purpose |
|--------|--------|---------|
| **Budget** | `budget/` | Token/cost tracking, optimization, benchmarking |
| **Quality** | `quality/` | Lint, type, test checks with quality gates |
| **Context** | `context/` | CLAUDE.md generation, progressive disclosure |
| **Architecture** | `architecture/` | Layer boundaries, class conformance |
| **GC** | `gc/` | Dead code, stale docs, architecture drift |
| **Self-Heal** | `heal/` | Auto-fix lint, circuit breaker escalation |

## Key Dependencies

- **click** -- CLI framework
- **pydantic** -- Config schema validation
- **pyyaml** -- YAML config parsing
- **rich** -- Terminal output formatting
- **ruff/mypy/pytest** -- Optional quality tools
