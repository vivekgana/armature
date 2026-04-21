"""Tests for _internal/ast_utils.py -- AST parsing helpers."""

from __future__ import annotations

from pathlib import Path

from armature._internal.ast_utils import extract_classes, extract_imports, parse_file


class TestParseFile:
    """Tests for parse_file()."""

    def test_valid_python(self, tmp_path: Path):
        f = tmp_path / "valid.py"
        f.write_text("x = 1\n", encoding="utf-8")
        result = parse_file(f)
        assert result is not None

    def test_syntax_error_returns_none(self, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n", encoding="utf-8")
        result = parse_file(f)
        assert result is None

    def test_nonexistent_returns_none(self, tmp_path: Path):
        result = parse_file(tmp_path / "nonexistent.py")
        assert result is None


class TestExtractClasses:
    """Tests for extract_classes()."""

    def test_extracts_class_info(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text(
            "class MyAgent(BaseAgent):\n"
            "    name = 'my'\n"
            "    def run(self): ...\n"
            "    def reset(self): ...\n",
            encoding="utf-8",
        )
        classes = extract_classes(f)
        assert len(classes) == 1
        assert classes[0].name == "MyAgent"
        assert "BaseAgent" in classes[0].bases
        assert "run" in classes[0].methods
        assert "reset" in classes[0].methods
        assert "name" in classes[0].attributes

    def test_multiple_classes(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text(
            "class A:\n    pass\nclass B(A):\n    pass\n",
            encoding="utf-8",
        )
        classes = extract_classes(f)
        assert len(classes) == 2

    def test_empty_file(self, tmp_path: Path):
        f = tmp_path / "empty.py"
        f.write_text("", encoding="utf-8")
        classes = extract_classes(f)
        assert len(classes) == 0


class TestExtractImports:
    """Tests for extract_imports()."""

    def test_import_statement(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("import os\nimport sys\n", encoding="utf-8")
        imports = extract_imports(f)
        assert len(imports) == 2
        modules = [i.module for i in imports]
        assert "os" in modules
        assert "sys" in modules

    def test_from_import(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("from pathlib import Path\n", encoding="utf-8")
        imports = extract_imports(f)
        assert len(imports) == 1
        assert imports[0].module == "pathlib"

    def test_line_numbers(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("import os\n\nimport sys\n", encoding="utf-8")
        imports = extract_imports(f)
        assert imports[0].line == 1
        assert imports[1].line == 3
