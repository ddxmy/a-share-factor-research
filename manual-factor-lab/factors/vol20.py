"""VOL20 — Twenty-session realized volatility.

Title: Twenty-session realized volatility.
Formula: Standard deviation of daily adjusted-close returns over trailing 20
sessions.
Rationale: Higher realized volatility is associated with lower subsequent
returns.
Direction: Negative; higher volatility is expected to predict lower future
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


FACTOR_ID = "VOL20"


def compute(panel: pd.DataFrame) -> pd.DataFrame:
    ordered = panel.sort_values(['security_id', 'trade_date']).reset_index(drop=True).copy()
    lag1 = ordered.groupby('security_id')['adjusted_close'].shift(1)
    ordered['daily_return'] = ordered['adjusted_close'] / lag1 - 1.0
    ordered['raw_value'] = (
        ordered.groupby('security_id')['daily_return']
        .transform(lambda values: values.rolling(20, min_periods=20).std(ddof=0))
    )

    return ordered[['trade_date', 'security_id', 'raw_value']]