---
layout: default
title: "Introducing Armature: Governance for AI Coding Agents"
date: 2026-04-20
author: Ganapathi Ekambaram
description: "How Armature brings budget control, quality gates, and spec traceability to AI-assisted development."
image: https://raw.githubusercontent.com/vivekgana/armature/main/docs/blog/assets/armature-banner.png
---

# Introducing Armature: Governance for AI Coding Agents

*April 20, 2026*

AI coding agents generate code fast. But speed without governance is a liability. **Armature** is a harness engineering framework that wraps around your AI coding workflow and adds the controls you need: budget tracking, quality gates, architectural boundary enforcement, and spec-to-test traceability.

---

## Why We Built This

Every team using AI coding agents faces the same questions:

- "How much did that feature cost in API tokens?"
- "Did the generated code actually pass our quality bar?"
- "Is there a human in the loop before this merges?"
- "Can I trace this test back to a specific acceptance criterion?"

Armature answers all of them — automatically, during development, not after.

## The Six Pillars

| Pillar | What It Does |
|--------|-------------|
| **Budget** | Per-spec token/cost tracking with circuit breakers |
| **Quality** | Lint + type-check + test scoring with merge-ready gates |
| **Architecture** | Layer definitions, boundary enforcement, import rules |
| **Context** | Progressive disclosure — agents see only relevant code |
| **GC** | Background agents detect drift, dead code, stale docs |
| **Self-Heal** | Auto-fix pipeline for lint and type errors |

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#4CAF50', 'primaryTextColor': '#fff', 'lineColor': '#333', 'secondaryColor': '#2196F3'}}}%%
flowchart TB
    Agent["🤖 AI Coding Agent"]

    Budget["💰 Budget\nToken & cost tracking\nCircuit breakers"]
    Quality["✅ Quality\nLint, type-check, tests\nQuality gates"]
    Arch["🏗️ Architecture\nLayer boundaries\nImport enforcement"]
    Context["📋 Context\nProgressive disclosure\nNarrow scope"]
    GC["🧹 GC\nDrift detection\nDead code removal"]
    Heal["🔧 Self-Heal\nAuto-fix lint errors\n3-attempt pipeline"]

    Budget --> Agent
    Quality --> Agent
    Arch --> Agent
    Context --> Agent
    GC --> Agent
    Heal --> Agent

    style Agent fill:#1a1a2e,color:#fff,stroke:#e94560,stroke-width:3px
    style Budget fill:#4CAF50,color:#fff,stroke:#2E7D32,stroke-width:2px
    style Quality fill:#2196F3,color:#fff,stroke:#1565C0,stroke-width:2px
    style Arch fill:#9C27B0,color:#fff,stroke:#6A1B9A,stroke-width:2px
    style Context fill:#FF9800,color:#fff,stroke:#E65100,stroke-width:2px
    style GC fill:#f44336,color:#fff,stroke:#C62828,stroke-width:2px
    style Heal fill:#009688,color:#fff,stroke:#00695C,stroke-width:2px
```

## Spec-Driven Workflow

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#2196F3', 'lineColor': '#333'}}}%%
flowchart LR
    A["📝 Write Spec"] --> B["🔍 pre-dev\nCapture baseline"]
    B --> C["🤖 Develop\nAgent writes code"]
    C --> D{"post-write\nhook"}
    D -->|"lint + type\ncheck pass"| C
    D -->|"all done"| E["📊 post-dev\nRegression check"]
    E --> F["💰 Budget\nReport"]
    F --> G{"🧑 Human\nGate"}
    G -->|"approved"| H["✅ Merge"]
    G -->|"rejected"| C

    style A fill:#FF9800,color:#fff,stroke:#E65100
    style B fill:#2196F3,color:#fff,stroke:#1565C0
    style C fill:#9C27B0,color:#fff,stroke:#6A1B9A
    style D fill:#FFC107,color:#000,stroke:#FF8F00
    style E fill:#2196F3,color:#fff,stroke:#1565C0
    style F fill:#4CAF50,color:#fff,stroke:#2E7D32
    style G fill:#f44336,color:#fff,stroke:#C62828
    style H fill:#4CAF50,color:#fff,stroke:#2E7D32
```

