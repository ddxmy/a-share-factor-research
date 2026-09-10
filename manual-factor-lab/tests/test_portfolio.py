"""Behavioral contracts for matched-frequency portfolio simulations."""

from pathlib import Path
import sys

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from a_share_factor_research.portfolio import net_return, simulate_portfolios  # noqa: E402


def make_portfolio_panel(scores, labels_5d):
    return pd.DataFrame(
        {
            "signal_date": pd.Timestamp("2024-01-02"),
            "security_id": [f"S{index}" for index in range(1, len(scores) + 1)],
            "directed_score": scores,
            "label_excess_o2o_5d": labels_5d,
            "tradable_next_open": True,
        }
    )


def test_top_k_uses_horizon_matched_o2o_label():
    """Catches using a daily or otherwise mismatched label in a 5D profile."""
    panel = make_portfolio_panel(scores=[3, 2, 1], labels_5d=[0.10, 0.02, -0.03])

    result = simulate_portfolios(
        panel, horizon_days=5, top_k=1, quintiles=3, one_way_cost_bps=0
    )

    assert result.top_k.loc[0, "gross_return"] == pytest.approx(0.10)


def test_one_way_cost_is_turnover_times_bps():
    """Catches halving or doubling the explicitly one-way transaction cost."""
    assert net_return(0.02, turnover=1.0, one_way_cost_bps=10) == pytest.approx(0.019)


def test_strict_tradable_mask_precedes_equal_weight_ranking():
    """Catches an untradable high score entering Top-K or the top quantile."""
    panel = pd.DataFrame(
        {
            "signal_date": pd.Timestamp("2024-01-02"),
            "security_id": ["A", "B", "C", "D", "E"],
            "directed_score": [5.0, 4.0, 3.0, 2.0, 1.0],
            "label_excess_o2o_1d": [0.50, 0.04, 0.03, 0.02, 0.01],
            "tradable_next_open": [False, True, True, True, True],
        }
    )

    result = simulate_portfolios(
        panel, horizon_days=1, top_k=1, quintiles=2, one_way_cost_bps=0
    )

    assert result.top_k.loc[0, "gross_return"] == pytest.approx(0.04)
    assert result.top_k.loc[0, "n_names"] == 1
    assert result.quintiles["portfolio"].tolist() == ["Q1", "Q2"]
    assert result.quintiles["gross_return"].tolist() == pytest.approx([0.015, 0.035])
    assert result.quintiles["n_names"].tolist() == [2, 2]


def test_top_k_turnover_and_cost_include_initial_entry_and_full_replacement():
    """Catches computing turnover from returns or omitting names that leave the book."""
    panel = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(
                ["2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"]
            ),
            "security_id": ["A", "B", "A", "B"],
            "directed_score": [2.0, 1.0, 1.0, 2.0],
            "label_excess_o2o_1d": [0.02, 0.00, 0.00, 0.02],
            "tradable_next_open": True,
        }
    )

    result = simulate_portfolios(
        panel, horizon_days=1, top_k=1, quintiles=2, one_way_cost_bps=10
    )

    assert result.top_k["turnover"].tolist() == pytest.approx([0.5, 1.0])
    assert result.top_k["cost"].tolist() == pytest.approx([0.0005, 0.001])
    assert result.top_k["net_return"].tolist() == pytest.approx([0.0195, 0.019])
    top_k_summary = result.summary.loc[
        (result.summary["portfolio"] == "top_1")
        & (result.summary["return_type"] == "gross")
    ].iloc[0]
    assert top_k_summary["mean_turnover"] == pytest.approx(0.75)


def test_top_minus_bottom_is_a_separate_diagnostic_portfolio():
    """Catches replacing the long-only result with a long-short spread."""
    panel = pd.DataFrame(
        {
            "signal_date": pd.Timestamp("2024-01-02"),
            "security_id": ["A", "B", "C", "D"],
            "directed_score": [4.0, 3.0, 2.0, 1.0],
            "label_excess_o2o_1d": [0.04, 0.02, 0.00, -0.02],
            "tradable_next_open": True,
        }
    )

    result = simulate_portfolios(
        panel, horizon_days=1, top_k=1, quintiles=2, one_way_cost_bps=10
    )

    assert result.top_k.loc[0, "portfolio"] == "top_1"
    assert result.top_k.loc[0, "gross_return"] == pytest.approx(0.04)
    assert result.long_short.loc[0, "portfolio"] == "top_bottom"
    assert result.long_short.loc[0, "gross_return"] == pytest.approx(0.04)
    assert result.long_short.loc[0, "turnover"] == pytest.approx(1.0)
    assert result.long_short.loc[0, "net_return"] == pytest.approx(0.039)


