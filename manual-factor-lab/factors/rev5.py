"""REV5 — Five-session reversal.

Title: Five-session reversal.
Formula: close_t / close_(t-5) - 1.
Rationale: Short-horizon reversal: recent losers outperform recent winners.
Direction: Negative; lower raw returns are expected to predict higher future
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


FACTOR_ID = "REV5"


def compute(panel: pd.DataFrame) -> pd.DataFrame:
    ordered = panel.sort_values(['security_id', 'trade_date']).reset_index(drop=True).copy()
    lag5 = ordered.groupby('security_id')['adjusted_close'].shift(5)
    ordered['raw_value'] = ordered['adjusted_close'] / lag5 - 1.0

    return ordered[['trade_date', 'security_id', 'raw_value']]