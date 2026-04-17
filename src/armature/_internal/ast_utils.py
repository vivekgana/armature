"""AST parsing helpers for Python source analysis."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClassInfo:
    """Information about a class definition."""
    name: str
    file: str
    line: int
    bases: list[str]
    methods: list[str]
    attributes: list[str]


@dataclass
class ImportInfo:
    """Information about an import statement."""
    module: str
    file: str
    line: int


def parse_file(file_path: Path) -> ast.Module | None:
    """Parse a Python file into an AST, returning None on failure."""
    try:
        source = file_path.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


def extract_classes(file_path: Path) -> list[ClassInfo]:
    """Extract all class definitions from a Python file."""
    tree = parse_file(file_path)
    if tree is None:
        return []

    classes: list[ClassInfo] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(ast.unparse(base))

        methods = [
            item.name for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        attributes = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attributes.append(item.target.id)

        classes.append(ClassInfo(
            name=node.name,
            file=str(file_path),
            line=node.lineno,
            bases=bases,
            methods=methods,
            attributes=attributes,
        ))

    return classes


def extract_imports(file_path: Path) -> list[ImportInfo]:
    """Extract all import statements from a Python file."""
    tree = parse_file(file_path)
    if tree is None:
        return []

    imports: list[ImportInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportInfo(module=alias.name, file=str(file_path), line=node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(ImportInfo(module=node.module, file=str(file_path), line=node.lineno))

    return imports