def test_profiles_use_independent_labels_and_rebalance_sequences():
    """Catches building 5D/20D results by subsampling a computed 1D NAV."""
    dates = pd.bdate_range("2024-01-02", periods=21)
    panel = pd.DataFrame(
        [
            {
                "signal_date": signal_date,
                "security_id": security_id,
                "directed_score": score,
                "label_excess_o2o_1d": 0.01,
                "label_excess_o2o_5d": 0.05,
                "label_excess_o2o_20d": 0.20,
                "tradable_next_open": True,
            }
            for signal_date in dates
            for security_id, score in (("A", 3.0), ("B", 2.0), ("C", 1.0))
        ]
    )

    daily = simulate_portfolios(
        panel, horizon_days=1, top_k=1, quintiles=3, one_way_cost_bps=0
    )
    weekly = simulate_portfolios(
        panel, horizon_days=5, top_k=1, quintiles=3, one_way_cost_bps=0
    )
    monthly = simulate_portfolios(
        panel, horizon_days=20, top_k=1, quintiles=3, one_way_cost_bps=0
    )

    assert daily.top_k["signal_date"].tolist() == dates.tolist()
    assert weekly.top_k["signal_date"].tolist() == dates[[0, 5, 10, 15, 20]].tolist()
    assert monthly.top_k["signal_date"].tolist() == dates[[0, 20]].tolist()
    assert daily.top_k["gross_return"].tolist() == pytest.approx([0.01] * 21)
    assert weekly.top_k["gross_return"].tolist() == pytest.approx([0.05] * 5)
    assert monthly.top_k["gross_return"].tolist() == pytest.approx([0.20] * 2)
    assert (daily.periods_per_year, weekly.periods_per_year, monthly.periods_per_year) == (
        252,
        52,
        12,
    )


def test_nav_and_summary_statistics_use_the_profile_periodicity():
    """Catches additive NAV, wrong annualization, or drawdown without the initial unit NAV."""
    dates = pd.bdate_range("2024-01-02", periods=6)
    top_returns = [-0.10, 0.80, 0.80, 0.80, 0.80, 0.10]
    panel = pd.DataFrame(
        [
            {
                "signal_date": signal_date,
                "security_id": security_id,
                "directed_score": score,
                "label_excess_o2o_5d": top_return if security_id == "A" else 0.0,
                "tradable_next_open": True,
            }
            for signal_date, top_return in zip(dates, top_returns)
            for security_id, score in (("A", 2.0), ("B", 1.0))
        ]
    )

    result = simulate_portfolios(
        panel, horizon_days=5, top_k=1, quintiles=2, one_way_cost_bps=0
    )

    assert result.top_k["gross_nav"].tolist() == pytest.approx([0.90, 0.99])
    assert result.top_k["net_nav"].tolist() == pytest.approx([0.90, 0.99])
    gross_summary = result.summary.loc[
        (result.summary.portfolio == "top_1")
        & (result.summary.return_type == "gross")
    ].iloc[0]
    assert gross_summary.periods_per_year == 52
    assert gross_summary.annualized_return == pytest.approx(0.99**26 - 1)
    assert gross_summary.volatility == pytest.approx(0.1 * 2**0.5 * 52**0.5)
    assert gross_summary.sharpe == pytest.approx(0.0)
    assert gross_summary.max_drawdown == pytest.approx(-0.10)


def test_future_label_availability_never_changes_selected_holdings():
    """Catches reranking with hindsight after a selected name lacks its future label."""
    panel = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(
                ["2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"]
            ),
            "security_id": ["A", "B", "A", "B"],
            "directed_score": [2.0, 1.0, 2.0, 1.0],
            "label_excess_o2o_1d": [None, 0.02, 0.03, 0.01],
            "tradable_next_open": True,
        }
    )

    result = simulate_portfolios(
        panel, horizon_days=1, top_k=1, quintiles=2, one_way_cost_bps=0
    )

    assert result.top_k["signal_date"].tolist() == pd.to_datetime(
        ["2024-01-02", "2024-01-03"]
    ).tolist()
    assert result.top_k["n_names"].tolist() == [1, 1]
    assert result.top_k["is_evaluable"].tolist() == [False, True]
    assert pd.isna(result.top_k.loc[0, "gross_return"])
    assert result.top_k.loc[1, "gross_return"] == pytest.approx(0.03)
    assert result.top_k["turnover"].tolist() == pytest.approx([0.5, 0.0])
    assert result.top_k["gross_nav"].isna().all()


