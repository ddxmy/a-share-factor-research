"""Integration contracts for dedicated researcher factor modules."""

import pandas as pd
import pytest

import factor_modules
import factors as legacy_factors
from a_share_factor_research.registry import (
    load_factor_definition,
    resolve_factor_callable,
)


@pytest.mark.parametrize("factor_id", ["REV5", "MOM20", "CLOSE_POS5"])
def test_registry_resolves_the_dedicated_module(factor_id):
    definition = load_factor_definition(factor_id)

    assert definition.compute.__module__ == f"factor_modules.{factor_id.lower()}"


def test_legacy_rev5_bridge_delegates_to_the_dedicated_module(monkeypatch):
    marker = pd.DataFrame({"trade_date": [], "security_id": [], "raw_value": []})
    monkeypatch.setattr(factor_modules.rev5, "compute", lambda panel: marker)

    assert legacy_factors.compute_rev5(pd.DataFrame()) is marker


def test_module_identifier_mismatch_is_rejected(monkeypatch):
    monkeypatch.setattr(factor_modules.rev5, "FACTOR_ID", "MOM20")

    with pytest.raises(ValueError, match="does not match"):
        resolve_factor_callable("REV5")
