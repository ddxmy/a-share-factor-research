"""Behavioral contracts for multi-horizon IC evidence and frozen decisions."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from a_share_factor_research.evaluation import (  # noqa: E402
    classify_factor,
    evaluate_ic,
    hac_lag_for_horizon,
)
from a_share_factor_research.registry import FactorDefinition  # noqa: E402


def _definition(direction="positive"):
    return FactorDefinition(
        factor_id="TEST",
        formula_definition="test formula",
        required_daily_fields=("adjusted_close",),
        signal_availability="after close",
        economic_hypothesis="test hypothesis",
        pre_registered_direction=direction,
        status="planned",
        compute=lambda panel: panel,
    )


def _panel_for_dates(dates, labels=(1.0, 2.0, 3.0), tradable=(True, True, True)):
    records = []
    for signal_date in dates:
        for name, (score, label, is_tradable) in enumerate(
            zip((1.0, 2.0, 3.0), labels, tradable), start=1
        ):
            records.append(
                {
                    "signal_date": signal_date,
                    "security_id": f"S{name}",
                    "directed_score": score,
                    "label_excess_o2o_1d": label,
                    "label_excess_o2o_5d": label,
                    "label_excess_o2o_20d": label,
                    "basic_eligible": True,
                    "tradable_next_open": is_tradable,
                }
            )
    return pd.DataFrame(records)


def _five_year_dates():
    return pd.DatetimeIndex(
        np.concatenate([pd.bdate_range(f"{year}-01-02", periods=120) for year in range(2021, 2026)])
    )


def test_rank_and_pearson_ic_are_one_for_identical_order():
    """Catches either IC metric using the wrong score, label, or cross-section."""
    panel = pd.DataFrame(
        {
            "signal_date": [pd.Timestamp("2024-01-02")] * 3,
            "directed_score": [1.0, 2.0, 3.0],
            "label_excess_o2o_1d": [0.01, 0.02, 0.03],
            "basic_eligible": [True, True, True],
        }
    )

    result = evaluate_ic(panel, horizons=(1,), eligibility="basic")

    assert result.daily.loc[0, "rank_ic"] == pytest.approx(1.0)
    assert result.daily.loc[0, "pearson_ic"] == pytest.approx(1.0)
    assert result.daily.loc[0, "n_names"] == 3


def test_hac_lag_matches_overlapping_horizon():
    """Catches treating overlapping 5D/20D labels as independent daily observations."""
    assert [hac_lag_for_horizon(horizon) for horizon in (1, 5, 20)] == [0, 4, 19]


def test_ic_requires_three_finite_nonconstant_eligible_pairs():
    """Catches reporting a correlation for an unidentified cross-section."""
    panel = pd.DataFrame(
        {
            "signal_date": [pd.Timestamp("2024-01-02")] * 4,
            "directed_score": [1.0, 1.0, 1.0, 4.0],
            "label_excess_o2o_1d": [1.0, 2.0, 3.0, 4.0],
            "basic_eligible": [True, True, True, False],
        }
    )

    result = evaluate_ic(panel, horizons=(1,), eligibility="basic")

    assert result.daily.loc[0, "n_names"] == 3
    assert pd.isna(result.daily.loc[0, "pearson_ic"])
    assert pd.isna(result.daily.loc[0, "rank_ic"])


def test_duplicate_index_labels_do_not_mix_daily_cross_sections():
    """Catches label-based selection combining rows from different signal dates."""
    panel = _panel_for_dates(pd.to_datetime(["2024-01-02", "2024-01-03"]))
    panel.index = ["duplicate"] * len(panel)

    result = evaluate_ic(panel, horizons=(1,), eligibility="basic")

    assert result.daily["signal_date"].tolist() == pd.to_datetime(
        ["2024-01-02", "2024-01-03"]
    ).tolist()
    assert result.daily["n_names"].tolist() == [3, 3]
    assert result.daily["rank_ic"].tolist() == pytest.approx([1.0, 1.0])


def test_basic_and_tradable_ic_use_separate_masks():
    """Catches next-open tradability leaking into the basic research IC."""
    panel = pd.DataFrame(
        {
            "signal_date": [pd.Timestamp("2024-01-02")] * 4,
            "directed_score": [1.0, 2.0, 3.0, 4.0],
            "label_excess_o2o_1d": [1.0, 2.0, 3.0, -10.0],
            "basic_eligible": [True] * 4,
            "tradable_next_open": [True, True, True, False],
        }
    )

    result = evaluate_ic(panel, horizons=(1,), eligibility=("basic", "tradable"))
    basic = result.daily.loc[result.daily.eligibility == "basic"].iloc[0]
    tradable = result.daily.loc[result.daily.eligibility == "tradable"].iloc[0]

    assert basic.rank_ic < 0
    assert tradable.rank_ic == pytest.approx(1.0)
    assert (basic.n_names, tradable.n_names) == (4, 3)


def test_summary_yearly_and_non_overlapping_evidence_are_reported():
    """Catches missing descriptive or non-overlap robustness evidence."""
    dates = pd.bdate_range("2024-01-02", periods=21)

    result = evaluate_ic(_panel_for_dates(dates), horizons=(1, 5, 20), eligibility="basic")

    one_day = result.summary.loc[result.summary.horizon_days == 1].iloc[0]
    assert one_day.n_observations == 21
    assert one_day.mean_rank_ic == pytest.approx(1.0)
    assert one_day.rank_ic_std == pytest.approx(0.0)
    assert one_day.positive_rank_ic_ratio == pytest.approx(1.0)
    assert one_day.cumulative_rank_ic == pytest.approx(21.0)
    assert one_day.hac_lag == 0
    assert one_day.hac_t_stat == np.inf
    assert one_day.hac_one_sided_p_value == pytest.approx(0.0)
    assert result.yearly.loc[0, "year"] == 2024
    assert result.yearly.loc[0, "mean_rank_ic"] == pytest.approx(1.0)

    five_day_dates = result.non_overlapping.loc[
        result.non_overlapping.horizon_days == 5, "signal_date"
    ].tolist()
    twenty_day_dates = result.non_overlapping.loc[
        result.non_overlapping.horizon_days == 20, "signal_date"
    ].tolist()
    assert five_day_dates == dates[[0, 5, 10, 15, 20]].tolist()
    assert twenty_day_dates == dates[[0, 20]].tolist()


def test_admit_uses_positive_directed_score_for_both_registered_directions():
    """Catches double-inverting a negative factor after processing aligned directed_score."""
    panel = _panel_for_dates(_five_year_dates())
    evaluation = evaluate_ic(panel, horizons=(1,), eligibility=("basic", "tradable"))

    assert classify_factor(evaluation, _definition("positive"), range(2021, 2026)) == "Admit"
    assert classify_factor(evaluation, _definition("negative"), range(2021, 2026)) == "Admit"


def test_rejects_insufficient_coverage_or_opposite_basic_direction():
    """Catches admitting thin evidence or a directed score with the wrong basic sign."""
    thin = evaluate_ic(
        _panel_for_dates(_five_year_dates()[:499]),
        horizons=(1,),
        eligibility=("basic", "tradable"),
    )
    opposite = evaluate_ic(
        _panel_for_dates(_five_year_dates(), labels=(3.0, 2.0, 1.0)),
        horizons=(1,),
        eligibility=("basic", "tradable"),
    )

    assert classify_factor(thin, _definition(), range(2021, 2026)) == "Reject"
    assert classify_factor(opposite, _definition(), range(2021, 2026)) == "Reject"


def test_pre_test_evidence_cannot_supply_locked_year_coverage():
    """Catches pre-test observations leaking into every frozen admission criterion."""
    pre_test_dates = pd.bdate_range("2018-01-02", periods=600)
    locked_dates = _five_year_dates()[:499]
    evaluation = evaluate_ic(
        _panel_for_dates(pre_test_dates.append(locked_dates)),
        horizons=(1,),
        eligibility=("basic", "tradable"),
    )

    assert evaluation.summary.loc[
        evaluation.summary.eligibility == "basic", "n_observations"
    ].iloc[0] == 1099
    assert classify_factor(evaluation, _definition(), range(2021, 2026)) == "Reject"


def test_empty_valid_panel_returns_empty_evidence_and_rejects():
    """Catches an empty data window crashing annual summaries or classification."""
    panel = pd.DataFrame(
        {
            "signal_date": pd.Series(dtype="datetime64[ns]"),
            "directed_score": pd.Series(dtype=float),
            "label_excess_o2o_1d": pd.Series(dtype=float),
            "basic_eligible": pd.Series(dtype=bool),
            "tradable_next_open": pd.Series(dtype=bool),
        }
    )

    evaluation = evaluate_ic(panel, horizons=(1,), eligibility=("basic", "tradable"))

    assert evaluation.daily.empty
    assert evaluation.summary.empty
    assert evaluation.yearly.empty
    assert evaluation.non_overlapping.empty
    assert evaluation.non_overlapping_summary.empty
    assert classify_factor(evaluation, _definition(), range(2021, 2026)) == "Reject"


def test_expected_basic_direction_with_wrong_tradable_direction_is_review():
    """Catches admitting a factor whose executable subset has the opposite sign."""
    dates = _five_year_dates()
    panel = _panel_for_dates(dates)
    fourth_names = pd.DataFrame(
        {
            "signal_date": dates,
            "security_id": "S4",
            "directed_score": 4.0,
            "label_excess_o2o_1d": 4.0,
            "label_excess_o2o_5d": 4.0,
            "label_excess_o2o_20d": 4.0,
            "basic_eligible": True,
            "tradable_next_open": False,
        }
    )
    panel = pd.concat([panel, fourth_names], ignore_index=True)
    panel.loc[panel.security_id == "S1", "label_excess_o2o_1d"] = 3.0
    panel.loc[panel.security_id == "S2", "label_excess_o2o_1d"] = 2.0
    panel.loc[panel.security_id == "S3", "label_excess_o2o_1d"] = 1.0
    evaluation = evaluate_ic(panel, horizons=(1,), eligibility=("basic", "tradable"))

    basic_mean = evaluation.summary.loc[
        evaluation.summary.eligibility == "basic", "mean_rank_ic"
    ].iloc[0]
    tradable_mean = evaluation.summary.loc[
        evaluation.summary.eligibility == "tradable", "mean_rank_ic"
    ].iloc[0]
    assert basic_mean > 0
    assert tradable_mean < 0
    assert classify_factor(evaluation, _definition(), range(2021, 2026)) == "Review"
