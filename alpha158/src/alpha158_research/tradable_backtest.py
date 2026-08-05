"""Small, deterministic execution primitives for the G7 A-share Top50 backtest."""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd


def _block_reason(state: pd.Series | None, side: str, price: float | None) -> str | None:
    if price is None or not np.isfinite(price) or price <= 0:
        return "missing_open_price"
    if state is None or bool(state.get("unknown_blocked", True)):
        return "unknown_blocked"
    if bool(state.get("suspended", False)):
        return "suspended"
    if side == "buy" and bool(state.get("limit_up", False)):
        return "limit_up"
    if side == "sell" and bool(state.get("limit_down", False)):
        return "limit_down"
    return None


def execute_rebalance(
    holdings: Mapping[str, float],
    cash: float,
    target_weights: Mapping[str, float],
    open_prices: pd.Series,
    tradability: pd.DataFrame,
    nav_before: float,
    one_way_cost_bps: float,
) -> tuple[dict[str, float], float, pd.DataFrame]:
    """Execute a sell-first, no-borrowing rebalance at supplied opening prices.

    Shares are deliberately fractional: this isolates signal/execution effects from lot-size rules,
    which are outside the frozen G7 protocol.
    """
    if cash < -1e-9 or nav_before <= 0 or one_way_cost_bps < 0:
        raise ValueError("cash, NAV, and trading cost inputs are invalid")
    current = {str(code): float(shares) for code, shares in holdings.items() if shares > 1e-12}
    weights = {str(code): float(weight) for code, weight in target_weights.items() if weight > 1e-12}
    if sum(weights.values()) > 1 + 1e-10:
        raise ValueError("target weights cannot exceed one without borrowing")
    cost_rate = float(one_way_cost_bps) / 10000.0
    ledger_rows: list[dict[str, object]] = []

    def price_for(code: str) -> float | None:
        if code not in open_prices.index:
            return None
        value = open_prices.loc[code]
        return float(value) if pd.notna(value) else None

    def state_for(code: str) -> pd.Series | None:
        return tradability.loc[code] if code in tradability.index else None

    desired = {
        code: (weights.get(code, 0.0) * nav_before / price)
        for code in set(current) | set(weights)
        if (price := price_for(code)) is not None and np.isfinite(price) and price > 0
    }

    for code in sorted(current):
        current_shares = current[code]
        desired_shares = desired.get(code, 0.0)
        sell_shares = max(current_shares - desired_shares, 0.0)
        if sell_shares <= 1e-12:
            continue
        price = price_for(code)
        reason = _block_reason(state_for(code), "sell", price)
        intended = sell_shares * (price or 0.0)
        filled = 0.0 if reason else intended
        cost = filled * cost_rate
        if not reason:
            current[code] = current_shares - sell_shares
            if current[code] <= 1e-12:
                current.pop(code)
            cash += filled - cost
        ledger_rows.append({"code": code, "side": "sell", "intended_notional": intended, "filled_notional": filled, "trading_cost": cost, "block_reason": reason})

    buy_candidates: list[tuple[str, float, float]] = []
    for code in sorted(weights):
        price = price_for(code)
        desired_shares = desired.get(code)
        if desired_shares is None:
            reason = _block_reason(state_for(code), "buy", price)
            ledger_rows.append({"code": code, "side": "buy", "intended_notional": 0.0, "filled_notional": 0.0, "trading_cost": 0.0, "block_reason": reason})
            continue
        buy_shares = max(desired_shares - current.get(code, 0.0), 0.0)
        if buy_shares <= 1e-12:
            continue
        reason = _block_reason(state_for(code), "buy", price)
        intended = buy_shares * float(price)
        if reason:
            ledger_rows.append({"code": code, "side": "buy", "intended_notional": intended, "filled_notional": 0.0, "trading_cost": 0.0, "block_reason": reason})
        else:
            buy_candidates.append((code, buy_shares, float(price)))

    total_required = sum(shares * price * (1 + cost_rate) for _, shares, price in buy_candidates)
    scale = min(1.0, cash / total_required) if total_required > 0 else 0.0
    for code, shares, price in buy_candidates:
        filled = shares * price * scale
        cost = filled * cost_rate
        current[code] = current.get(code, 0.0) + filled / price
        cash -= filled + cost
        ledger_rows.append({"code": code, "side": "buy", "intended_notional": shares * price, "filled_notional": filled, "trading_cost": cost, "block_reason": None})
    if cash < -1e-7:
        raise RuntimeError("cash became negative after constrained buy execution")
    return current, max(cash, 0.0), pd.DataFrame(ledger_rows, columns=["code", "side", "intended_notional", "filled_notional", "trading_cost", "block_reason"])
