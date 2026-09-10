"""PV_CORR20 — Twenty-session price-volume correlation.

Title: Twenty-session price-volume correlation.
Formula: Correlation of daily adjusted-close returns and log daily volume over
trailing 20 sessions.
Rationale: Positive price-volume comovement reflects informed trading and
demand continuation.
Direction: Positive; higher price-volume correlation is expected to predict
higher future returns.
Required fields: adjusted_close and volume.
Availability: After the signal-date close; eligible for next-trading-day
execution.
Output contract: ``compute(panel)`` returns a pandas DataFrame containing
exactly ``trade_date``, ``security_id``, and ``raw_value``.  It must return the
raw formula value without sign-flipping, preprocessing, portfolio construction,
future-return calculation, or output writing.
"""

import pandas as pd
import numpy as np


FACTOR_ID = "PV_CORR20"


def compute(panel: pd.DataFrame) -> pd.DataFrame:
    ordered = (
            panel.sort_values(['security_id', 'trade_date'])
            .reset_index(drop=True)
            .copy()
        )
    lag1 = ordered.groupby('security_id')['adjusted_close'].shift(1)
    ordered['daily_return'] = ordered['adjusted_close'] / lag1 - 1.0
    valid_volume = ordered['volume'].where(ordered['volume'] > 0)
    ordered['log_volume'] = np.log(valid_volume)
    ordered["raw_value"] = (
        ordered.groupby("security_id", group_keys=False)
        .apply(rolling_pv_corr, include_groups=False)
    )
    return ordered[["trade_date", "security_id", "raw_value"]]


def rolling_pv_corr(group: pd.DataFrame) -> pd.Series:
    return group['daily_return'].rolling(
        window=20,
        min_periods=20,
    ).corr(group['log_volume'])
