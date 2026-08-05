from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from alpha158_research.modeling import (  # noqa: E402
    choose_candidate,
    neutralize_scores,
    weekly_equal_weights,
    weekly_rank_ic,
)


def test_weekly_equal_weights_give_each_date_equal_total_weight():
    frame = pd.DataFrame(
        {
            "signal_date": ["2020-01-03"] * 2 + ["2020-01-10"] * 4,
            "con_code": list("ABCDEF"),
        }
    )
    weights = weekly_equal_weights(frame)
    totals = pd.Series(weights).groupby(frame["signal_date"]).sum()
    assert np.allclose(totals.iloc[0], totals.iloc[1])
    assert np.isclose(weights.mean(), 1.0)


def test_choose_candidate_uses_icir_then_stronger_regularization_tie_breaker():
    summary = pd.DataFrame(
        {
            "alpha": [1.0, 10.0, 100.0],
            "mean_rank_ic": [0.02, 0.02, 0.01],
            "rank_icir": [0.3, 0.3, 0.9],
        }
    )
    assert choose_candidate(summary)["alpha"] == 10.0


def test_weekly_rank_ic_is_positive_for_matching_order():
    frame = pd.DataFrame(
        {
            "signal_date": ["2020-01-03"] * 3,
            "prediction": [0.1, 0.2, 0.3],
            "target": [0.01, 0.02, 0.03],
        }
    )
    output = weekly_rank_ic(frame, "prediction", "target")
    assert output.loc[0, "rank_ic"] == 1.0


def test_neutralized_scores_are_orthogonal_to_size_and_industry():
    frame = pd.DataFrame(
        {
            "signal_date": ["2020-01-03"] * 6,
            "total_mv_cny": [10, 20, 30, 40, 50, 60],
            "sw2021_l1_name": ["A", "A", "A", "B", "B", "B"],
            "score": [1.0, 2.1, 2.9, 6.0, 7.1, 8.0],
        }
    )
    residual = neutralize_scores(frame, "score")
    assert abs(pd.Series(residual).corr(np.log(frame["total_mv_cny"]))) < 1e-10
    assert pd.Series(residual).groupby(frame["sw2021_l1_name"]).mean().abs().max() < 1e-10
