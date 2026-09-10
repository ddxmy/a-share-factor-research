"""MOM20 — Twenty-session momentum.

Title: Twenty-session momentum.
Formula: close_t / close_(t-20) - 1.
Rationale: Intermediate momentum: recent winners continue to outperform.
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


FACTOR_ID = "MOM20"


def compute(panel: pd.DataFrame) -> pd.DataFrame:
    ordered = panel.sort_values(['security_id', 'trade_date']).reset_index(drop=True).copy()
    lag20 = ordered.groupby('security_id')['adjusted_close'].shift(20)
    ordered['raw_value'] = ordered['adjusted_close'] / lag20 - 1.0

    return ordered[['trade_date', 'security_id', 'raw_value']]