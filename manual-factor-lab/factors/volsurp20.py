"""VOLSURP20 — Twenty-session volume surprise.

Title: Twenty-session volume surprise.
Formula: daily volume_t / mean daily volume over trailing 20 sessions.
Rationale: Unusually high volume confirms information-driven demand.
Direction: Positive; higher volume surprise is expected to predict higher future
returns.
Required fields: volume.
Availability: After the signal-date close; eligible for next-trading-day
execution.
Output contract: ``compute(panel)`` returns a pandas DataFrame containing
exactly ``trade_date``, ``security_id``, and ``raw_value``.  It must return the
raw formula value without sign-flipping, preprocessing, portfolio construction,
future-return calculation, or output writing.
"""

import pandas as pd


FACTOR_ID = "VOLSURP20"


def compute(panel: pd.DataFrame) -> pd.DataFrame:
        ordered = panel.sort_values(['security_id', 'trade_date']).reset_index(drop=True).copy()
        ordered['mean_volume'] = ordered.groupby('security_id')['volume'].transform(
            lambda values: values.shift(1).rolling(20, min_periods=20).mean()
        )
        ordered['mean_volume'] = ordered['mean_volume'].where(
                ordered['mean_volume'] > 0
        )
        ordered['raw_value'] = ordered['volume'] / ordered['mean_volume']

        return ordered[['trade_date', 'security_id', 'raw_value']]