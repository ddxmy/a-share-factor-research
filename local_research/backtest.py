#!/usr/bin/env python3
"""Local, reproducible T-1 cross-sectional backtest for the factor library.

This is intentionally independent from the legacy Linux-only ``run_factor``
and ``FactorTest`` extensions.  It reuses the project's formula executor and
factor-library JSON, while reporting standard research metrics locally.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from evaluation.evaluator import FormulaExecutor  # noqa: E402


@dataclass
class BacktestResult:
    factor_id: str
    factor_name: str
    formula: str
    in_sample: bool
    observations: int
    mean_ic: float
    icir: float
    ic_positive_ratio: float
    annual_return: float
    annual_volatility: float
    sharpe: float
    max_drawdown: float
    average_daily_turnover: float
    total_cost: float
    average_universe_size: float
    average_signal_coverage: float
    monthly_ic_positive_ratio: float
    group_return_monotonicity: float


def _parse_date(value: str | None) -> int | None:
    return int(value.replace("-", "")) if value else None


def _load_library(path: Path) -> list[dict]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError(f"No factor records found in {path}")
    return records


def _load_script_factors(script_dir: Path) -> list[dict]:
    """Read active factor definitions from scripts without importing legacy code.

    Legacy scripts call an unavailable server-side trading-calendar helper.  Their
    ``FORMULA`` constants are the canonical, executable factor definitions, so
    AST parsing preserves the definition while keeping local research offline.
    """
    records: list[dict] = []
    for path in sorted(script_dir.rglob("*.py")):
        if "_retired" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        constants = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {"FACTOR_NAME", "FORMULA"}
        }
        if {"FACTOR_NAME", "FORMULA"}.issubset(constants):
            records.append({
                "factor_id": path.stem,
                "factor_name": constants["FACTOR_NAME"],
                "formula": constants["FORMULA"],
                "script_path": str(path.relative_to(PROJECT_ROOT)),
            })
    if not records:
        raise ValueError(f"No active factor scripts with FACTOR_NAME/FORMULA found in {script_dir}")
    return records


def _annual_return(daily_returns: pd.Series) -> float:
    return float((1 + daily_returns).prod() ** (252 / len(daily_returns)) - 1)


def _max_drawdown(daily_returns: pd.Series) -> float:
    wealth = (1 + daily_returns).cumprod()
    return float((wealth / wealth.cummax() - 1).min())


def _load_adjusted_close(path: str) -> pd.DataFrame:
    """Load actual adjusted close for P&L, without board-limit rescaling."""
    market = pd.read_parquet(path, columns=["dt", "Ticker", "close", "adjfactor"])
    if not {"dt", "Ticker"}.issubset(market.columns):
        market = market.reset_index()
    market["dt"] = pd.to_datetime(market["dt"])
    market["adjusted_close"] = market["close"] * market["adjfactor"].fillna(1.0)
    return market.pivot(index="dt", columns="Ticker", values="adjusted_close").sort_index()


def _load_universe_mask(path: str, dates: pd.Index, tickers: pd.Index) -> tuple[pd.DataFrame, dict]:
    """Build an as-of membership mask from dated index-weight snapshots.

    A snapshot only becomes usable on its own ``trade_date``.  Dates before the
    first snapshot remain outside the universe, which prevents month-end data
    from leaking backward into earlier dates.
    """
    raw = pd.read_parquet(path)
    required = {"trade_date", "con_code"}
    if not required.issubset(raw.columns):
        raise ValueError(f"Universe file must contain {sorted(required)}")
    raw = raw.copy()
    raw["trade_date"] = pd.to_datetime(raw["trade_date"])
    raw["con_code"] = raw["con_code"].astype(str)
    raw = raw.drop_duplicates(["trade_date", "con_code"]).sort_values(["trade_date", "con_code"])
    snapshots = raw["trade_date"].drop_duplicates().sort_values().tolist()
    if not snapshots:
        raise ValueError(f"No constituent snapshots found in {path}")
    members = {date: set(group["con_code"]) for date, group in raw.groupby("trade_date")}
    mask = pd.DataFrame(False, index=pd.DatetimeIndex(dates), columns=tickers, dtype=bool)
    ticker_set = set(tickers)
    snapshot_position = -1
    for date in mask.index:
        while snapshot_position + 1 < len(snapshots) and snapshots[snapshot_position + 1] <= date:
            snapshot_position += 1
        if snapshot_position < 0:
            continue
        active = list(members[snapshots[snapshot_position]] & ticker_set)
        if active:
            mask.loc[date, active] = True
    counts = mask.sum(axis=1)
    metadata = {
        "source": str(Path(path).resolve()),
        "first_snapshot": snapshots[0].strftime("%Y-%m-%d"),
        "last_snapshot": snapshots[-1].strftime("%Y-%m-%d"),
        "snapshot_count": len(snapshots),
        "covered_dates": int((counts > 0).sum()),
        "average_members": float(counts[counts > 0].mean()) if (counts > 0).any() else 0.0,
    }
    return mask, metadata


def _factor_metrics(
    record: dict,
    signal: pd.DataFrame,
    forward_return: pd.DataFrame,
    split_date: pd.Timestamp | None,
    cost_bps: float,
    quantiles: int,
    universe_size: pd.Series,
) -> tuple[BacktestResult, pd.DataFrame]:
    # A factor observed after the t close predicts the adjusted close-to-close
    # return from t to t+1.  The target is already forward-shifted, so applying
    # another lag to the signal would introduce an unintended extra day.
    aligned_signal = signal
    daily_ic: dict[pd.Timestamp, float] = {}
    portfolio_returns: dict[pd.Timestamp, float] = {}
    weights: dict[pd.Timestamp, pd.Series] = {}
    group_returns: dict[pd.Timestamp, dict[str, float]] = {}
    signal_counts: dict[pd.Timestamp, int] = {}

    for date in aligned_signal.index:
        frame = pd.concat(
            [aligned_signal.loc[date].rename("signal"), forward_return.loc[date].rename("return")],
            axis=1,
        ).dropna()
        if len(frame) < max(20, quantiles * 2):
            continue
        if frame["signal"].nunique(dropna=True) < 2:
            continue
        signal_counts[date] = len(frame)
        daily_ic[date] = frame["signal"].corr(frame["return"], method="spearman")
        try:
            bucket = pd.qcut(frame["signal"], q=quantiles, labels=False, duplicates="drop")
        except ValueError:
            continue
        if bucket.nunique() < 2:
            continue
        group_returns[date] = {
            f"group_{int(group) + 1}_return": float(frame.loc[bucket == group, "return"].mean())
            for group in sorted(bucket.dropna().unique())
        }
        long_names = bucket.index[bucket == bucket.max()]
        short_names = bucket.index[bucket == bucket.min()]
        weight = pd.Series(0.0, index=frame.index)
        weight.loc[long_names] = 1.0 / len(long_names)
        weight.loc[short_names] = -1.0 / len(short_names)
        weights[date] = weight
        portfolio_returns[date] = float((weight * frame["return"]).sum())

    gross = pd.Series(portfolio_returns, dtype=float).sort_index()
    ic = pd.Series(daily_ic, dtype=float).reindex(gross.index)
    if gross.empty:
        raise ValueError(f"{record['factor_name']}: no usable daily cross-sections")

    turnover = pd.Series(index=gross.index, dtype=float)
    previous = pd.Series(dtype=float)
    for date, current in weights.items():
        all_names = previous.index.union(current.index)
        turnover.loc[date] = (current.reindex(all_names, fill_value=0) - previous.reindex(all_names, fill_value=0)).abs().sum() / 2
        previous = current
    cost = turnover * cost_bps / 10_000
    net = gross - cost
    active = net.index >= split_date if split_date is not None else pd.Series(True, index=net.index)
    selected_net, selected_ic, selected_turnover, selected_cost = net[active], ic[active], turnover[active], cost[active]
    if len(selected_net) < 2:
        raise ValueError(f"{record['factor_name']}: selected period contains fewer than two observations")

    annual_volatility = float(selected_net.std(ddof=1) * np.sqrt(252))
    monthly_ic = selected_ic.groupby(selected_ic.index.to_period("M")).mean()
    group_daily = pd.DataFrame.from_dict(group_returns, orient="index").sort_index()
    selected_groups = group_daily.reindex(selected_net.index)
    average_group_returns = selected_groups.mean().dropna()
    if len(average_group_returns) >= 2:
        group_numbers = pd.Series(range(1, len(average_group_returns) + 1), index=average_group_returns.index)
        monotonicity = float(group_numbers.corr(average_group_returns, method="spearman"))
    else:
        monotonicity = float("nan")
    selected_universe = universe_size.reindex(selected_net.index)
    selected_signal_counts = pd.Series(signal_counts, dtype=float).reindex(selected_net.index)
    coverage = selected_signal_counts / selected_universe.replace(0, np.nan)
    result = BacktestResult(
        factor_id=str(record["factor_id"]), factor_name=record["factor_name"], formula=record["formula"],
        in_sample=bool(split_date is not None and selected_net.index.max() < split_date), observations=len(selected_net),
        mean_ic=float(selected_ic.mean()), icir=float(selected_ic.mean() / (selected_ic.std(ddof=1) + 1e-12) * np.sqrt(252)),
        ic_positive_ratio=float((selected_ic > 0).mean()), annual_return=_annual_return(selected_net),
        annual_volatility=annual_volatility, sharpe=float(selected_net.mean() / (selected_net.std(ddof=1) + 1e-12) * np.sqrt(252)),
        max_drawdown=_max_drawdown(selected_net), average_daily_turnover=float(selected_turnover.mean()), total_cost=float(selected_cost.sum()),
        average_universe_size=float(selected_universe.mean()), average_signal_coverage=float(coverage.mean()),
        monthly_ic_positive_ratio=float((monthly_ic > 0).mean()), group_return_monotonicity=monotonicity,
    )
    daily = pd.DataFrame({"gross_long_short_return": gross, "turnover": turnover, "cost": cost, "net_long_short_return": net, "ic": ic})
    daily = daily.join(group_daily, how="left")
    daily["universe_size"] = universe_size.reindex(daily.index)
    daily["signal_count"] = pd.Series(signal_counts, dtype=float).reindex(daily.index)
    daily["signal_coverage"] = daily["signal_count"] / daily["universe_size"].replace(0, np.nan)
    return result, daily


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest FactorMiner scripts with a local parquet file")
    parser.add_argument("--market-data", required=True, help="Local parquet containing market data")
    parser.add_argument("--start-date", help="First evaluation date, YYYYMMDD or YYYY-MM-DD")
    parser.add_argument("--end-date", help="Last evaluation date, YYYYMMDD or YYYY-MM-DD")
    parser.add_argument("--split-date", help="Optional OOS start date; emits IS/OOS summaries")
    parser.add_argument("--cost-bps", type=float, default=10.0, help="One-way transaction cost in bps (default: 10)")
    parser.add_argument("--quantiles", type=int, default=5, help="Cross-sectional buckets (default: 5)")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "local_research" / "results"))
    parser.add_argument("--source", choices=["scripts", "library"], default="scripts", help="Factor-definition source (default: active scripts)")
    parser.add_argument("--factor", action="append", help="Optional factor name or script stem; may be given repeatedly")
    parser.add_argument("--universe-membership", help="Parquet from download_hs300_membership.py")
    parser.add_argument("--skip-factor-correlation", action="store_true", help="Skip the factor rank-correlation matrix")
    args = parser.parse_args()

    start, end, split = _parse_date(args.start_date), _parse_date(args.end_date), _parse_date(args.split_date)
    output_dir = Path(args.output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    records = (_load_script_factors(PROJECT_ROOT / "factor_script") if args.source == "scripts"
               else _load_library(PROJECT_ROOT / "data" / "factor_library.json"))
    if args.factor:
        selected = set(args.factor)
        records = [r for r in records if str(r["factor_id"]) in selected or r["factor_name"] in selected]
    if not records:
        raise ValueError("No selected factors found in data/factor_library.json")

    # Load the entire file before applying the evaluation-date mask so rolling
    # formulas retain their pre-sample lookback history.
    executor = FormulaExecutor(args.market_data, start_date=20120101, end_date=end or 20250706)
    close = _load_adjusted_close(args.market_data).reindex(
        index=executor.md["index"], columns=executor.columns,
    )
    forward_return = close.pct_change(fill_method=None).shift(-1)
    if args.universe_membership:
        universe_mask, universe_metadata = _load_universe_mask(
            args.universe_membership, executor.md["index"], executor.columns,
        )
    else:
        universe_mask = pd.DataFrame(True, index=executor.md["index"], columns=executor.columns, dtype=bool)
        universe_metadata = {"source": "all securities in market data", "covered_dates": len(universe_mask)}
    (output_dir / "universe_metadata.json").write_text(
        json.dumps(universe_metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summaries: list[dict] = []
    failures: list[dict] = []
    signal_rank_vectors: dict[str, np.ndarray] = {}
    for record in records:
        try:
            signal = executor.compute(record["formula"])
            base_mask = pd.Series(True, index=signal.index)
            if start:
                base_mask &= signal.index >= pd.Timestamp(str(start))
            if end:
                base_mask &= signal.index <= pd.Timestamp(str(end))
            base_universe = universe_mask.reindex(index=signal.index, columns=signal.columns, fill_value=False)
            active_columns = base_universe.loc[base_mask].any(axis=0)
            if not args.skip_factor_correlation and active_columns.any():
                ranked = signal.loc[base_mask, active_columns].where(
                    base_universe.loc[base_mask, active_columns]
                ).rank(axis=1, pct=True)
                signal_rank_vectors[str(record["factor_id"])] = ranked.to_numpy(dtype=np.float32).ravel()
            periods = [("full", None)]
            if split:
                periods = [("in_sample", pd.Timestamp(str(split))), ("out_of_sample", None)]
            for label, cutoff in periods:
                if label == "in_sample":
                    mask = base_mask & (signal.index < cutoff)
                elif label == "out_of_sample" and split:
                    mask = base_mask & (signal.index >= pd.Timestamp(str(split)))
                else:
                    mask = base_mask
                period_universe = base_universe.loc[mask]
                period_signal = signal.loc[mask].where(period_universe)
                period_return = forward_return.loc[mask].where(period_universe)
                result, daily = _factor_metrics(
                    record, period_signal, period_return, None, args.cost_bps, args.quantiles,
                    period_universe.sum(axis=1),
                )
                row = asdict(result); row["in_sample"] = label == "in_sample"; row["period"] = label; summaries.append(row)
                daily.to_csv(output_dir / f"factor_{record['factor_id']}_{label}_daily.csv", index_label="dt")
        except Exception as exc:  # One bad formula should not hide other factors.
            failures.append({"factor_id": record.get("factor_id"), "factor_name": record.get("factor_name"), "error": str(exc)})

    correlation = pd.DataFrame()
    if signal_rank_vectors:
        correlation = pd.DataFrame(signal_rank_vectors).corr(min_periods=200)
        correlation.to_csv(output_dir / "factor_signal_rank_correlation.csv", index_label="factor_id")
    summary = pd.DataFrame(summaries)
    if not summary.empty and not correlation.empty:
        absolute = correlation.abs().copy()
        np.fill_diagonal(absolute.values, np.nan)
        max_corr = absolute.max(axis=1).rename("max_abs_factor_correlation")
        summary = summary.merge(max_corr, left_on="factor_id", right_index=True, how="left")
    if not summary.empty:
        summary = summary.sort_values(["period", "sharpe"], ascending=[True, False])
    summary.to_csv(output_dir / "factor_summary.csv", index=False)
    (output_dir / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    print(summary.to_string(index=False) if not summary.empty else "No factor completed successfully.")
    print(f"Saved research outputs to: {output_dir}")
    if failures:
        print(f"{len(failures)} factor(s) failed; see {output_dir / 'failures.json'}")


if __name__ == "__main__":
    main()
