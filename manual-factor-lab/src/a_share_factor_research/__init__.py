"""Reusable contracts for point-in-time A-share factor research."""

from .config import ResearchProfile, ResolvedPaths, load_profile, resolve_data_root

__all__ = [
    "ResearchProfile",
    "ResolvedPaths",
    "load_profile",
    "resolve_data_root",
]
