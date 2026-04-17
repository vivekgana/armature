"""Ossature compatibility: convert and compare ossature projects with armature."""

from armature.compat._ossature_model import OssatureProjectFull, load_ossature_project
from armature.compat.compare import ComparisonReport, compare_ossature_project
from armature.compat.ossature import ConversionResult, ConversionWarning, convert_ossature_project

__all__ = [
    "ComparisonReport",
    "ConversionResult",
    "ConversionWarning",
    "OssatureProjectFull",
    "compare_ossature_project",
    "convert_ossature_project",
    "load_ossature_project",
]
