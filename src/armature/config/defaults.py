"""Language/framework-specific default configurations."""

from __future__ import annotations

from armature.config.schema import (
    ArchitectureConfig,
    ArmatureConfig,
    BoundaryRule,
    ClaudeCodeConfig,
    HealConfig,
    HealerConfig,
    IntegrationsConfig,
    LayerDef,
    PostWriteConfig,
    ProjectConfig,
    QualityConfig,
    ToolCheckConfig,
)


def defaults_for_python_fastapi() -> ArmatureConfig:
    """Default config for a Python FastAPI project."""
    return ArmatureConfig(
        project=ProjectConfig(language="python", framework="fastapi", src_dir="app/", test_dir="tests/"),
        quality=QualityConfig(
            enabled=True,
            checks={
                "lint": ToolCheckConfig(tool="ruff", args=["check", "--statistics"], weight=25),
                "type_check": ToolCheckConfig(tool="mypy", args=["--no-error-summary"], weight=25),
                "test": ToolCheckConfig(tool="pytest", args=["-x", "--tb=short"], weight=20, coverage_min=85),
            },
            post_write=PostWriteConfig(enabled=True),
        ),
        architecture=ArchitectureConfig(
            enabled=True,
            layers=[
                LayerDef(name="models", dirs=["app/models/"]),
                LayerDef(name="services", dirs=["app/services/"]),
                LayerDef(name="routes", dirs=["app/routes/", "app/api/"]),
            ],
            boundaries=[
                BoundaryRule(**{"from": "models", "to": ["routes"]}),
                BoundaryRule(**{"from": "services", "to": ["routes"]}),
            ],
            allowed_shared=["app/config/", "app/utils/", "app/errors/"],
        ),
        heal=HealConfig(enabled=True, healers={"lint": HealerConfig(auto_fix=True)}),
        integrations=IntegrationsConfig(claude_code=ClaudeCodeConfig(enabled=True)),
    )


def defaults_for_python_django() -> ArmatureConfig:
    """Default config for a Python Django project."""
    return ArmatureConfig(
        project=ProjectConfig(language="python", framework="django", src_dir="./", test_dir="tests/"),
        quality=QualityConfig(
            enabled=True,
            checks={
                "lint": ToolCheckConfig(tool="ruff", args=["check"], weight=25),
                "type_check": ToolCheckConfig(tool="mypy", args=["--no-error-summary"], weight=25),
                "test": ToolCheckConfig(tool="pytest", args=["-x"], weight=20, coverage_min=80),
            },
        ),
        architecture=ArchitectureConfig(
            enabled=True,
            layers=[
                LayerDef(name="models", dirs=["*/models/"]),
                LayerDef(name="views", dirs=["*/views/"]),
                LayerDef(name="serializers", dirs=["*/serializers/"]),
            ],
            boundaries=[BoundaryRule(**{"from": "models", "to": ["views"]})],
        ),
        heal=HealConfig(enabled=True),
    )


def defaults_for_typescript_nextjs() -> ArmatureConfig:
    """Default config for a TypeScript Next.js project."""
    return ArmatureConfig(
        project=ProjectConfig(language="typescript", framework="nextjs", src_dir="src/", test_dir="__tests__/"),
        quality=QualityConfig(
            enabled=True,
            checks={
                "lint": ToolCheckConfig(tool="eslint", args=["--ext", ".ts,.tsx"], weight=25),
                "type_check": ToolCheckConfig(tool="tsc", args=["--noEmit"], weight=25),
                "test": ToolCheckConfig(tool="jest", args=["--passWithNoTests"], weight=20, coverage_min=80),
            },
        ),
        architecture=ArchitectureConfig(
            enabled=True,
            layers=[
                LayerDef(name="lib", dirs=["src/lib/"]),
                LayerDef(name="server", dirs=["src/app/api/"]),
                LayerDef(name="components", dirs=["src/components/"]),
            ],
            boundaries=[BoundaryRule(**{"from": "lib", "to": ["components"]})],
        ),
        heal=HealConfig(enabled=True),
    )


def get_defaults(language: str, framework: str) -> ArmatureConfig:
    """Get framework-specific defaults."""
    key = f"{language}_{framework}"
    defaults_map = {
        "python_fastapi": defaults_for_python_fastapi,
        "python_django": defaults_for_python_django,
        "typescript_nextjs": defaults_for_typescript_nextjs,
    }
    factory = defaults_map.get(key)
    if factory:
        return factory()
    return ArmatureConfig(
        project=ProjectConfig(language=language, framework=framework),
        quality=QualityConfig(enabled=True),
        heal=HealConfig(enabled=True),
    )