Every spec is a YAML contract:

```yaml
spec_id: "SPEC-2026-Q2-001"
title: "Add user authentication endpoint"
type: feature

acceptance_criteria:
  - id: AC-1
    description: "POST /auth/register returns 201"
    testable: true

eval:
  unit_test_coverage_min: 90
  integration_test_required: true
```

Armature enforces the `eval` section — if your coverage drops below 90%, the quality gate won't pass.

## Live Demo: Three Example Projects

We shipped complete `output/` folders showing what Armature-governed AI agents produce:

### Python FastAPI
- JWT auth endpoints (register, login, token validation)
- Pagination bugfix with regression tests
- Every function docstring traces back to an AC

### TypeScript Next.js
- Dark mode toggle (CSS custom properties, localStorage, FOUC prevention)
- Composable API middleware (`withAuth`, `withLogging`, `withValidation`)
- Jest tests with spec traceability comments

### Python Monorepo
- Shared auth package for FastAPI + Celery
- GraphQL gateway spike — 3-day investigation → NO-GO recommendation
- Decision doc with architecture diagrams and performance benchmarks

## Comparing Armature vs Ossature

For teams already using Ossature, the compatibility bridge converts and compares:

```bash
armature spec compare-all
```

```
my-fastapi-app vs Spenny       | MEETS=4, GAPS=6
my-nextjs-app  vs math_quest   | MEETS=1, GAPS=5
my-monorepo    vs markman      | MEETS=2, GAPS=4
```

The gaps are where Armature adds value: human gates, spec traceability, quality thresholds, and budget controls that Ossature doesn't provide.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#673AB7'}}}%%
flowchart LR
    Spec["📄 Spec\nSPEC-2026-Q2-001"] --> AC1["AC-1\nRegister returns 201"]
    Spec --> AC2["AC-2\nLogin returns JWT"]
    Spec --> AC3["AC-3\n401 on bad creds"]

    AC1 --> UT1["🧪 Unit Test\ntest_register_creates_user"]
    AC2 --> UT2["🧪 Unit Test\ntest_valid_credentials_return_token"]
    AC3 --> UT3["🧪 Unit Test\ntest_invalid_password_returns_none"]

    UT1 --> IT["🔗 Integration\ntest_auth_endpoint"]
    UT2 --> IT
    UT3 --> IT

    IT --> TM["📋 Traceability\nMatrix: 100% covered"]

    style Spec fill:#FF9800,color:#fff,stroke:#E65100
    style AC1 fill:#FFC107,color:#000,stroke:#FF8F00
    style AC2 fill:#FFC107,color:#000,stroke:#FF8F00
    style AC3 fill:#FFC107,color:#000,stroke:#FF8F00
    style UT1 fill:#2196F3,color:#fff,stroke:#1565C0
    style UT2 fill:#2196F3,color:#fff,stroke:#1565C0
    style UT3 fill:#2196F3,color:#fff,stroke:#1565C0
    style IT fill:#9C27B0,color:#fff,stroke:#6A1B9A
    style TM fill:#4CAF50,color:#fff,stroke:#2E7D32
```

## MCP Integration

Armature is an MCP server — it connects directly to Claude Code, Cursor, or any MCP-compatible agent:

```bash
pip install armature-harness
```

11 tools available: `check_quality`, `get_budget_status`, `check_architecture`, `capture_baseline`, `detect_regressions`, `suggest_optimizations`, and more.

## Get Started

```bash
pip install armature-harness
armature init
# Write your first spec
armature pre-dev SPEC-2026-Q2-001
# ... develop with your AI agent ...
armature post-dev SPEC-2026-Q2-001
```

## Links

- **GitHub:** [github.com/vivekgana/armature](https://github.com/vivekgana/armature)
- **MCP Registry:** `io.github.vivekgana/armature`
- **Spec Guide:** [SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md](https://github.com/vivekgana/armature/blob/main/docs/SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md)
- **Spec File Format:** [SPEC_FILE_STRUCTURE.md](https://github.com/vivekgana/armature/blob/main/docs/SPEC_FILE_STRUCTURE.md)

---

*Armature is open source (MIT). Star us on GitHub and tell us what governance features your team needs.*

---

[Back to Blog](./index.html)
