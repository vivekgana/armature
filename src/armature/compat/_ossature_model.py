"""Data model and parser for ossature projects.

Parses ossature.toml, .smd (spec markdown), and .amd (architecture markdown)
files into typed dataclasses. No armature imports -- pure parsing layer.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_DIRECTIVE_RE = re.compile(r"^@(\w+):\s*(.+)$", re.MULTILINE)
_DEPENDS_SPLIT_RE = re.compile(r"[,\s]+")


@dataclass
class OssatureProject:
    name: str = ""
    version: str = "0.1.0"
    spec_dir: str = "specs"
    context_dir: str = "context"


@dataclass
class OssatureOutput:
    language: str = "python"
    dir: str = "output"


@dataclass
class OssatureBuild:
    setup: str = ""
    verify: str = ""
    test: str = ""
    max_fix_attempts: int = 3


@dataclass
class OssatureTest:
    runner: str = ""
    coverage: bool = False
    coverage_threshold: float = 0.0


@dataclass
class OssatureLLM:
    model: str = ""
    audit: str = ""
    planner: str = ""
    fixer: str = ""


@dataclass
class OssatureSpec:
    """Parsed from a .smd file."""
    id: str = ""
    status: str = "draft"
    priority: str = "medium"
    depends: list[str] = field(default_factory=list)
    body: str = ""
    source_file: str = ""


@dataclass
class OssatureComponent:
    """Parsed from a .amd file."""
    spec: str = ""
    path: str = ""
    depends: list[str] = field(default_factory=list)
    name: str = ""
    body: str = ""
    source_file: str = ""


@dataclass
class OssatureProjectFull:
    project: OssatureProject = field(default_factory=OssatureProject)
    output: OssatureOutput = field(default_factory=OssatureOutput)
    build: OssatureBuild = field(default_factory=OssatureBuild)
    test: OssatureTest = field(default_factory=OssatureTest)
    llm: OssatureLLM = field(default_factory=OssatureLLM)
    specs: list[OssatureSpec] = field(default_factory=list)
    components: list[OssatureComponent] = field(default_factory=list)
    root: Path = field(default_factory=Path)


def _extract_directives(text: str) -> dict[str, str]:
    """Extract all @key: value directives from markdown text."""
    return {m.group(1).lower(): m.group(2).strip() for m in _DIRECTIVE_RE.finditer(text)}


def _parse_depends(raw: str) -> list[str]:
    """Parse a depends value like 'A, B' or 'A B' or '[]' into a list."""
    cleaned = raw.strip("[]")
    if not cleaned:
        return []
    return [s for s in _DEPENDS_SPLIT_RE.split(cleaned) if s]


def parse_ossature_toml(path: Path) -> dict[str, object]:
    """Parse an ossature.toml file and return the raw dict."""
    with open(path, "rb") as f:
        return tomllib.load(f)


def parse_smd_file(path: Path) -> OssatureSpec:
    """Parse a .smd (spec markdown) file, extracting @ directives."""
    text = path.read_text(encoding="utf-8")
    directives = _extract_directives(text)

    body_lines = [line for line in text.splitlines() if not line.strip().startswith("@")]
    body = "\n".join(body_lines).strip()

    return OssatureSpec(
        id=directives.get("id", ""),
        status=directives.get("status", "draft"),
        priority=directives.get("priority", "medium"),
        depends=_parse_depends(directives.get("depends", "")),
        body=body,
        source_file=str(path),
    )


def parse_amd_file(path: Path) -> list[OssatureComponent]:
    """Parse a .amd (architecture markdown) file.

    A single .amd may define multiple components via ### headings with @path.
    """
    text = path.read_text(encoding="utf-8")
    top_directives = _extract_directives(text)

    sections = re.split(r"^###\s+", text, flags=re.MULTILINE)
    components: list[OssatureComponent] = []

    if len(sections) <= 1:
        directives = top_directives
        return [OssatureComponent(
            spec=directives.get("spec", ""),
            path=directives.get("path", ""),
            depends=_parse_depends(directives.get("depends", "")),
            name=directives.get("id", path.stem),
            body=text,
            source_file=str(path),
        )]

    spec_ref = top_directives.get("spec", "")

    for section in sections[1:]:
        lines = section.splitlines()
        name = lines[0].strip() if lines else ""
        section_text = "\n".join(lines[1:])
        directives = _extract_directives(section_text)

        comp_path = directives.get("path", "")
        if not comp_path:
            continue

        depends_raw = directives.get("depends", "")
        if not depends_raw:
            body_lower = section_text.lower()
            dep_match = re.search(r"\*\*depends on:\*\*\s*(.+)", body_lower)
            if dep_match and "none" not in dep_match.group(1):
                depends_raw = dep_match.group(1)

        components.append(OssatureComponent(
            spec=spec_ref,
            path=comp_path,
            depends=_parse_depends(depends_raw),
            name=name,
            body=section_text,
            source_file=str(path),
        ))

    return components


def load_ossature_project(root: Path) -> OssatureProjectFull:
    """Load and parse a complete ossature project from its root directory."""
    toml_path = root / "ossature.toml"
    if not toml_path.exists():
        raise FileNotFoundError(f"No ossature.toml found at {root}")

    raw = parse_ossature_toml(toml_path)

    proj_raw = raw.get("project", {})
    project = OssatureProject(
        name=proj_raw.get("name", root.name),
        version=proj_raw.get("version", "0.1.0"),
        spec_dir=proj_raw.get("spec_dir", "specs"),
        context_dir=proj_raw.get("context_dir", "context"),
    )

    out_raw = raw.get("output", {})
    output = OssatureOutput(
        language=out_raw.get("language", "python"),
        dir=out_raw.get("dir", "output"),
    )

    build_raw = raw.get("build", {})
    build = OssatureBuild(
        setup=build_raw.get("setup", ""),
        verify=build_raw.get("verify", ""),
        test=build_raw.get("test", ""),
        max_fix_attempts=build_raw.get("max_fix_attempts", 3),
    )

    test_raw = raw.get("test", {})
    test = OssatureTest(
        runner=test_raw.get("runner", ""),
        coverage=test_raw.get("coverage", False),
        coverage_threshold=test_raw.get("coverage_threshold", 0.0),
    )

    llm_raw = raw.get("llm", {})
    llm = OssatureLLM(
        model=llm_raw.get("model", ""),
        audit=llm_raw.get("audit", ""),
        planner=llm_raw.get("planner", ""),
        fixer=llm_raw.get("fixer", ""),
    )

    spec_dir = root / project.spec_dir
    specs: list[OssatureSpec] = []
    if spec_dir.is_dir():
        for smd in sorted(spec_dir.rglob("*.smd")):
            specs.append(parse_smd_file(smd))

    components: list[OssatureComponent] = []
    for amd_dir in [spec_dir, root / "architecture", root / project.context_dir]:
        if amd_dir.is_dir():
            for amd in sorted(amd_dir.rglob("*.amd")):
                components.extend(parse_amd_file(amd))

    return OssatureProjectFull(
        project=project,
        output=output,
        build=build,
        test=test,
        llm=llm,
        specs=specs,
        components=components,
        root=root,
    )
