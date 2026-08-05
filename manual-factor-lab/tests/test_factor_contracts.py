"""Contracts for the researcher-owned manual factor laboratory."""

from pathlib import Path
import sys

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import factors  # noqa: E402


def test_all_registered_factors_have_researcher_owned_stubs():
    registry = pd.read_csv(PROJECT_ROOT / "factor_registry.csv")

    assert len(registry) == 10
    for factor_id in registry["factor_id"]:
        function = getattr(factors, f"compute_{factor_id.lower()}")
        with pytest.raises(NotImplementedError, match=factor_id):
            function(pd.DataFrame())
