from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from alpha158_research.tradable_backtest import execute_rebalance  # noqa: E402


def _state(**overrides: bool) -> pd.DataFrame:
    defaults = {"suspended": False, "limit_up": False, "limit_down": False, "unknown_blocked": False}
    defaults.update(overrides)
    return pd.DataFrame(defaults, index=["A"])


def test_limit_up_blocks_buy_but_not_cash_accounting():
    holdings, cash, ledger = execute_rebalance(
        {}, 100.0, {"A": 1.0}, pd.Series({"A": 10.0}), _state(limit_up=True), 100.0, 10
    )
    assert holdings == {}
    assert cash == 100.0
    assert ledger.loc[0, "block_reason"] == "limit_up"
    assert ledger.loc[0, "filled_notional"] == 0.0


def test_limit_down_failed_sell_is_retained():
    holdings, cash, ledger = execute_rebalance(
        {"A": 10.0}, 0.0, {}, pd.Series({"A": 10.0}), _state(limit_down=True), 100.0, 0
    )
    assert holdings == {"A": 10.0}
    assert cash == 0.0
    assert ledger.loc[0, "block_reason"] == "limit_down"


def test_cost_is_charged_only_on_actual_filled_notional():
    holdings, cash, ledger = execute_rebalance(
        {}, 100.0, {"A": 1.0}, pd.Series({"A": 10.0}), _state(), 100.0, 100
    )
    assert holdings["A"] == 9.900990099009901
    assert round(cash, 12) == 0.0
    assert round(ledger.loc[0, "trading_cost"], 12) == round(99.00990099009901 * 0.01, 12)


def test_suspension_blocks_both_sides():
    holdings, cash, ledger = execute_rebalance(
        {"A": 10.0}, 0.0, {}, pd.Series({"A": 10.0}), _state(suspended=True), 100.0, 0
    )
    assert holdings == {"A": 10.0}
    assert cash == 0.0
    assert ledger.loc[0, "block_reason"] == "suspended"


def test_buy_orders_scale_to_available_cash_without_borrowing():
    holdings, cash, ledger = execute_rebalance(
        {}, 60.0, {"A": 1.0}, pd.Series({"A": 10.0}), _state(), 100.0, 0
    )
    assert holdings == {"A": 6.0}
    assert cash == 0.0
    assert ledger.loc[0, "filled_notional"] == 60.0
