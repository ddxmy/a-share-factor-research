"""Formula-level regression tests for the third user-authored factor batch."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from factor_modules import close_pos5, pv_corr20


def _value(frame: pd.DataFrame, security_id: str, date: pd.Timestamp) -> float:
    return float(
        frame.loc[
            (frame["security_id"] == security_id) & (frame["trade_date"] == date),
            "raw_value",
        ].iloc[0]
    )


def test_close_pos5_is_per_security_and_excludes_zero_price_ranges():
    dates = pd.bdate_range("2024-01-02", periods=6)
    panel = pd.DataFrame(
        {
            "trade_date": list(dates) * 2,
            "security_id": ["A"] * 6 + ["B"] * 6,
            "adjusted_high": [11, 12, 13, 14, 15, 16] + [10] * 6,
            "adjusted_low": [9, 9, 10, 11, 12, 13] + [10] * 6,
            "adjusted_close": [10, 11, 12, 13, 14, 15] + [10] * 6,
        }
    ).sample(frac=1.0, random_state=31)

    result = close_pos5.compute(panel)

    assert result.loc[result.security_id == "A", "raw_value"].iloc[:4].isna().all()
    assert _value(result, "A", dates[4]) == pytest.approx((14 - 9) / (15 - 9))
    assert result.loc[result.security_id == "B", "raw_value"].isna().all()


def test_pv_corr20_requires_twenty_valid_pairs_and_stays_within_security():
    dates = pd.bdate_range("2024-01-02", periods=22)
    returns = np.linspace(-0.02, 0.02, 21)
    volume_a = np.exp(np.r_[0.0, returns * 100 + 10])
    close_a = np.r_[100.0, 100.0 * np.cumprod(1.0 + returns)]
    close_b = np.r_[200.0, 200.0 * np.cumprod(1.0 - returns)]
    panel = pd.DataFrame(
        {
            "trade_date": list(dates) * 2,
            "security_id": ["A"] * 22 + ["B"] * 22,
            "adjusted_close": np.r_[close_a, close_b],
            "volume": np.r_[volume_a, [0.0] * 22],
        }
    )
    panel = panel.sample(frac=1.0, random_state=37).reset_index(drop=True)

    result = pv_corr20.compute(panel)

    a_values = result.loc[result.security_id == "A", "raw_value"].reset_index(drop=True)
    assert a_values.iloc[:20].isna().all()
    assert _value(result, "A", dates[-1]) > 0.99
    assert result.loc[result.security_id == "B", "raw_value"].isna().all()
    assert not np.isinf(result.raw_value.to_numpy(dtype=float)).any()
