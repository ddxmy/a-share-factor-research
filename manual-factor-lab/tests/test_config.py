"""Contracts for the single-factor research runtime configuration."""

from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from a_share_factor_research.config import load_profile, resolve_data_root  # noqa: E402


def test_daily_baseline_is_frozen():
    """Rejects an accidental change to baseline timing or horizons."""
    profile = load_profile(PROJECT_ROOT / "config" / "daily_baseline.yaml")

    assert (profile.signal_price, profile.execution_price) == ("close", "next_open")
    assert profile.signal_frequency_days == 1
    assert profile.horizons == (1, 5, 20)


def test_missing_data_root_is_actionable(monkeypatch):
    """Makes an unset private-data location clear to the research operator."""
    monkeypatch.delenv("A_SHARE_DATA_ROOT", raising=False)

    with pytest.raises(RuntimeError, match="A_SHARE_DATA_ROOT"):
        resolve_data_root()


def test_data_root_resolves_only_the_fixed_catalog_children(tmp_path):
    """Prevents callers from treating arbitrary locations as catalog inputs."""
    paths = resolve_data_root({"A_SHARE_DATA_ROOT": str(tmp_path)})

    assert paths.data_root == tmp_path
    assert paths.daily_panel == tmp_path / "derived" / "daily_panel.parquet"
    assert paths.pit_csi300 == tmp_path / "derived" / "universe" / "pit_csi300.parquet"
    assert paths.csi300_open == tmp_path / "derived" / "benchmark" / "csi300_open.parquet"
    assert paths.open_eligibility == tmp_path / "derived" / "tradability" / "open_eligibility.parquet"


def test_profile_rejects_invalid_signal_price(tmp_path):
    """Prevents signals calculated before the close from entering the baseline."""
    invalid_profile = _write_profile(tmp_path, signal_price="open")

    with pytest.raises(ValueError, match="signal_price"):
        load_profile(invalid_profile)


def test_profile_rejects_invalid_execution_price(tmp_path):
    """Prevents execution timing from drifting from the next-open contract."""
    invalid_profile = _write_profile(tmp_path, execution_price="close")

    with pytest.raises(ValueError, match="execution_price"):
        load_profile(invalid_profile)


def test_profile_rejects_horizons_without_one_or_increasing_order(tmp_path):
    """Prevents incompatible forward-label horizons from reaching evaluation."""
    invalid_profile = _write_profile(tmp_path, holding_period_days="[5, 1]", horizons="[5, 1]")

    with pytest.raises(ValueError, match="horizons"):
        load_profile(invalid_profile)


def test_profile_rejects_holding_periods_that_do_not_match_ic_horizons(tmp_path):
    """Prevents reporting an IC horizon without its matched NAV profile."""
    invalid_profile = _write_profile(tmp_path, holding_period_days="[1]", horizons="[1, 5, 20]")

    with pytest.raises(ValueError, match="holding_period_days"):
        load_profile(invalid_profile)


def _write_profile(
    tmp_path, *, signal_price="close", execution_price="next_open", holding_period_days="[1, 5, 20]", horizons="[1, 5, 20]"
):
    profile_path = tmp_path / "invalid.yaml"
    profile_path.write_text(
        "\n".join(
            [
                "universe: pit_csi300",
                f"signal_price: {signal_price}",
                f"execution_price: {execution_price}",
                "signal_frequency_days: 1",
                f"holding_period_days: {holding_period_days}",
                f"horizons: {horizons}",
                "ic_metric: spearman_rank_ic",
                "top_k: 30",
                "quintiles: 5",
                "one_way_cost_bps: 10",
                "test_years: [2021, 2022, 2023, 2024, 2025]",
            ]
        )
    )
    return profile_path
