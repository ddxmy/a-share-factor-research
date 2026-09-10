"""Behavioral contracts for registered factor processing."""

from pathlib import Path
import sys

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import factors  # noqa: E402
import factor_modules  # noqa: E402
from a_share_factor_research.processing import prepare_factor_cross_sections  # noqa: E402
from a_share_factor_research.registry import FactorDefinition, load_factor_definition  # noqa: E402


@pytest.fixture
def positive_definition():
    return FactorDefinition(
        factor_id="MOM20",
        formula_definition="test formula",
        required_daily_fields=("adjusted_close",),
        signal_availability="after close",
        economic_hypothesis="test hypothesis",
        pre_registered_direction="positive",
        status="planned",
        compute=factors.compute_mom20,
    )


@pytest.fixture
def negative_definition():
    return FactorDefinition(
        factor_id="REV5",
        formula_definition="test formula",
        required_daily_fields=("adjusted_close",),
        signal_availability="after close",
        economic_hypothesis="test hypothesis",
        pre_registered_direction="negative",
        status="planned",
        compute=factors.compute_rev5,
    )


@pytest.fixture
def raw_two_names():
    return pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")] * 2,
            "security_id": ["A", "B"],
            "raw_value": [1.0, 2.0],
        }
    )


def test_raw_factor_is_preserved_before_processing(positive_definition):
    """Catches replacing the researcher-calculated raw factor with processed values."""
    raw = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")] * 3,
            "security_id": ["A", "B", "C"],
            "raw_value": [1.0, 2.0, 100.0],
        }
    )

    prepared = prepare_factor_cross_sections(raw, positive_definition)

    assert prepared.raw_value.tolist() == [1.0, 2.0, 100.0]
    assert prepared.zscore_value.notna().all()


def test_negative_direction_only_changes_directed_score(raw_two_names, negative_definition):
    """Catches applying a negative direction before storing the neutral z-score."""
    prepared = prepare_factor_cross_sections(raw_two_names, negative_definition)

    assert prepared.zscore_value.tolist() == [-1.0, 1.0]
    assert prepared.directed_score.tolist() == [1.0, -1.0]


def test_processing_imputes_before_mad_clipping(positive_definition):
    """Catches clipping before a missing raw value receives its cross-sectional median."""
    raw = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")] * 4,
            "security_id": ["A", "B", "C", "D"],
            "raw_value": [1.0, None, 2.0, 100.0],
        }
    )

    prepared = prepare_factor_cross_sections(raw, positive_definition)

    assert prepared.raw_value.isna().tolist() == [False, True, False, False]
    assert prepared.winsorized_value.tolist() == pytest.approx([1.0, 2.0, 2.0, 5.7065])


def test_duplicate_index_labels_do_not_combine_cross_sections(positive_definition):
    """Catches date groups being assigned through duplicate caller index labels."""
    raw = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")],
            "security_id": ["A", "B"],
            "raw_value": [1.0, 2.0],
        },
        index=["duplicate", "duplicate"],
    )

    prepared = prepare_factor_cross_sections(raw, positive_definition)

    assert prepared.index.tolist() == ["duplicate", "duplicate"]
    assert prepared.raw_value.tolist() == [1.0, 2.0]
    assert prepared.zscore_value.isna().all()
    assert prepared.directed_score.isna().all()


def test_registry_definition_resolves_the_registered_factor_callable():
    """Catches a registry entry that does not bind to its researcher-owned function."""
    definition = load_factor_definition("REV5")

    assert definition.factor_id == "REV5"
    assert definition.pre_registered_direction == "negative"
    assert definition.compute is factor_modules.rev5.compute
