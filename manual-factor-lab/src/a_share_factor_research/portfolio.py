"""Matched-frequency portfolio simulations for directed factor scores."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np
import pandas as pd


_PERIODS_PER_YEAR = {1: 252, 5: 52, 20: 12}
_SUMMARY_COLUMNS = [
    "horizon_days",
    "periods_per_year",
    "portfolio",
    "portfolio_kind",
    "is_diagnostic",
    "return_type",
    "n_periods",
    "n_evaluable_periods",
    "annualized_return",
    "volatility",
    "sharpe",
    "max_drawdown",
    "mean_turnover",
]


@dataclass(frozen=True)
class PortfolioSimulation:
    """Portfolio return tables produced for one holding-period profile."""

    horizon_days: int
    periods_per_year: int
    quintiles: pd.DataFrame
    top_k: pd.DataFrame
    long_short: pd.DataFrame
    summary: pd.DataFrame


def net_return(gross_return: float, turnover: float, one_way_cost_bps: float) -> float:
    """Deduct a one-way transaction cost from a period gross return."""
    values = (gross_return, turnover, one_way_cost_bps)
    if not all(isinstance(value, Real) and np.isfinite(value) for value in values):
        raise ValueError("gross_return, turnover, and one_way_cost_bps must be finite numbers")
    if turnover < 0 or one_way_cost_bps < 0:
        raise ValueError("turnover and one_way_cost_bps must be non-negative")
    return gross_return - turnover * one_way_cost_bps / 10_000.0


def simulate_portfolios(
    panel: pd.DataFrame,
    horizon_days: int,
    top_k: int,
    quintiles: int,
    one_way_cost_bps: float,
) -> PortfolioSimulation:
    """Simulate one independent daily, weekly, or monthly holding profile.

    Each profile selects its own non-overlapping rebalance dates and consumes
    the exact open-to-open label for its horizon.  Portfolio formation uses
    only next-open tradability and finite signal-date scores.  Future label
    availability affects evaluation, never selection.
    """
    _validate_parameters(horizon_days, top_k, quintiles, one_way_cost_bps)
    label_column = f"label_excess_o2o_{horizon_days}d"
    label_end_column = f"label_end_date_{horizon_days}d"
    timing_columns_supplied = "entry_date" in panel and label_end_column in panel
    if ("entry_date" in panel) != (label_end_column in panel):
        raise ValueError(
            f"Portfolio panel must supply entry_date and {label_end_column} together."
        )
    prepared = _prepare_panel(panel, label_column)
    if not timing_columns_supplied:
        prepared["entry_date"] = pd.NaT
        prepared[label_end_column] = pd.NaT
    rebalance_dates = prepared["signal_date"].drop_duplicates().sort_values().iloc[::horizon_days]

    quintile_records: list[dict[str, object]] = []
    top_k_records: list[dict[str, object]] = []
    long_short_records: list[dict[str, object]] = []
    previous_weights: dict[str, dict[object, float]] = {}
    minimum_names = max(top_k, quintiles)

    for signal_date in rebalance_dates:
        cross_section = prepared.loc[prepared["signal_date"].eq(signal_date)].copy()
        finite_score = np.isfinite(cross_section["directed_score"].to_numpy(dtype=float))
        tradable = cross_section["tradable_next_open"].astype("boolean").fillna(False)
        eligible = cross_section.loc[finite_score & tradable.to_numpy(dtype=bool)].copy()
        if len(eligible) < minimum_names:
            _record_invalid_cross_section(
                quintile_records,
                top_k_records,
                long_short_records,
                cross_section=cross_section,
                signal_date=signal_date,
                horizon_days=horizon_days,
                top_k=top_k,
                quintiles=quintiles,
                label_end_column=label_end_column,
                timing_required=timing_columns_supplied,
            )
            continue

        eligible["_security_sort_key"] = eligible["security_id"].astype(str)
        ranked = eligible.sort_values(
            ["directed_score", "_security_sort_key"], kind="mergesort"
        )
        groups = np.array_split(ranked.index.to_numpy(), quintiles)
        quintile_weights: dict[str, dict[object, float]] = {}
        for number, group_index in enumerate(groups, start=1):
            holdings = eligible.loc[group_index]
            portfolio = f"Q{number}"
            weights = _equal_weights(holdings["security_id"])
            quintile_weights[portfolio] = weights
            _record_period(
                quintile_records,
                signal_date=signal_date,
                horizon_days=horizon_days,
                portfolio=portfolio,
                portfolio_kind="quintile_long",
                is_diagnostic=False,
                weights=weights,
                holdings=holdings,
                label_column=label_column,
                label_end_column=label_end_column,
                timing_required=timing_columns_supplied,
                previous_weights=previous_weights,
                one_way_cost_bps=one_way_cost_bps,
            )

        top_holdings = ranked.tail(top_k)
        top_portfolio = f"top_{top_k}"
        top_weights = _equal_weights(top_holdings["security_id"])
        _record_period(
            top_k_records,
            signal_date=signal_date,
            horizon_days=horizon_days,
            portfolio=top_portfolio,
            portfolio_kind="top_k_long",
            is_diagnostic=False,
            weights=top_weights,
            holdings=top_holdings,
            label_column=label_column,
            label_end_column=label_end_column,
            timing_required=timing_columns_supplied,
            previous_weights=previous_weights,
            one_way_cost_bps=one_way_cost_bps,
        )

        spread_weights = dict(quintile_weights[f"Q{quintiles}"])
        for security_id, weight in quintile_weights["Q1"].items():
            spread_weights[security_id] = spread_weights.get(security_id, 0.0) - weight
        spread_names = set(quintile_weights[f"Q{quintiles}"]) | set(quintile_weights["Q1"])
        spread_holdings = eligible.loc[eligible["security_id"].isin(spread_names)]
        _record_period(
            long_short_records,
            signal_date=signal_date,
            horizon_days=horizon_days,
            portfolio="top_bottom",
            portfolio_kind="diagnostic_long_short",
            is_diagnostic=True,
            weights=spread_weights,
            holdings=spread_holdings,
            label_column=label_column,
            label_end_column=label_end_column,
            timing_required=timing_columns_supplied,
            previous_weights=previous_weights,
            one_way_cost_bps=one_way_cost_bps,
        )

    quintile_table = _with_nav(quintile_records, label_end_column)
    top_k_table = _with_nav(top_k_records, label_end_column)
    long_short_table = _with_nav(long_short_records, label_end_column)
    periods_per_year = _PERIODS_PER_YEAR[horizon_days]
    summary = _summarize_portfolios(
        pd.concat([quintile_table, top_k_table, long_short_table], ignore_index=True),
        periods_per_year,
    )
    return PortfolioSimulation(
        horizon_days=horizon_days,
        periods_per_year=periods_per_year,
        quintiles=quintile_table,
        top_k=top_k_table,
        long_short=long_short_table,
        summary=summary,
    )


def _validate_parameters(
    horizon_days: int, top_k: int, quintiles: int, one_way_cost_bps: float
) -> None:
    if not isinstance(horizon_days, Integral) or int(horizon_days) not in _PERIODS_PER_YEAR:
        raise ValueError("horizon_days must be 1, 5, or 20")
    if not isinstance(top_k, Integral) or top_k <= 0:
        raise ValueError("top_k must be a positive integer")
    if not isinstance(quintiles, Integral) or quintiles < 2:
        raise ValueError("quintiles must be an integer of at least two")
    if (
        not isinstance(one_way_cost_bps, Real)
        or not np.isfinite(one_way_cost_bps)
        or one_way_cost_bps < 0
    ):
        raise ValueError("one_way_cost_bps must be a finite non-negative number")


def _prepare_panel(panel: pd.DataFrame, label_column: str) -> pd.DataFrame:
    required_columns = {
        "signal_date",
        "security_id",
        "directed_score",
        label_column,
        "tradable_next_open",
    }
    missing_columns = required_columns.difference(panel.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Portfolio panel is missing required columns: {missing}.")

    prepared = panel.loc[:, list(panel.columns)].copy().reset_index(drop=True)
    prepared["signal_date"] = pd.to_datetime(prepared["signal_date"], errors="coerce")
    if prepared["signal_date"].isna().any():
        raise ValueError("Portfolio panel contains an unparsable signal_date.")
    if prepared["security_id"].isna().any():
        raise ValueError("Portfolio panel contains a missing security_id.")
    if prepared.duplicated(["signal_date", "security_id"]).any():
        raise ValueError("Portfolio panel must have unique (signal_date, security_id) keys.")
    prepared["directed_score"] = pd.to_numeric(prepared["directed_score"], errors="coerce")
    prepared[label_column] = pd.to_numeric(prepared[label_column], errors="coerce")
    date_columns = [
        column
        for column in prepared
        if column == "entry_date" or column.startswith("label_end_date_")
    ]
    for column in date_columns:
        prepared[column] = pd.to_datetime(prepared[column], errors="coerce")
    return prepared.sort_values(["signal_date", "security_id"], kind="mergesort").reset_index(drop=True)


def _equal_weights(security_ids: pd.Series) -> dict[object, float]:
    weight = 1.0 / len(security_ids)
    return {security_id: weight for security_id in security_ids}


def _record_period(
    records: list[dict[str, object]],
    *,
    signal_date: pd.Timestamp,
    horizon_days: int,
    portfolio: str,
    portfolio_kind: str,
    is_diagnostic: bool,
    weights: dict[object, float],
    holdings: pd.DataFrame,
    label_column: str,
    label_end_column: str,
    timing_required: bool,
    previous_weights: dict[str, dict[object, float]],
    one_way_cost_bps: float,
) -> None:
    prior = previous_weights.get(portfolio, {})
    names = set(weights) | set(prior)
    turnover = 0.5 * sum(abs(weights.get(name, 0.0) - prior.get(name, 0.0)) for name in names)
    indexed = holdings.set_index("security_id")
    labels = indexed[label_column]
    labels_are_finite = np.isfinite(labels.to_numpy(dtype=float)).all()
    entry_date, entry_is_valid = _common_date(holdings["entry_date"])
    label_end_date, end_is_valid = _common_date(holdings[label_end_column])
    timing_is_valid = not timing_required or (entry_is_valid and end_is_valid)
    is_evaluable = bool(labels_are_finite and timing_is_valid)
    gross = (
        float(sum(weight * float(labels.loc[name]) for name, weight in weights.items()))
        if is_evaluable
        else np.nan
    )
    cost = turnover * one_way_cost_bps / 10_000.0
    records.append(
        {
            "signal_date": pd.Timestamp(signal_date),
            "entry_date": entry_date,
            label_end_column: label_end_date,
            "nav_date": label_end_date,
            "horizon_days": horizon_days,
            "portfolio": portfolio,
            "portfolio_kind": portfolio_kind,
            "is_diagnostic": is_diagnostic,
            "n_names": len(weights),
            "is_evaluable": is_evaluable,
            "gross_return": gross,
            "turnover": turnover,
            "cost": cost,
            "net_return": (
                net_return(gross, turnover, one_way_cost_bps) if is_evaluable else np.nan
            ),
        }
    )
    previous_weights[portfolio] = weights


def _record_invalid_cross_section(
    quintile_records: list[dict[str, object]],
    top_k_records: list[dict[str, object]],
    long_short_records: list[dict[str, object]],
    *,
    cross_section: pd.DataFrame,
    signal_date: pd.Timestamp,
    horizon_days: int,
    top_k: int,
    quintiles: int,
    label_end_column: str,
    timing_required: bool,
) -> None:
    entry_date, entry_is_valid = _common_date(cross_section["entry_date"])
    label_end_date, end_is_valid = _common_date(cross_section[label_end_column])
    if timing_required and not (entry_is_valid and end_is_valid):
        entry_date = pd.NaT
        label_end_date = pd.NaT

    def append_placeholder(
        records: list[dict[str, object]],
        portfolio: str,
        portfolio_kind: str,
        is_diagnostic: bool,
    ) -> None:
        records.append(
            {
                "signal_date": pd.Timestamp(signal_date),
                "entry_date": entry_date,
                label_end_column: label_end_date,
                "nav_date": label_end_date,
                "horizon_days": horizon_days,
                "portfolio": portfolio,
                "portfolio_kind": portfolio_kind,
                "is_diagnostic": is_diagnostic,
                "n_names": 0,
                "is_evaluable": False,
                "gross_return": np.nan,
                "turnover": 0.0,
                "cost": 0.0,
                "net_return": np.nan,
            }
        )

    for number in range(1, quintiles + 1):
        append_placeholder(quintile_records, f"Q{number}", "quintile_long", False)
    append_placeholder(top_k_records, f"top_{top_k}", "top_k_long", False)
    append_placeholder(long_short_records, "top_bottom", "diagnostic_long_short", True)


def _common_date(values: pd.Series) -> tuple[pd.Timestamp | pd.NaT, bool]:
    dates = pd.to_datetime(values, errors="coerce")
    unique_dates = dates.dropna().unique()
    if len(dates) == 0 or dates.isna().any() or len(unique_dates) != 1:
        return pd.NaT, False
    return pd.Timestamp(unique_dates[0]), True


def _return_columns(label_end_column: str) -> list[str]:
    return [
        "signal_date",
        "entry_date",
        label_end_column,
        "nav_date",
        "horizon_days",
        "portfolio",
        "portfolio_kind",
        "is_diagnostic",
        "n_names",
        "is_evaluable",
        "gross_return",
        "turnover",
        "cost",
        "net_return",
        "gross_nav",
        "net_nav",
    ]


def _with_nav(records: list[dict[str, object]], label_end_column: str) -> pd.DataFrame:
    return_columns = _return_columns(label_end_column)
    if not records:
        return pd.DataFrame(columns=return_columns)
    table = pd.DataFrame.from_records(records)
    table = table.sort_values(["portfolio", "signal_date"], kind="mergesort").reset_index(
        drop=True
    )
    table["gross_nav"] = np.nan
    table["net_nav"] = np.nan
    for _, group in table.groupby("portfolio", sort=False):
        table.loc[group.index, "gross_nav"] = _halted_nav(
            group["gross_return"], group["is_evaluable"]
        )
        table.loc[group.index, "net_nav"] = _halted_nav(
            group["net_return"], group["is_evaluable"]
        )
    return table[return_columns]


def _halted_nav(returns: pd.Series, is_evaluable: pd.Series) -> pd.Series:
    nav = 1.0
    active = True
    values = []
    for period_return, evaluable in zip(returns, is_evaluable):
        if not active or not bool(evaluable) or not np.isfinite(period_return):
            active = False
            values.append(np.nan)
            continue
        nav *= 1.0 + float(period_return)
        values.append(nav)
    return pd.Series(values, index=returns.index, dtype=float)


def _summarize_portfolios(table: pd.DataFrame, periods_per_year: int) -> pd.DataFrame:
    if table.empty:
        return pd.DataFrame(columns=_SUMMARY_COLUMNS)
    records: list[dict[str, object]] = []
    for (portfolio, portfolio_kind, is_diagnostic), group in table.groupby(
        ["portfolio", "portfolio_kind", "is_diagnostic"], sort=True
    ):
        ordered = group.sort_values("signal_date")
        for return_type in ("gross", "net"):
            all_returns = ordered[f"{return_type}_return"].astype(float)
            returns = all_returns.loc[ordered["is_evaluable"]].dropna()
            nav = ordered[f"{return_type}_nav"].astype(float)
            n_periods = len(ordered)
            n_evaluable_periods = int(ordered["is_evaluable"].sum())
            final_nav = float(nav.iloc[-1])
            annualized_return = (
                final_nav ** (periods_per_year / n_periods) - 1.0 if final_nav > 0 else np.nan
            )
            volatility = float(returns.std(ddof=1) * np.sqrt(periods_per_year))
            return_std = float(returns.std(ddof=1))
            sharpe = (
                float(returns.mean() / return_std * np.sqrt(periods_per_year))
                if np.isfinite(return_std) and return_std > 0
                else np.nan
            )
            valid_nav = nav.dropna().to_numpy(dtype=float)
            nav_with_origin = np.concatenate(([1.0], valid_nav))
            drawdowns = nav_with_origin / np.maximum.accumulate(nav_with_origin) - 1.0
            records.append(
                {
                    "horizon_days": int(ordered["horizon_days"].iloc[0]),
                    "periods_per_year": periods_per_year,
                    "portfolio": portfolio,
                    "portfolio_kind": portfolio_kind,
                    "is_diagnostic": bool(is_diagnostic),
                    "return_type": return_type,
                    "n_periods": n_periods,
                    "n_evaluable_periods": n_evaluable_periods,
                    "annualized_return": annualized_return,
                    "volatility": volatility,
                    "sharpe": sharpe,
                    "max_drawdown": float(drawdowns.min()),
                    "mean_turnover": float(ordered["turnover"].mean()),
                }
            )
    return pd.DataFrame.from_records(records, columns=_SUMMARY_COLUMNS)
