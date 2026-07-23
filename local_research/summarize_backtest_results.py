#!/usr/bin/env python3
"""Create a unified factor summary from per-factor daily backtest files."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def annual_return(x: pd.Series) -> float:
    return float((1 + x).prod() ** (252 / len(x)) - 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    args = parser.parse_args()
    root = Path(args.results_dir)
    rows = []
    for path in sorted(root.glob("factor_*_full_daily.csv")):
        frame = pd.read_csv(path)
        ret, ic = frame["net_long_short_return"].dropna(), frame["ic"].dropna()
        wealth = (1 + ret).cumprod()
        rows.append({
            "factor_id": path.name.removeprefix("factor_").removesuffix("_full_daily.csv"),
            "observations": len(ret), "mean_ic": ic.mean(),
            "icir": ic.mean() / (ic.std(ddof=1) + 1e-12) * np.sqrt(252),
            "annual_return": annual_return(ret),
            "annual_volatility": ret.std(ddof=1) * np.sqrt(252),
            "sharpe": ret.mean() / (ret.std(ddof=1) + 1e-12) * np.sqrt(252),
            "max_drawdown": (wealth / wealth.cummax() - 1).min(),
            "average_daily_turnover": frame["turnover"].mean(), "total_cost": frame["cost"].sum(),
        })
    summary = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    summary.to_csv(root / "factor_summary_all_completed.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
