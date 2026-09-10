"""Small, real Parquet catalog fixtures for data-contract tests."""

from pathlib import Path
import sys

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from a_share_factor_research.config import ResolvedPaths  # noqa: E402


@pytest.fixture
def paths(tmp_path):
    """Write the fixed private-catalog layout with date-specific membership."""
    derived = tmp_path / "derived"
    (derived / "universe").mkdir(parents=True)
    (derived / "benchmark").mkdir()
    (derived / "tradability").mkdir()

    dates = pd.bdate_range("2024-01-02", periods=8)
    daily = pd.DataFrame(
        {
            "trade_date": list(dates) * 2,
            "security_id": ["000001.SZ"] * len(dates) + ["000002.SZ"] * len(dates),
            "adjusted_open": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0]
            + [20.0] * len(dates),
            "adjusted_close": [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5]
            + [20.5] * len(dates),
        }
    )
    daily.to_parquet(derived / "daily_panel.parquet", index=False)

    membership = pd.DataFrame(
        {
            "trade_date": list(dates) + [date for date in dates if date != pd.Timestamp("2024-01-03")],
            "security_id": ["000001.SZ"] * len(dates) + ["000002.SZ"] * (len(dates) - 1),
            "is_member": True,
        }
    )
    membership.to_parquet(derived / "universe" / "pit_csi300.parquet", index=False)

    pd.DataFrame(
        {
            "trade_date": dates,
            "adjusted_open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
        }
    ).to_parquet(derived / "benchmark" / "csi300_open.parquet", index=False)
    pd.DataFrame(
        {
            "trade_date": list(dates) * 2,
            "security_id": ["000001.SZ"] * len(dates) + ["000002.SZ"] * len(dates),
            "tradable_next_open": [True] * len(dates) + [False] * len(dates),
        }
    ).to_parquet(derived / "tradability" / "open_eligibility.parquet", index=False)

    return ResolvedPaths(
        data_root=tmp_path,
        daily_panel=derived / "daily_panel.parquet",
        pit_csi300=derived / "universe" / "pit_csi300.parquet",
        csi300_open=derived / "benchmark" / "csi300_open.parquet",
        open_eligibility=derived / "tradability" / "open_eligibility.parquet",
    )


@pytest.fixture
def synthetic_panel(paths):
    """Load the catalog fixture through the public PIT panel boundary."""
    from a_share_factor_research.data import load_research_panel

    return load_research_panel(paths, "2024-01-02", "2024-01-11")


@pytest.fixture
def synthetic_benchmark(paths):
    """Expose the same real benchmark catalog used by the panel fixture."""
    return pd.read_parquet(paths.csi300_open)
