"""Formula-level regression tests for the second user-authored factor batch."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from factor_modules import amihud20, turn20, volsurp20


def _panel(periods: int = 22) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    rows = []
    for index, date in enumerate(dates):
        rows.extend(
            [
                {
                    "trade_date": date,
                    "security_id": "A",
                    "adjusted_close": 100.0 + index,
                    "turnover": float(index + 1),
                    "volume": float(index + 1),
                    "traded_amount": 1_000_000.0,
                },
                {
                    "trade_date": date,
                    "security_id": "B",
                    "adjusted_close": 200.0 - index,
                    "turnover": 100.0 + index,
                    "volume": 0.0 if index < 20 else 10.0,
                    "traded_amount": 0.0 if index == 5 else 2_000_000.0,
                },
            ]
        )
    return pd.DataFrame(rows).sample(frac=1.0, random_state=19).reset_index(drop=True), dates


def _value(frame: pd.DataFrame, security_id: str, date: pd.Timestamp) -> float:
    return float(
        frame.loc[
            (frame["security_id"] == security_id) & (frame["trade_date"] == date),
            "raw_value",
        ].iloc[0]
    )


def test_turn20_and_volume_surprise_use_per_security_trailing_windows():
    panel, dates = _panel()
    turn = turn20.compute(panel)
    surprise = volsurp20.compute(panel)

    assert turn.loc[turn.security_id == "A", "raw_value"].iloc[:19].isna().all()
    assert _value(turn, "A", dates[19]) == pytest.approx(np.mean(np.arange(1, 21)))
    assert _value(turn, "B", dates[19]) == pytest.approx(np.mean(np.arange(100, 120)))
    assert surprise.loc[surprise.security_id == "A", "raw_value"].iloc[:20].isna().all()
    assert _value(surprise, "A", dates[20]) == pytest.approx(21.0 / np.mean(np.arange(1, 21)))
    assert np.isnan(_value(surprise, "B", dates[20]))


def test_amihud20_never_creates_infinite_values_from_zero_traded_amount():
    panel, dates = _panel()
    result = amihud20.compute(panel)

    assert result.loc[result.security_id == "A", "raw_value"].iloc[:20].isna().all()
    expected = np.mean([(100.0 + i) / (99.0 + i) - 1.0 for i in range(1, 21)]) / 1_000_000.0
    assert _value(result, "A", dates[20]) == pytest.approx(expected)
    assert np.isnan(_value(result, "B", dates[-1]))
    assert not np.isinf(result.raw_value.to_numpy(dtype=float)).any()
