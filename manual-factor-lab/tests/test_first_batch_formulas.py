"""Formula-level regression tests for the first user-authored factor batch."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from factor_modules import mom20, mom60, vol20


def _interleaved_panel(periods: int = 62) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for index, date in enumerate(dates):
        rows.extend(
            [
                {"trade_date": date, "security_id": "A", "adjusted_close": 100.0 + index},
                {"trade_date": date, "security_id": "B", "adjusted_close": 200.0 - 2.0 * index},
            ]
        )
    return pd.DataFrame(rows).sample(frac=1.0, random_state=11).reset_index(drop=True)


def _value(frame: pd.DataFrame, security_id: str, trade_date: pd.Timestamp) -> float:
    return float(
        frame.loc[
            (frame["security_id"] == security_id) & (frame["trade_date"] == trade_date),
            "raw_value",
        ].iloc[0]
    )


def test_momentum_windows_are_per_security_and_leave_initial_history_missing():
    panel = _interleaved_panel()
    dates = pd.bdate_range("2024-01-02", periods=62)

    result20 = mom20.compute(panel)
    result60 = mom60.compute(panel)

    assert list(result20.columns) == ["trade_date", "security_id", "raw_value"]
    assert result20.loc[result20.security_id == "A", "raw_value"].iloc[:20].isna().all()
    assert _value(result20, "A", dates[-1]) == pytest.approx((161.0 / 141.0) - 1.0)
    assert _value(result20, "B", dates[-1]) == pytest.approx((78.0 / 118.0) - 1.0)
    assert result60.loc[result60.security_id == "A", "raw_value"].iloc[:60].isna().all()
    assert _value(result60, "A", dates[-1]) == pytest.approx((161.0 / 101.0) - 1.0)


def test_volatility_uses_raw_positive_volatility_without_direction_flip():
    panel = _interleaved_panel()
    dates = pd.bdate_range("2024-01-02", periods=62)

    result = vol20.compute(panel)
    a_values = result.loc[result.security_id == "A", "raw_value"].reset_index(drop=True)

    assert a_values.iloc[:20].isna().all()
    expected_returns = pd.Series([(100.0 + i) / (99.0 + i) - 1.0 for i in range(1, 21)])
    assert _value(result, "A", dates[20]) == pytest.approx(expected_returns.std(ddof=0))
    assert _value(result, "A", dates[20]) >= 0.0
    assert np.isfinite(_value(result, "B", dates[-1]))
