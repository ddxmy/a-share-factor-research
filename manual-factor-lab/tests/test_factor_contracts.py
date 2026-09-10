"""Contracts for the researcher-owned manual factor laboratory."""

from pathlib import Path
import sys

import pandas as pd
PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import factors  # noqa: E402


def test_all_registered_factors_have_implemented_legacy_bridges():
    registry = pd.read_csv(PROJECT_ROOT / "factor_registry.csv")

    assert len(registry) == 10
    assert registry["status"].eq("implemented").all()
    for factor_id in registry["factor_id"]:
        assert callable(getattr(factors, f"compute_{factor_id.lower()}"))
