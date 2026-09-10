"""Small behavioural checks for the researcher-owned REV5 calculation."""

from __future__ import annotations

import pandas as pd
import pytest

from factor_modules.rev5 import compute


def test_rev5_uses_each_securitys_own_five_session_lag() -> None:
    """Interleaved input rows must never cause prices to cross securities."""
    dates = pd.date_range("2021-01-04", periods=6, freq="B")
    panel = pd.DataFrame(
        {
            "trade_date": list(dates) * 2,
            "security_id": ["000001.SZ"] * 6 + ["600000.SH"] * 6,
            "adjusted_close": [10, 11, 12, 13, 14, 15, 20, 18, 16, 14, 12, 10],
        }
    ).sample(frac=1.0, random_state=7)

    result = compute(panel)

    first_security = result.loc[
        (result["security_id"] == "000001.SZ") & (result["trade_date"] == dates[-1]),
        "raw_value",
    ].iloc[0]
    second_security = result.loc[
        (result["security_id"] == "600000.SH") & (result["trade_date"] == dates[-1]),
        "raw_value",
    ].iloc[0]

    assert first_security == pytest.approx(15 / 10 - 1)
    assert second_security == pytest.approx(10 / 20 - 1)
    assert result.groupby("security_id").head(5)["raw_value"].isna().all()
