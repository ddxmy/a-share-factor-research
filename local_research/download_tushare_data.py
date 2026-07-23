#!/usr/bin/env python3
"""Download a reproducible daily A-share panel for local factor research."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
import tushare as ts


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "local_research" / "data" / "tushare_a_share_daily.parquet"
PRICE_FIELDS = "ts_code,trade_date,open,high,low,close,pre_close,vol,amount,pct_chg"
BASIC_FIELDS = "ts_code,trade_date,turnover_rate,total_mv,circ_mv"
ADJ_FIELDS = "ts_code,trade_date,adj_factor"


def _is_a_share(code: str) -> bool:
    return len(code) >= 1 and code[0] in {"0", "3", "4", "6", "8"}


def _request(call, retries: int = 3) -> pd.DataFrame:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return call()
        except Exception as exc:  # Retry only transient API failures.
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Tushare request failed after {retries} attempts: {last_error}")


def _build_day(pro, trade_date: str) -> pd.DataFrame:
    daily = _request(lambda: pro.daily(trade_date=trade_date, fields=PRICE_FIELDS))
    basic = _request(lambda: pro.daily_basic(trade_date=trade_date, fields=BASIC_FIELDS))
    adj = _request(lambda: pro.adj_factor(trade_date=trade_date, fields=ADJ_FIELDS))
    if daily.empty:
        return pd.DataFrame()
    frame = daily.merge(basic, on=["ts_code", "trade_date"], how="inner").merge(
        adj, on=["ts_code", "trade_date"], how="inner"
    )
    frame = frame.loc[frame["ts_code"].map(_is_a_share)].copy()
    # Tushare: vol = hands; amount = thousand CNY; market values = ten-thousand CNY.
    frame["volume"] = frame["vol"] * 100.0
    frame["amt"] = frame["amount"] * 1000.0
    frame["vwap"] = frame["amt"] / frame["volume"].replace(0, pd.NA)
    frame["mkt_cap_ard"] = frame["total_mv"] * 10_000.0
    frame["total_shares"] = frame["mkt_cap_ard"] / frame["close"].replace(0, pd.NA)
    frame["free_float_shares"] = (frame["circ_mv"] * 10_000.0) / frame["close"].replace(0, pd.NA)
    frame["turn"] = frame["turnover_rate"] / 100.0
    frame = frame.rename(columns={"ts_code": "Ticker", "trade_date": "dt"})
    frame["dt"] = pd.to_datetime(frame["dt"])
    return frame[[
        "dt", "Ticker", "open", "high", "low", "close", "volume", "amt", "vwap",
        "pre_close", "pct_chg", "total_shares", "free_float_shares", "adj_factor",
        "mkt_cap_ard", "turn",
    ]].rename(columns={"adj_factor": "adjfactor"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Tushare A-share panel for local factor backtests")
    parser.add_argument("--start-date", default="20230103")
    parser.add_argument("--end-date", default="20250630")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--pause", type=float, default=0.12, help="Pause after each API call in seconds")
    args = parser.parse_args()

    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is not set. Export it in your shell and retry.")
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    pro = ts.pro_api(token)
    calendar = _request(lambda: pro.trade_cal(
        exchange="", start_date=args.start_date.replace("-", ""), end_date=args.end_date.replace("-", ""),
        is_open="1", fields="cal_date,is_open",
    )).sort_values("cal_date")
    if calendar.empty:
        raise RuntimeError("No open trading days returned for the requested date range")

    chunks: list[pd.DataFrame] = []
    failures: list[dict] = []
    dates = calendar["cal_date"].tolist()
    for position, trade_date in enumerate(dates, start=1):
        try:
            chunks.append(_build_day(pro, trade_date))
        except Exception as exc:
            failures.append({"trade_date": trade_date, "error": str(exc)})
        if position % 25 == 0 or position == len(dates):
            print(f"Downloaded {position}/{len(dates)} trading days; failures={len(failures)}", flush=True)
        time.sleep(args.pause)

    panel = pd.concat([x for x in chunks if not x.empty], ignore_index=True)
    panel = panel.drop_duplicates(["dt", "Ticker"]).sort_values(["dt", "Ticker"])
    panel.to_parquet(output, index=False)
    manifest = {
        "source": ["Tushare daily", "Tushare daily_basic", "Tushare adj_factor"],
        "requested_date_range": [args.start_date, args.end_date],
        "downloaded_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "rows": len(panel), "tickers": int(panel["Ticker"].nunique()),
        "dates": int(panel["dt"].nunique()), "columns": list(panel.columns), "failures": failures,
    }
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(panel):,} rows to {output}")
    print(f"Saved manifest to {manifest_path}")
    if failures:
        print("WARNING: output is incomplete; inspect failures in the manifest.")


if __name__ == "__main__":
    main()
