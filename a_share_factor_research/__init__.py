"""Repository-root import bridge for the manual-factor-lab src package."""

from pathlib import Path
import sys


_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "manual-factor-lab" / "src"
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))
__path__ = [str(_SOURCE_ROOT / "a_share_factor_research")]

from .config import ResearchProfile, ResolvedPaths, load_profile, resolve_data_root

__all__ = [
    "ResearchProfile",
    "ResolvedPaths",
    "load_profile",
    "resolve_data_root",
]
