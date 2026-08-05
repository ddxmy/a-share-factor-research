from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from alpha158_research.evaluation import (  # noqa: E402
    newey_west_mean_test,
    rank_ic_summary,
    validate_common_prediction_panel,
    weekly_quintile_returns,
)


def test_common_panel_rejects_label_mismatch():
    ridge = pd.DataFrame(
        {
            "signal_date": ["2021-01-08"],
            "con_code": ["A"],
            "target_excess_return": [0.01],
            "raw_prediction_score": [0.1],
            "neutralized_prediction_score": [0.1],
        }
    )
    lightgbm = ridge.assign(target_excess_return=0.02)
    with pytest.raises(ValueError, match="target labels"):
        validate_common_prediction_panel(ridge, lightgbm)


def test_newey_west_mean_test_matches_constant_mean():
    result = newey_west_mean_test(np.full(5, 0.01), max_lag=1)
    assert result["mean"] == pytest.approx(0.01)
    assert result["weeks"] == 5
    assert np.isfinite(result["hac_standard_error"])


def test_rank_ic_summary_uses_sample_standard_deviation():
    weekly_ic = pd.DataFrame({"rank_ic": [0.0, 0.1, 0.2]})
    result = rank_ic_summary(weekly_ic)
    assert result["weeks"] == 3
    assert result["std_rank_ic"] == pytest.approx(0.1)
    assert result["rank_icir"] == pytest.approx(1.0)


def test_weekly_quintile_returns_make_q5_minus_q1_from_equal_count_groups():
    frame = pd.DataFrame(
        {
            "signal_date": ["2021-01-08"] * 10,
            "score": range(10),
            "target_excess_return": np.arange(10) / 100,
        }
    )
    output = weekly_quintile_returns(frame, "score")
    q1 = output.loc[output["quintile"].eq("Q1"), "mean_excess_return"].item()
    q5 = output.loc[output["quintile"].eq("Q5"), "mean_excess_return"].item()
    spread = output.loc[output["quintile"].eq("Q5-Q1"), "mean_excess_return"].item()
    assert spread == pytest.approx(q5 - q1)
