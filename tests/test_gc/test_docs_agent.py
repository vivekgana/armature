"""Tests for gc/agents/docs.py -- documentation staleness detection."""

from __future__ import annotations

from pathlib import Path

from armature.gc.agents.docs import scan_docs


class TestScanDocs:
    """Tests for scan_docs() stale reference detection."""

    def test_detects_stale_path_reference(self, tmp_path: Path):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "README.md").write_text(
            "See `src/models/deleted_file.py` for details.\n",
            encoding="utf-8",
        )

        findings = scan_docs(tmp_path, ["docs/*.md"])
        assert len(findings) == 1
        assert "stale_reference" in findings[0].category
        assert "deleted_file" in findings[0].message

    def test_no_findings_for_valid_refs(self, tmp_path: Path):
        src = tmp_path / "src" / "models"
        src.mkdir(parents=True)
        (src / "user.py").write_text("class User: ...\n", encoding="utf-8")

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "README.md").write_text(
            "See `src/models/user.py` for the User model.\n",
            encoding="utf-8",
        )

        findings = scan_docs(tmp_path, ["docs/*.md"])
        assert len(findings) == 0

    def test_detects_markdown_link_stale_ref(self, tmp_path: Path):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text(
            "Check [the config](src/config/missing.py) for setup.\n",
            encoding="utf-8",
        )

        findings = scan_docs(tmp_path, ["docs/*.md"])
        assert len(findings) == 1

    def test_no_files_no_findings(self, tmp_path: Path):
        findings = scan_docs(tmp_path, ["docs/*.md"])
        assert len(findings) == 0
