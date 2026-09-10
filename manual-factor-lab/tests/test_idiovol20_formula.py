"""Regression tests for the IDIOVOL20 researcher factor formula."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from factor_modules import idiovol20


def _panel_with_market_relation(constant_market: bool = False) -> tuple[pd.DataFrame, np.ndarray]:
    dates = pd.bdate_range("2024-01-02", periods=22)
    market = np.r_[0.0, np.full(21, 0.001) if constant_market else np.linspace(-0.01, 0.01, 21)]
    noise = np.array([(-1) ** index * (index % 4 + 1) * 0.0007 for index in range(21)])
    stock_returns = 0.0008 + 1.3 * market[1:] + noise
    adjusted_close = 100.0 * np.cumprod(np.r_[1.0, 1.0 + stock_returns])
    return (
        pd.DataFrame(
            {
                "trade_date": dates,
                "security_id": "A",
                "adjusted_close": adjusted_close,
                "market_return": market,
            }
        ),
        stock_returns,
    )


def test_idiovol20_matches_explicit_intercept_ols_residual_standard_deviation():
    panel, stock_returns = _panel_with_market_relation()

    result = idiovol20.compute(panel)

    x = panel["market_return"].iloc[1:21].to_numpy()
    y = stock_returns[:20]
    design = np.column_stack([np.ones(len(x)), x])
    residuals = y - design @ np.linalg.lstsq(design, y, rcond=None)[0]
    expected = residuals.std(ddof=0)

    assert list(result.columns) == ["trade_date", "security_id", "raw_value"]
    assert result["raw_value"].iloc[:20].isna().all()
    assert result["raw_value"].iloc[20] == pytest.approx(expected)


def test_idiovol20_returns_missing_when_market_variance_is_zero():
    panel, _ = _panel_with_market_relation(constant_market=True)

    result = idiovol20.compute(panel)

    assert result["raw_value"].isna().all()