def test_return_and_nav_are_recognized_on_the_label_end_date():
    """Catches dating a realized O2O result at the earlier signal date."""
    panel = pd.DataFrame(
        {
            "signal_date": pd.Timestamp("2024-01-02"),
            "entry_date": pd.Timestamp("2024-01-03"),
            "label_end_date_5d": pd.Timestamp("2024-01-10"),
            "security_id": ["A", "B", "C"],
            "directed_score": [3.0, 2.0, 1.0],
            "label_excess_o2o_5d": [0.10, 0.02, -0.03],
            "tradable_next_open": True,
        }
    )

    result = simulate_portfolios(
        panel, horizon_days=5, top_k=1, quintiles=3, one_way_cost_bps=0
    )

    row = result.top_k.iloc[0]
    assert row.signal_date == pd.Timestamp("2024-01-02")
    assert row.entry_date == pd.Timestamp("2024-01-03")
    assert row.label_end_date_5d == pd.Timestamp("2024-01-10")
    assert row.nav_date == pd.Timestamp("2024-01-10")


def test_invalid_middle_week_remains_in_schedule_and_halts_nav():
    """Catches compressing a 5D calendar and annualizing only surviving weeks."""
    dates = pd.bdate_range("2024-01-02", periods=11)
    records = []
    for date_index, signal_date in enumerate(dates):
        for security_id, score in (("A", 2.0), ("B", 1.0)):
            records.append(
                {
                    "signal_date": signal_date,
                    "entry_date": signal_date + pd.offsets.BDay(1),
                    "label_end_date_5d": signal_date + pd.offsets.BDay(6),
                    "security_id": security_id,
                    "directed_score": None if date_index == 5 else score,
                    "label_excess_o2o_5d": 0.05,
                    "tradable_next_open": True,
                }
            )

    result = simulate_portfolios(
        pd.DataFrame(records),
        horizon_days=5,
        top_k=1,
        quintiles=2,
        one_way_cost_bps=0,
    )

    assert result.top_k["signal_date"].tolist() == dates[[0, 5, 10]].tolist()
    assert result.top_k["is_evaluable"].tolist() == [True, False, True]
    assert result.top_k["gross_nav"].tolist()[:1] == pytest.approx([1.05])
    assert result.top_k["gross_nav"].iloc[1:].isna().all()
    gross_summary = result.summary.loc[
        (result.summary.portfolio == "top_1")
        & (result.summary.return_type == "gross")
    ].iloc[0]
    assert gross_summary.n_periods == 3
    assert gross_summary.n_evaluable_periods == 2
    assert pd.isna(gross_summary.annualized_return)


def test_diagnostic_portfolio_is_tagged_in_rows_and_summary():
    """Catches downstream consumers treating a long-short diagnostic as executable."""
    panel = pd.DataFrame(
        {
            "signal_date": pd.Timestamp("2024-01-02"),
            "security_id": ["A", "B", "C", "D"],
            "directed_score": [4.0, 3.0, 2.0, 1.0],
            "label_excess_o2o_1d": [0.04, 0.02, 0.00, -0.02],
            "tradable_next_open": True,
        }
    )

    result = simulate_portfolios(
        panel, horizon_days=1, top_k=1, quintiles=2, one_way_cost_bps=0
    )

    assert result.top_k[["portfolio_kind", "is_diagnostic"]].iloc[0].tolist() == [
        "top_k_long",
        False,
    ]
    assert result.long_short[["portfolio_kind", "is_diagnostic"]].iloc[0].tolist() == [
        "diagnostic_long_short",
        True,
    ]
    diagnostic_summary = result.summary.loc[
        result.summary.portfolio.eq("top_bottom")
    ]
    assert diagnostic_summary["portfolio_kind"].eq("diagnostic_long_short").all()
    assert diagnostic_summary["is_diagnostic"].eq(True).all()


@pytest.mark.parametrize("horizon_days", [0, 2, 21])
def test_only_daily_weekly_and_monthly_profiles_are_accepted(horizon_days):
    """Catches silently applying an undefined rebalance cadence or annualizer."""
    panel = make_portfolio_panel(scores=[3, 2, 1], labels_5d=[0.10, 0.02, -0.03])

    with pytest.raises(ValueError, match="horizon_days.*1, 5, or 20"):
        simulate_portfolios(
            panel,
            horizon_days=horizon_days,
            top_k=1,
            quintiles=3,
            one_way_cost_bps=0,
        )
