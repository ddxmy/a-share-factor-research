"""MOM60 — Sixty-session momentum.

Title: Sixty-session momentum.
Formula: close_t / close_(t-60) - 1.
Rationale: Medium-horizon momentum: sustained winners continue to outperform.
Direction: Positive; higher raw returns are expected to predict higher future
returns.
Required fields: adjusted_close.
Availability: After the signal-date close; eligible for next-trading-day
execution.
Output contract: ``compute(panel)`` returns a pandas DataFrame containing
exactly ``trade_date``, ``security_id``, and ``raw_value``.  It must return the
raw formula value without sign-flipping, preprocessing, portfolio construction,
future-return calculation, or output writing.
"""

import pandas as pd


FACTOR_ID = "MOM60"


def compute(panel: pd.DataFrame) -> pd.DataFrame:
    ordered = panel.sort_values(['security_id', 'trade_date']).reset_index(drop=True).copy()
    lag60 = ordered.groupby('security_id')['adjusted_close'].shift(60)
    ordered['raw_value'] = ordered['adjusted_close'] / lag60 - 1.0

    return ordered[['trade_date', 'security_id', 'raw_value']]