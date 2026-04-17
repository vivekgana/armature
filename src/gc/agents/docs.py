"""GC Agent: Documentation staleness detection.

Scans documentation files for references to files, classes, and paths
that no longer exist on disk.
"""

from __future__ import annotations

import re
from pathlib import Path

from armature._internal.types import GCFinding, Severity


def scan_docs(root: Path, watched_files: list[str]) -> list[GCFinding]:
    """Scan watched documentation files for stale references."""
    findings: list[GCFinding] = []

    # Patterns for file references in markdown
    path_patterns = [
        re.compile(r"`((?:src|tests|scripts|docs|e2e)/[^\s`]+)`"),  # backtick paths
        re.compile(r'"((?:src|tests|scripts|docs|e2e)/[^\s"]+)"'),  # quoted paths
        re.compile(r"\[.*?\]\(((?:src|tests|scripts|docs|e2e)/[^\s)]+)\)"),  # markdown links
    ]

    for pattern in watched_files:
        for doc_file in root.glob(pattern):
            try:
                content = doc_file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            for path_re in path_patterns:
                for match in path_re.finditer(content):
                    ref_path = match.group(1)
                    # Strip trailing punctuation
                    ref_path = ref_path.rstrip(".,;:)")
                    full_path = root / ref_path

                    if not full_path.exists():
                        findings.append(GCFinding(
                            agent="docs",
                            category="stale_reference",
                            file=str(doc_file.relative_to(root)),
                            message=f"References non-existent path: {ref_path}",
                            severity=Severity.WARNING,
                        ))

    return findings
