"""Behavioral contracts for PIT universe loading and O2O label alignment."""

from pathlib import Path
import sys

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from a_share_factor_research.data import attach_forward_labels, load_research_panel  # noqa: E402


def _row(frame, security_id, trade_date):
    return frame.loc[
        (frame["security_id"] == security_id)
        & (frame["trade_date"] == pd.Timestamp(trade_date))
    ].iloc[0]


def test_close_t_maps_to_next_open_to_following_open(synthetic_panel, synthetic_benchmark):
    """Catches an accidental same-day or close-price forward-return label."""
    labelled = attach_forward_labels(synthetic_panel, synthetic_benchmark, horizons=(1,))

    row = _row(labelled, "000001.SZ", "2024-01-02")
    assert row.entry_date == pd.Timestamp("2024-01-03")
    assert row.label_excess_o2o_1d == pytest.approx((12 / 11 - 1) - (102 / 101 - 1))
    assert row.label_end_date_1d == pd.Timestamp("2024-01-04")


def test_horizon_uses_h_plus_one_observable_open(synthetic_panel, synthetic_benchmark):
    """Catches a five-day label ending one open too early."""
    labelled = attach_forward_labels(synthetic_panel, synthetic_benchmark, horizons=(5,))

    row = _row(labelled, "000001.SZ", "2024-01-02")
    assert row.label_excess_o2o_5d == pytest.approx((16 / 11 - 1) - (106 / 101 - 1))
    assert row.label_end_date_5d == pd.Timestamp("2024-01-10")


def test_pit_membership_applies_on_the_exact_date(paths):
    """Catches joins that use only security ID and leak later/earlier membership."""
    panel = load_research_panel(paths, "2024-01-02", "2024-01-05")

    assert not (
        (panel.security_id == "000002.SZ")
        & (panel.trade_date == pd.Timestamp("2024-01-03"))
    ).any()


def test_basic_and_tradable_eligibility_remain_distinct(paths):
    """Catches a tradability filter being incorrectly applied to basic IC rows."""
    panel = load_research_panel(paths, "2024-01-02", "2024-01-05")

    row = _row(panel, "000002.SZ", "2024-01-02")
    assert bool(row.basic_eligible) is True
    assert bool(row.tradable_next_open) is False


def test_dedicated_tradability_catalog_overrides_daily_convenience_column(paths):
    """Catches merge suffixes when a daily source also stores a proxy flag."""
    daily = pd.read_parquet(paths.daily_panel)
    daily["tradable_next_open"] = False
    daily.to_parquet(paths.daily_panel, index=False)

    panel = load_research_panel(paths, "2024-01-02", "2024-01-05")

    assert bool(_row(panel, "000001.SZ", "2024-01-02").tradable_next_open) is True


def test_missing_open_is_not_forward_filled(synthetic_panel, synthetic_benchmark):
    """Catches fabricating an O2O label when a needed market open is missing."""
    benchmark_missing_entry = synthetic_benchmark.loc[
        synthetic_benchmark.trade_date != pd.Timestamp("2024-01-03")
    ]
    labelled = attach_forward_labels(synthetic_panel, benchmark_missing_entry, horizons=(1,))

    row = _row(labelled, "000001.SZ", "2024-01-02")
    assert pd.isna(row.label_excess_o2o_1d)
    assert bool(row.basic_eligible) is False


def test_benchmark_horizon_requires_the_same_observable_endpoints(synthetic_panel, synthetic_benchmark):
    """Catches using benchmark endpoints that skip a missing session differently."""
    benchmark_missing_middle = synthetic_benchmark.loc[
        synthetic_benchmark.trade_date != pd.Timestamp("2024-01-04")
    ]
    labelled = attach_forward_labels(synthetic_panel, benchmark_missing_middle, horizons=(2,))

    row = _row(labelled, "000001.SZ", "2024-01-02")
    assert pd.isna(row.label_excess_o2o_2d)


def test_duplicate_daily_keys_are_rejected(paths):
    """Catches ambiguous daily inputs before they can corrupt a panel join."""
    daily = pd.read_parquet(paths.daily_panel)
    pd.concat([daily, daily.iloc[[0]]], ignore_index=True).to_parquet(paths.daily_panel, index=False)

    with pytest.raises(ValueError, match="unique.*trade_date.*security_id"):
        load_research_panel(paths, "2024-01-02", "2024-01-05")
