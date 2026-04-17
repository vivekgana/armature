"""GC Agent: Architecture drift detection.

Runs architectural checks and compares against baseline to detect drift.
"""

from __future__ import annotations

from armature._internal.types import GCFinding


# Architecture GC is handled directly in gc/runner.py via boundary + conformance checks.
# This module exists for future expansion (e.g., trend analysis, PR generation).
