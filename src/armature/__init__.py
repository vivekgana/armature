"""Armature -- Harness engineering framework for AI coding agents.

The invisible skeleton that gives shape to what agents produce.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("armature")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = ["__version__"]
