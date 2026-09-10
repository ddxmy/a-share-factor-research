"""IDIOVOL20 — Twenty-session idiosyncratic volatility.

Title: Twenty-session idiosyncratic volatility.
Formula: Standard deviation of trailing-20 residuals from stock daily return
regressed on market daily return.
Rationale: Higher idiosyncratic volatility is associated with lower subsequent
returns.
Direction: Negative; higher residual volatility is expected to predict lower
future returns.
Required fields: adjusted_close and market_return.
Availability: After the signal-date close; eligible for next-trading-day
execution.
Output contract: ``compute(panel)`` returns a pandas DataFrame containing
exactly ``trade_date``, ``security_id``, and ``raw_value``.  It must return the
raw formula value without sign-flipping, preprocessing, portfolio construction,
future-return calculation, or output writing.
"""

import numpy as np
import pandas as pd

FACTOR_ID = "IDIOVOL20"


def compute(panel: pd.DataFrame) -> pd.DataFrame:
    ordered = (
        panel.sort_values(['security_id', 'trade_date'])
        .reset_index(drop=True)
        .copy()
    )

    lag1 = ordered.groupby('security_id')['adjusted_close'].shift(1)
    ordered['daily_return'] = ordered['adjusted_close'] / lag1 - 1.0
    per_security = [
        rolling_idiovol(group)
        for _, group in ordered.groupby("security_id", sort=False)
    ]
    ordered["raw_value"] = pd.concat(per_security).reindex(ordered.index)

    return ordered[["trade_date", "security_id", "raw_value"]]


def rolling_idiovol(group: pd.DataFrame) -> pd.Series:
    """Compute rolling residual volatility from an intercept OLS regression."""
    market_return = group["market_return"].astype(float)
    stock_return = group["daily_return"].astype(float)
    valid_pair = market_return.notna() & stock_return.notna()
    x = market_return.where(valid_pair)
    y = stock_return.where(valid_pair)

    window = 20
    n = valid_pair.astype(float).rolling(window, min_periods=window).sum()
    sum_x = x.rolling(window, min_periods=window).sum()
    sum_y = y.rolling(window, min_periods=window).sum()
    sum_xx = (x * x).rolling(window, min_periods=window).sum()
    sum_yy = (y * y).rolling(window, min_periods=window).sum()
    sum_xy = (x * y).rolling(window, min_periods=window).sum()

    centered_xx = sum_xx - sum_x.pow(2).div(n)
    centered_yy = sum_yy - sum_y.pow(2).div(n)
    centered_xy = sum_xy - sum_x.mul(sum_y).div(n)
    residual_sum_squares = centered_yy - centered_xy.pow(2).div(
        centered_xx.where(centered_xx > 0)
    )
    residual_variance = residual_sum_squares.clip(lower=0).div(n)
    return np.sqrt(residual_variance).where((n == window) & (centered_xx > 0))
