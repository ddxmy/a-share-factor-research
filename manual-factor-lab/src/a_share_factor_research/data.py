"""Point-in-time panel loading and exact forward open-to-open labels."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from .config import ResolvedPaths


_PANEL_KEYS = ["trade_date", "security_id"]


def load_research_panel(paths: ResolvedPaths, start: str | pd.Timestamp, end: str | pd.Timestamp) -> pd.DataFrame:
    """Load valid daily rows that are CSI 300 members on their exact dates.

    The catalog is deliberately joined on both date and security ID.  Basic
    eligibility represents PIT membership and usable signal-date prices; next
    open tradability remains a separate field for portfolio construction.
    """
    start_date = _as_date(start, "start")
    end_date = _as_date(end, "end")
    if start_date > end_date:
        raise ValueError("start must not be after end")

    daily = _read_daily(paths.daily_panel)
    membership = _read_membership(paths.pit_csi300)
    tradability = _read_tradability(paths.open_eligibility)

    panel = daily.merge(membership, on=_PANEL_KEYS, how="inner", validate="one_to_one")
    # Tradability is owned by the separate PIT eligibility catalog.  A daily
    # source may carry a convenience/proxy column too; it must not shadow the
    # canonical catalogue value during the merge.
    panel = panel.drop(columns=["tradable_next_open"], errors="ignore")
    panel = panel.merge(tradability, on=_PANEL_KEYS, how="left", validate="one_to_one")
    panel["tradable_next_open"] = panel["tradable_next_open"].fillna(False).astype(bool)
    panel["signal_date"] = panel["trade_date"]
    panel["basic_eligible"] = True

    return (
        panel.loc[panel["trade_date"].between(start_date, end_date)]
        .sort_values(_PANEL_KEYS)
        .reset_index(drop=True)
    )


def attach_forward_labels(
    panel: pd.DataFrame, benchmark_open: pd.DataFrame, horizons: Iterable[int]
) -> pd.DataFrame:
    """Attach matched excess O2O returns without filling absent observations.

    A close[t] signal enters at the next observable security open and exits at
    its (h + 1)th observable open.  CSI 300 opens are looked up on those exact
    entry and exit dates, so a missing benchmark observation makes the label
    unavailable rather than inventing a filled value.
    """
    requested_horizons = _validated_horizons(horizons)
    labelled = _validate_panel_for_labels(panel)
    benchmark = _read_benchmark_frame(benchmark_open)

    ordered = labelled.sort_values(["security_id", "trade_date"]).copy()
    grouped = ordered.groupby("security_id", sort=False)
    ordered["entry_date"] = grouped["trade_date"].shift(-1)
    ordered["_entry_open"] = grouped["adjusted_open"].shift(-1)

    primary_label_valid: pd.Series | None = None
    for horizon in requested_horizons:
        end_date_column = f"label_end_date_{horizon}d"
        exit_open_column = f"_exit_open_{horizon}d"
        label_column = f"label_excess_o2o_{horizon}d"

        ordered[end_date_column] = grouped["trade_date"].shift(-(horizon + 1))
        ordered[exit_open_column] = grouped["adjusted_open"].shift(-(horizon + 1))
        benchmark_forward = benchmark.sort_values("trade_date").copy()
        benchmark_forward["_entry_date"] = benchmark_forward["trade_date"].shift(-1)
        benchmark_forward["_entry_open"] = benchmark_forward["adjusted_open"].shift(-1)
        benchmark_forward["_end_date"] = benchmark_forward["trade_date"].shift(-(horizon + 1))
        benchmark_forward["_exit_open"] = benchmark_forward["adjusted_open"].shift(-(horizon + 1))
        benchmark_by_signal = benchmark_forward.set_index("trade_date")
        entry_benchmark_date = ordered["trade_date"].map(benchmark_by_signal["_entry_date"])
        end_benchmark_date = ordered["trade_date"].map(benchmark_by_signal["_end_date"])
        entry_benchmark = ordered["trade_date"].map(benchmark_by_signal["_entry_open"])
        exit_benchmark = ordered["trade_date"].map(benchmark_by_signal["_exit_open"])
        values = ordered[["_entry_open", exit_open_column]].to_numpy(dtype=float)
        benchmark_values = pd.DataFrame(
            {"entry": entry_benchmark, "exit": exit_benchmark}, index=ordered.index
        ).to_numpy(dtype=float)
        label_valid = (
            np.isfinite(values).all(axis=1)
            & (values > 0).all(axis=1)
            & np.isfinite(benchmark_values).all(axis=1)
            & (benchmark_values > 0).all(axis=1)
            & ordered["entry_date"].eq(entry_benchmark_date)
            & ordered[end_date_column].eq(end_benchmark_date)
        )
        excess_return = (ordered[exit_open_column] / ordered["_entry_open"] - 1.0) - (
            exit_benchmark / entry_benchmark - 1.0
        )
        ordered[label_column] = excess_return.where(label_valid)
        if horizon == requested_horizons[0]:
            primary_label_valid = pd.Series(label_valid, index=ordered.index)

    # The baseline eligibility uses the shortest supplied horizon (1D in the
    # frozen profile); longer horizons retain their own missing labels.
    if primary_label_valid is not None:
        ordered["basic_eligible"] = ordered["basic_eligible"].astype(bool) & primary_label_valid

    temporary_columns = ["_entry_open"] + [f"_exit_open_{horizon}d" for horizon in requested_horizons]
    return ordered.drop(columns=temporary_columns).sort_values(_PANEL_KEYS).reset_index(drop=True)


def _read_daily(path) -> pd.DataFrame:
    daily = pd.read_parquet(path).copy()
    _require_columns(daily, [*_PANEL_KEYS, "adjusted_open", "adjusted_close"], "daily panel")
    _parse_dates(daily, "daily panel")
    _validate_unique_keys(daily, "daily panel")
    _validate_positive_finite(daily, ["adjusted_open", "adjusted_close"], "daily panel")
    return daily


def _read_membership(path) -> pd.DataFrame:
    membership = pd.read_parquet(path).copy()
    _require_columns(membership, _PANEL_KEYS, "PIT CSI 300 membership")
    _parse_dates(membership, "PIT CSI 300 membership")
    if "is_member" in membership:
        membership = membership.loc[membership["is_member"].astype(bool)].copy()
    _validate_unique_keys(membership, "PIT CSI 300 membership")
    return membership[_PANEL_KEYS]


def _read_tradability(path) -> pd.DataFrame:
    tradability = pd.read_parquet(path).copy()
    _require_columns(tradability, [*_PANEL_KEYS, "tradable_next_open"], "open eligibility")
    _parse_dates(tradability, "open eligibility")
    _validate_unique_keys(tradability, "open eligibility")
    return tradability[_PANEL_KEYS + ["tradable_next_open"]]


def _validate_panel_for_labels(panel: pd.DataFrame) -> pd.DataFrame:
    labelled = panel.copy()
    _require_columns(labelled, [*_PANEL_KEYS, "adjusted_open", "basic_eligible"], "research panel")
    _parse_dates(labelled, "research panel")
    _validate_unique_keys(labelled, "research panel")
    _validate_positive_finite(labelled, ["adjusted_open"], "research panel")
    return labelled


def _read_benchmark_frame(benchmark_open: pd.DataFrame) -> pd.DataFrame:
    benchmark = benchmark_open.copy()
    _require_columns(benchmark, ["trade_date", "adjusted_open"], "CSI 300 open")
    _parse_dates(benchmark, "CSI 300 open")
    if benchmark.duplicated(["trade_date"]).any():
        raise ValueError("CSI 300 open must have unique trade_date keys")
    _validate_positive_finite(benchmark, ["adjusted_open"], "CSI 300 open")
    return benchmark[["trade_date", "adjusted_open"]]


def _require_columns(frame: pd.DataFrame, columns: list[str], source: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{source} is missing required columns: {', '.join(missing)}")


def _parse_dates(frame: pd.DataFrame, source: str) -> None:
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    if frame["trade_date"].isna().any():
        raise ValueError(f"{source} contains an unparsable trade_date")


def _validate_unique_keys(frame: pd.DataFrame, source: str) -> None:
    if frame.duplicated(_PANEL_KEYS).any():
        raise ValueError(f"{source} must have unique (trade_date, security_id) keys")


def _validate_positive_finite(frame: pd.DataFrame, columns: list[str], source: str) -> None:
    values = frame[columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    if not (np.isfinite(values).all() and (values > 0).all()):
        raise ValueError(f"{source} must have finite positive {' and '.join(columns)}")
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="raise")


def _validated_horizons(horizons: Iterable[int]) -> tuple[int, ...]:
    values = tuple(horizons)
    if not values or any(not isinstance(horizon, (int, np.integer)) or horizon <= 0 for horizon in values):
        raise ValueError("horizons must contain positive integers")
    if len(set(values)) != len(values):
        raise ValueError("horizons must not contain duplicates")
    return tuple(sorted(int(horizon) for horizon in values))


def _as_date(value: str | pd.Timestamp, name: str) -> pd.Timestamp:
    date = pd.to_datetime(value, errors="coerce")
    if pd.isna(date):
        raise ValueError(f"{name} must be a parseable date")
    return pd.Timestamp(date)
