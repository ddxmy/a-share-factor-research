"""CLOSE_POS5 — Five-session closing-range position.

Title: Five-session closing-range position.
Formula: (close_t - rolling_low_5) / (rolling_high_5 - rolling_low_5).
Rationale: Closing near the recent high indicates persistent demand.
Direction: Positive; a higher closing-range position is expected to predict
higher future returns.
Required fields: adjusted_close, adjusted_high, and adjusted_low.
Availability: After the signal-date close; eligible for next-trading-day
execution.
Output contract: ``compute(panel)`` returns a pandas DataFrame containing
exactly ``trade_date``, ``security_id``, and ``raw_value``.  It must return the
raw formula value without sign-flipping, preprocessing, portfolio construction,
future-return calculation, or output writing.
"""

import pandas as pd


FACTOR_ID = "CLOSE_POS5"


def compute(panel: pd.DataFrame) -> pd.DataFrame:
    ordered = (
        panel.sort_values(['security_id', 'trade_date'])
        .reset_index(drop=True)
        .copy()
    )

    high5 = ordered.groupby('security_id')['adjusted_high'].transform(
        lambda values: values.rolling(window=5, min_periods=5).max()
    )

    low5 = ordered.groupby('security_id')['adjusted_low'].transform(
        lambda values: values.rolling(window=5, min_periods=5).min()
    )

    price_change = high5 - low5
    raw_value = (ordered['adjusted_close'] - low5) / price_change

    ordered['raw_value'] = raw_value.where(price_change > 0)

    return ordered[['trade_date', 'security_id', 'raw_value']]