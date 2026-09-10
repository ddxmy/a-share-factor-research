"""TURN20 — Twenty-session average turnover.

Title: Twenty-session average turnover.
Formula: Mean daily turnover over trailing 20 sessions.
Rationale: High turnover signals attention and short-term overpricing.
Direction: Negative; higher turnover is expected to predict lower future
returns.
Required fields: turnover.
Availability: After the signal-date close; eligible for next-trading-day
execution.
Output contract: ``compute(panel)`` returns a pandas DataFrame containing
exactly ``trade_date``, ``security_id``, and ``raw_value``.  It must return the
raw formula value without sign-flipping, preprocessing, portfolio construction,
future-return calculation, or output writing.
"""

import pandas as pd


FACTOR_ID = "TURN20"


def compute(panel: pd.DataFrame) -> pd.DataFrame:
    ordered = panel.sort_values(['security_id', 'trade_date']).reset_index(drop=True).copy()
    ordered['raw_value'] = ordered.groupby('security_id')['turnover'].transform(
        lambda values: values.rolling(20, min_periods=20).mean()
    )

    return ordered[['trade_date', 'security_id', 'raw_value']]