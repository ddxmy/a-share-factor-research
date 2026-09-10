"""AMIHUD20 — Twenty-session Amihud illiquidity.

Title: Twenty-session Amihud illiquidity.
Formula: Mean of abs(daily adjusted-close return) / traded_amount over trailing
20 sessions.
Rationale: Greater illiquidity earns an expected return premium.
Direction: Positive; higher illiquidity is expected to predict higher future
returns.
Required fields: adjusted_close and traded_amount.
Availability: After the signal-date close; eligible for next-trading-day
execution.
Output contract: ``compute(panel)`` returns a pandas DataFrame containing
exactly ``trade_date``, ``security_id``, and ``raw_value``.  It must return the
raw formula value without sign-flipping, preprocessing, portfolio construction,
future-return calculation, or output writing.
"""

import pandas as pd


FACTOR_ID = "AMIHUD20"


def compute(panel: pd.DataFrame) -> pd.DataFrame:
    ordered = panel.sort_values(['security_id', 'trade_date']).reset_index(drop=True).copy()
    lag1 = ordered.groupby('security_id')['adjusted_close'].shift(1)
    ordered['daily_return'] = ordered['adjusted_close'] / lag1 - 1.0

    ordered['traded_amount'] = ordered['traded_amount'].where(
        ordered['traded_amount'] > 0
    )
    ordered['daily_factor'] = ordered['daily_return'].abs() / ordered['traded_amount']
    ordered['raw_value'] = (
        ordered.groupby('security_id')['daily_factor'].transform(
            lambda values: values.rolling(20, min_periods=20)
            .mean()
        )
    )

    return ordered[['trade_date', 'security_id', 'raw_value']]