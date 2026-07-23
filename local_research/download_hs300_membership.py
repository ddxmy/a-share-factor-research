#!/usr/bin/env python3
"""Download point-in-time CSI 300 constituent-weight snapshots from Tushare."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
import tushare as ts


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "local_research" / "data" / "universe" / "hs300_index_weight.parquet"


def _request(call, retries: int = 3) -> pd.DataFrame:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return call()
        except Exception as exc:
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Tushare request failed after {retries} attempts: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download monthly CSI 300 constituent weights")
    parser.add_argument("--start-date", required=True, help="First backtest date, YYYYMMDD")
    parser.add_argument("--end-date", required=True, help="Last backtest date, YYYYMMDD")
    parser.add_argument("--index-code", default="000300.SH")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--pause", type=float, default=0.25)
    args = parser.parse_args()

    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is not set. Export it in your shell and retry.")
    start = pd.Timestamp(args.start_date)
    end = pd.Timestamp(args.end_date)
    if start > end:
        raise ValueError("start-date must not be after end-date")

    # The first backtest month needs the previous month's snapshot so that the
    # as-of join never looks forward to a month-end constituent list.
    first_period = start.to_period("M") - 1
    last_period = end.to_period("M")
    periods = pd.period_range(first_period, last_period, freq="M")
    pro = ts.pro_api(token)
    chunks: list[pd.DataFrame] = []
    failures: list[dict] = []

    for position, period in enumerate(periods, start=1):
        month_start = period.start_time.strftime("%Y%m%d")
        month_end = period.end_time.strftime("%Y%m%d")
        try:
            frame = _request(lambda: pro.index_weight(
                index_code=args.index_code,
                start_date=month_start,
                end_date=month_end,
            ))
            if frame.empty:
                failures.append({"month": str(period), "error": "empty result"})
            else:
                chunks.append(frame)
        except Exception as exc:
            failures.append({"month": str(period), "error": str(exc)})
        print(f"Downloaded {position}/{len(periods)} monthly snapshots; failures={len(failures)}", flush=True)
        time.sleep(args.pause)

    if not chunks:
        raise RuntimeError("No CSI 300 constituent snapshots were downloaded")
    panel = pd.concat(chunks, ignore_index=True)
    required = {"index_code", "con_code", "trade_date", "weight"}
    if not required.issubset(panel.columns):
        raise ValueError(f"index_weight response is missing fields: {sorted(required - set(panel.columns))}")
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    panel = panel.drop_duplicates(["index_code", "trade_date", "con_code"]).sort_values(
        ["trade_date", "con_code"]
    )

    snapshot_quality = (
        panel.groupby("trade_date")
        .agg(member_count=("con_code", "nunique"), weight_sum=("weight", "sum"))
        .reset_index()
    )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(output, index=False)
    manifest = {
        "source": "Tushare index_weight",
        "index_code": args.index_code,
        "requested_backtest_range": [args.start_date, args.end_date],
        "requested_months_including_prior": [str(first_period), str(last_period)],
        "downloaded_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "rows": len(panel),
        "snapshots": int(panel["trade_date"].nunique()),
        "unique_members": int(panel["con_code"].nunique()),
        "columns": list(panel.columns),
        "snapshot_quality": [
            {
                "trade_date": row.trade_date.strftime("%Y-%m-%d"),
                "member_count": int(row.member_count),
                "weight_sum": float(row.weight_sum),
            }
            for row in snapshot_quality.itertuples(index=False)
        ],
        "failures": failures,
    }
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(panel):,} rows across {panel['trade_date'].nunique()} snapshots to {output}")
    print(f"Saved manifest to {manifest_path}")
    if failures:
        print("WARNING: membership output is incomplete; inspect failures in the manifest.")


if __name__ == "__main__":
    main()
