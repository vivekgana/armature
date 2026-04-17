"""Pydantic models for armature.yaml configuration schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Project ---

class ProjectConfig(BaseModel):
    """Top-level project metadata."""
    name: str = ""
    language: str = "python"
    framework: str = ""
    src_dir: str = "src/"
    test_dir: str = "tests/"


# --- Budget (Pillar 1) ---

class BudgetTier(BaseModel):
    """Token/cost limits for a complexity tier."""
    max_tokens: int = 500_000
    max_cost_usd: float = 10.0


class BudgetCircuitConfig(BaseModel):
    """Circuit breaker for budget overruns."""
    consecutive_over_budget: int = 3


class ProviderRoutingConfig(BaseModel):
    """Multi-provider model routing configuration."""
    strategy: str = "cost_optimized"  # cost_optimized | quality_first | single_model
    default_model: str = "claude-sonnet"
    enabled_models: list[str] = Field(default_factory=lambda: ["claude-sonnet"])
    quality_floor: float = 0.75
    premium_intents: list[str] = Field(
        default_factory=lambda: ["complex_code_gen", "architecture"]
    )


class SemanticCacheConfig(BaseModel):
    """Application-level response cache using structural fingerprints."""
    enabled: bool = False
    storage: str = ".armature/cache/"
    max_size_mb: int = 100
    ttl_days: int = 7


class CalibrationConfig(BaseModel):
    """Auto-calibration of budget multipliers from historical actuals."""
    enabled: bool = False
    auto_calibrate: bool = True
    min_specs: int = 3
    task_overrides: dict[str, float] = Field(default_factory=dict)
    model_verbosity_overrides: dict[str, float] = Field(default_factory=dict)
    cache_hit_rate_override: float | None = None


class MonitoringConfig(BaseModel):
    """Cross-provider usage monitoring and anomaly detection."""
    track_provider: bool = True
    track_latency: bool = True
    track_cache_hits: bool = True
    anomaly_threshold: float = 3.0


class BudgetConfig(BaseModel):
    """Pillar 1: Budgeted Development."""
    enabled: bool = False
    defaults: dict[str, BudgetTier] = Field(default_factory=lambda: {
        "low": BudgetTier(max_tokens=100_000, max_cost_usd=2.0),
        "medium": BudgetTier(max_tokens=500_000, max_cost_usd=10.0),
        "high": BudgetTier(max_tokens=1_000_000, max_cost_usd=20.0),
        "critical": BudgetTier(max_tokens=2_000_000, max_cost_usd=40.0),
    })
    phase_allocation: dict[str, int] = Field(default_factory=lambda: {
        "validate": 5, "audit": 10, "plan": 15,
        "build": 40, "test": 25, "review": 5,
    })
    circuit_breaker: BudgetCircuitConfig = Field(default_factory=BudgetCircuitConfig)
    storage: str = ".armature/budget/"
    providers: ProviderRoutingConfig = Field(default_factory=ProviderRoutingConfig)
    cache: SemanticCacheConfig = Field(default_factory=SemanticCacheConfig)
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)


# --- Quality (Pillar 2) ---

class ToolCheckConfig(BaseModel):
    """Configuration for a single quality check tool."""
    tool: str = ""
    args: list[str] = Field(default_factory=list)
    weight: int = 25
    coverage_min: int | None = None


class ComplexityConfig(BaseModel):
    """Complexity thresholds."""
    max_cyclomatic: int = 10
    max_function_lines: int = 50
    weight: int = 15


class ConformanceWeight(BaseModel):
    """Conformance check weight."""
    weight: int = 15


class PostWriteConfig(BaseModel):
    """Shift-left: checks run on every file write."""
    enabled: bool = True
    tools: list[str] = Field(default_factory=lambda: ["lint", "type_check"])
    max_output_lines: int = 5


class QualityConfig(BaseModel):
    """Pillar 2: Internal Quality Assessment."""
    enabled: bool = True
    gates: dict[str, float] = Field(default_factory=lambda: {
        "draft": 0.70, "review_ready": 0.85, "merge_ready": 0.95,
    })
    checks: dict[str, ToolCheckConfig] = Field(default_factory=lambda: {
        "lint": ToolCheckConfig(tool="ruff", args=["check", "--statistics"], weight=25),
        "type_check": ToolCheckConfig(tool="mypy", args=["--no-error-summary"], weight=25),
        "test": ToolCheckConfig(tool="pytest", args=["-x", "--tb=short"], weight=20, coverage_min=90),
    })
    complexity: ComplexityConfig = Field(default_factory=ComplexityConfig)
    conformance: ConformanceWeight = Field(default_factory=ConformanceWeight)
    post_write: PostWriteConfig = Field(default_factory=PostWriteConfig)


# --- Context (Pillar 3) ---

class AgentMDConfig(BaseModel):
    """Agent instruction file configuration."""
    path: str = "CLAUDE.md"
    max_lines: int = 200
    deep_docs: list[str] = Field(default_factory=list)


class ContextConfig(BaseModel):
    """Pillar 3: Context Engineering."""
    enabled: bool = False
    agent_md: AgentMDConfig = Field(default_factory=AgentMDConfig)
    progressive_disclosure: bool = True
    memory_dir: str = ".claude/memory/"


# --- Architecture (Pillar 4) ---

class LayerDef(BaseModel):
    """Definition of an architectural layer."""
    name: str
    dirs: list[str]


class BoundaryRule(BaseModel):
    """A single boundary enforcement rule: 'from' cannot import 'to'."""
    from_layer: str = Field(alias="from")
    to_layers: list[str] = Field(alias="to")

    model_config = {"populate_by_name": True}


class ConformanceRule(BaseModel):
    """Class hierarchy enforcement rule."""
    pattern: str
    base_class: str
    required_methods: list[str] = Field(default_factory=list)
    required_attributes: list[str] = Field(default_factory=list)
    dirs: list[str] = Field(default_factory=list)


class SchemaSyncConfig(BaseModel):
    """Model-to-DDL/schema sync checking."""
    enabled: bool = False
    ddl_dir: str = "sql/ddl/"
    model_dirs: list[str] = Field(default_factory=list)


class ArchitectureConfig(BaseModel):
    """Pillar 4: Architectural Constraints."""
    enabled: bool = False
    layers: list[LayerDef] = Field(default_factory=list)
    boundaries: list[BoundaryRule] = Field(default_factory=list)
    allowed_shared: list[str] = Field(default_factory=list)
    conformance: list[ConformanceRule] = Field(default_factory=list)
    schema_sync: SchemaSyncConfig = Field(default_factory=SchemaSyncConfig)
    custom_linters: list[str] = Field(default_factory=list)


# --- GC (Pillar 5) ---

class GCAgentConfig(BaseModel):
    """Configuration for a single GC agent."""
    enabled: bool = True
    cadence: str = "weekly"
    watched_files: list[str] = Field(default_factory=list)
    thresholds: dict[str, object] = Field(default_factory=dict)


class GCConfig(BaseModel):
    """Pillar 5: Garbage Collection."""
    enabled: bool = False
    storage: str = ".armature/gc/"
    agents: dict[str, GCAgentConfig] = Field(default_factory=lambda: {
        "architecture": GCAgentConfig(cadence="daily"),
        "docs": GCAgentConfig(cadence="weekly"),
        "dead_code": GCAgentConfig(cadence="weekly"),
        "budget": GCAgentConfig(cadence="per-spec"),
    })


# --- Heal (Pillar 6) ---

class HealerConfig(BaseModel):
    """Configuration for a single healer."""
    enabled: bool = True
    auto_fix: bool = False


class HealConfig(BaseModel):
    """Pillar 6: Self-Healing Pipeline."""
    enabled: bool = True
    max_attempts: int = 3
    circuit_breaker_threshold: int = 3
    failure_report_dir: str = ".armature/failures/"
    healers: dict[str, HealerConfig] = Field(default_factory=lambda: {
        "lint": HealerConfig(auto_fix=True),
        "type_check": HealerConfig(auto_fix=False),
        "test": HealerConfig(auto_fix=False),
    })


# --- Specs (Optional) ---

class TraceabilityConfig(BaseModel):
    """AC-to-test traceability settings."""
    enabled: bool = False
    pattern: str = r"(SPEC-\d{4}-Q\d-\d{3})\s*/\s*(AC-\d+)"


class SpecConfig(BaseModel):
    """Optional spec management for spec-driven projects."""
    enabled: bool = False
    dir: str = "specs/"
    templates_dir: str = "specs/templates/"
    id_pattern: str = r"^SPEC-\d{4}-Q[1-4]-\d{3}$"
    required_fields: list[str] = Field(default_factory=lambda: [
        "spec_id", "title", "type", "description", "acceptance_criteria",
    ])
    traceability: TraceabilityConfig = Field(default_factory=TraceabilityConfig)


# --- Integrations ---

class ClaudeCodeConfig(BaseModel):
    """Claude Code integration settings."""
    enabled: bool = False
    post_tool_use: bool = True
    pre_session: bool = True


class CursorConfig(BaseModel):
    """Cursor integration settings."""
    enabled: bool = False


class CopilotConfig(BaseModel):
    """GitHub Copilot integration settings."""
    enabled: bool = False


class PreCommitConfig(BaseModel):
    """pre-commit integration settings."""
    enabled: bool = False


class GitHubActionsConfig(BaseModel):
    """GitHub Actions integration settings."""
    enabled: bool = False


class IntegrationsConfig(BaseModel):
    """IDE/Agent integration settings."""
    claude_code: ClaudeCodeConfig = Field(default_factory=ClaudeCodeConfig)
    cursor: CursorConfig = Field(default_factory=CursorConfig)
    copilot: CopilotConfig = Field(default_factory=CopilotConfig)
    pre_commit: PreCommitConfig = Field(default_factory=PreCommitConfig)
    github_actions: GitHubActionsConfig = Field(default_factory=GitHubActionsConfig)


# --- Root Config ---

class ArmatureConfig(BaseModel):
    """Root configuration model for armature.yaml."""
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    architecture: ArchitectureConfig = Field(default_factory=ArchitectureConfig)
    gc: GCConfig = Field(default_factory=GCConfig)
    heal: HealConfig = Field(default_factory=HealConfig)
    specs: SpecConfig = Field(default_factory=SpecConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)
