#!/usr/bin/env python3
"""Orient factors using training IC, apply gates, and cluster redundant signals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def _annual_return(returns: pd.Series) -> float:
    return float((1 + returns).prod() ** (252 / len(returns)) - 1)


def _max_drawdown(returns: pd.Series) -> float:
    wealth = (1 + returns).cumprod()
    return float((wealth / wealth.cummax() - 1).min())


def _period_metrics(path: Path, direction: int) -> dict:
    daily = pd.read_csv(path, parse_dates=["dt"]).set_index("dt")
    ic = direction * daily["ic"]
    gross = direction * daily["gross_long_short_return"]
    net = gross - daily["cost"]
    monthly_ic = ic.groupby(ic.index.to_period("M")).mean()
    volatility = net.std(ddof=1) * np.sqrt(252)
    return {
        "observations": int(net.notna().sum()),
        "oriented_mean_ic": float(ic.mean()),
        "oriented_icir": float(ic.mean() / (ic.std(ddof=1) + 1e-12) * np.sqrt(252)),
        "oriented_monthly_ic_positive_ratio": float((monthly_ic > 0).mean()),
        "oriented_annual_return": _annual_return(net.dropna()),
        "oriented_annual_volatility": float(volatility),
        "oriented_sharpe": float(net.mean() / (net.std(ddof=1) + 1e-12) * np.sqrt(252)),
        "oriented_max_drawdown": _max_drawdown(net.dropna()),
        "average_daily_turnover": float(daily["turnover"].mean()),
        "total_cost": float(daily["cost"].sum()),
        "average_signal_coverage": float(daily["signal_coverage"].mean()),
    }


def _components(ids: list[str], correlation: pd.DataFrame, threshold: float) -> list[list[str]]:
    remaining = set(ids)
    components: list[list[str]] = []
    while remaining:
        root = min(remaining)
        remaining.remove(root)
        component = {root}
        frontier = [root]
        while frontier:
            current = frontier.pop()
            neighbours = {
                other for other in list(remaining)
                if current in correlation.index and other in correlation.columns
                and pd.notna(correlation.loc[current, other])
                and abs(correlation.loc[current, other]) >= threshold
            }
            remaining -= neighbours
            component |= neighbours
            frontier.extend(neighbours)
        components.append(sorted(component))
    return sorted(components, key=lambda group: (-len(group), group[0]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit HS300 factor backtest results")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--min-train-ic", type=float, default=0.02)
    parser.add_argument("--min-validation-ic", type=float, default=0.02)
    parser.add_argument("--min-monthly-hit-rate", type=float, default=0.5)
    parser.add_argument("--min-coverage", type=float, default=0.95)
    parser.add_argument("--corr-threshold", type=float, default=0.8)
    args = parser.parse_args()

    root = Path(args.results_dir)
    raw = pd.read_csv(root / "factor_summary.csv")
    train = raw.loc[raw["period"] == "in_sample"].set_index("factor_id")
    validation = raw.loc[raw["period"] == "out_of_sample"].set_index("factor_id")
    common = sorted(set(train.index) & set(validation.index))
    rows: list[dict] = []

    for factor_id in common:
        train_row = train.loc[factor_id]
        direction = 1 if train_row["mean_ic"] >= 0 else -1
        base = {
            "factor_id": factor_id,
            "factor_name": train_row["factor_name"],
            "formula": train_row["formula"],
            "train_direction": direction,
            "max_abs_factor_correlation": train_row.get("max_abs_factor_correlation", np.nan),
        }
        for period, label in (("in_sample", "train"), ("out_of_sample", "validation")):
            metrics = _period_metrics(root / f"factor_{factor_id}_{period}_daily.csv", direction)
            base.update({f"{label}_{key}": value for key, value in metrics.items()})
        base["direction_consistent"] = base["validation_oriented_mean_ic"] > 0
        gates = {
            "train_ic": base["train_oriented_mean_ic"] >= args.min_train_ic,
            "validation_ic": base["validation_oriented_mean_ic"] >= args.min_validation_ic,
            "direction": base["direction_consistent"],
            "monthly_hit_rate": base["validation_oriented_monthly_ic_positive_ratio"] >= args.min_monthly_hit_rate,
            "coverage": min(base["train_average_signal_coverage"], base["validation_average_signal_coverage"]) >= args.min_coverage,
        }
        base["passes_stability_gates"] = all(gates.values())
        base["failed_gates"] = ",".join(name for name, passed in gates.items() if not passed)
        rows.append(base)

    audit = pd.DataFrame(rows)
    correlation = pd.read_csv(root / "factor_signal_rank_correlation.csv", index_col=0)
    correlation.index = correlation.index.astype(str)
    correlation.columns = correlation.columns.astype(str)
    selected_ids = audit.loc[audit["passes_stability_gates"], "factor_id"].astype(str).tolist()
    components = _components(selected_ids, correlation, args.corr_threshold)
    clusters: list[dict] = []
    for cluster_id, members in enumerate(components, start=1):
        candidates = audit[audit["factor_id"].astype(str).isin(members)].copy()
        candidates["robust_ic"] = candidates[["train_oriented_mean_ic", "validation_oriented_mean_ic"]].min(axis=1)
        candidates = candidates.sort_values(
            ["robust_ic", "validation_oriented_sharpe", "validation_average_daily_turnover"],
            ascending=[False, False, True],
        )
        representative = str(candidates.iloc[0]["factor_id"])
        clusters.append({
            "cluster_id": cluster_id,
            "members": members,
            "representative": representative,
            "size": len(members),
        })
        audit.loc[audit["factor_id"].astype(str).isin(members), "redundancy_cluster"] = cluster_id
        audit.loc[audit["factor_id"].astype(str).isin(members), "cluster_representative"] = representative

    audit = audit.sort_values(
        ["passes_stability_gates", "validation_oriented_mean_ic"], ascending=[False, False]
    )
    audit.to_csv(root / "factor_oriented_audit.csv", index=False)
    report = {
        "direction_rule": "sign of in-sample mean Rank IC; frozen for validation",
        "gates": {
            "min_train_ic": args.min_train_ic,
            "min_validation_ic": args.min_validation_ic,
            "min_validation_monthly_hit_rate": args.min_monthly_hit_rate,
            "min_signal_coverage": args.min_coverage,
        },
        "correlation_threshold": args.corr_threshold,
        "evaluated_factors": len(audit),
        "stable_factors_before_dedup": int(audit["passes_stability_gates"].sum()),
        "redundancy_clusters": clusters,
        "representatives": [item["representative"] for item in clusters],
    }
    (root / "factor_audit_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    display = audit.loc[audit["passes_stability_gates"], [
        "factor_id", "train_direction", "train_oriented_mean_ic", "validation_oriented_mean_ic",
        "validation_oriented_icir", "validation_oriented_sharpe", "validation_average_daily_turnover",
        "max_abs_factor_correlation", "redundancy_cluster", "cluster_representative",
    ]]
    print(display.to_string(index=False))
    print(f"Stable factors before dedup: {report['stable_factors_before_dedup']}")
    print(f"Representatives after {args.corr_threshold:.2f} correlation clustering: {len(clusters)}")
    print(f"Saved audit outputs to {root}")


if __name__ == "__main__":
    main()
