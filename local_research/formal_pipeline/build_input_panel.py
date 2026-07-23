#!/usr/bin/env python3
"""Build a frozen, point-in-time evaluator input panel from the local data lake."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAKE_PIPELINE = PROJECT_ROOT / "local_research" / "lake_pipeline"
sys.path.insert(0, str(LAKE_PIPELINE))

from common import DEFAULT_ROOT, parquet_sha256, run_id, write_json_immutable, write_parquet_immutable  # noqa: E402


STAGE_END_DATES = {
    "discovery": pd.Timestamp("2020-12-31"),
    "factor_validation": pd.Timestamp("2022-12-31"),
    "synthesis_validation": pd.Timestamp("2024-12-31"),
}

PANEL_COLUMNS = [
    "trade_date",
    "ts_code",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "pct_chg",
    "volume_shares",
    "amount_cny",
    "vwap",
    "total_share_shares",
    "float_share_shares",
    "adj_factor",
    "total_mv_cny",
    "circ_mv_cny",
    "turnover_rate_decimal",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "dv_ratio_decimal",
    "dv_ttm_decimal",
    "can_buy_open",
    "can_sell_open",
    "is_st",
]


def period_key(path: Path) -> tuple[int, int]:
    match = re.search(r"year=(\d{4})/month=(\d{2})", str(path))
    if match is None:
        raise ValueError(f"Cannot parse year/month from {path}")
    return int(match.group(1)), int(match.group(2))


def through_date(path: Path) -> str:
    match = re.search(r"part-through-(\d{8})-", path.name)
    return match.group(1) if match else "00000000"


def latest_monthly_silver(root: Path) -> dict[tuple[int, int], Path]:
    grouped: dict[tuple[int, int], list[Path]] = {}
    for path in (root / "silver" / "equity_daily").glob(
        "year=*/month=*/part-through-*.parquet"
    ):
        grouped.setdefault(period_key(path), []).append(path)
    return {
        key: max(
            paths,
            key=lambda path: (through_date(path), path.stat().st_mtime_ns, path.name),
        )
        for key, paths in grouped.items()
    }


def latest_passing_report(root: Path) -> tuple[Path, dict[str, Any]]:
    for path in reversed(sorted((root / "manifests").glob("data-quality-*.json"))):
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("status") == "pass":
            return path, report
    raise RuntimeError("No passing data-quality report is available")


def largest_parquet(paths: list[Path]) -> Path:
    if not paths:
        raise RuntimeError("No matching parquet files found")
    return max(paths, key=lambda path: pq.ParquetFile(path).metadata.num_rows)


def load_universe_snapshots(
    root: Path,
    index_code: str,
) -> tuple[Path, list[pd.Timestamp], dict[pd.Timestamp, set[str]]]:
    path = largest_parquet(
        list((root / "silver" / "universe_membership" / index_code).glob("index_weight-*.parquet"))
    )
    frame = pd.read_parquet(path, columns=["trade_date", "con_code"])
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], format="%Y%m%d", errors="coerce")
    frame["con_code"] = frame["con_code"].astype(str)
    frame = frame.dropna(subset=["trade_date"]).drop_duplicates(["trade_date", "con_code"])
    snapshots = sorted(frame["trade_date"].unique().tolist())
    members = {
        pd.Timestamp(date): set(group["con_code"])
        for date, group in frame.groupby("trade_date", sort=True)
    }
    return path, [pd.Timestamp(date) for date in snapshots], members


def active_universe_for_date(
    date: pd.Timestamp,
    snapshots: list[pd.Timestamp],
    members: dict[pd.Timestamp, set[str]],
) -> tuple[pd.Timestamp | None, set[str]]:
    position = bisect.bisect_right(snapshots, pd.Timestamp(date)) - 1
    if position < 0:
        return None, set()
    snapshot_date = snapshots[position]
    return snapshot_date, members[snapshot_date]


def attach_industry(frame: pd.DataFrame, industry: pd.DataFrame) -> pd.DataFrame:
    joined = frame.merge(
        industry[["ts_code", "l1_code", "l1_name", "in_date", "out_date"]],
        on="ts_code",
        how="left",
        validate="many_to_many",
    )
    active = joined.loc[
        joined["in_date"].notna()
        & (joined["trade_date"] >= joined["in_date"])
        & (joined["out_date"].isna() | (joined["trade_date"] <= joined["out_date"]))
    ].copy()
    counts = active.groupby(["trade_date", "ts_code"]).size()
    if counts.gt(1).any():
        raise RuntimeError(
            f"Found {int(counts.gt(1).sum())} rows with multiple active industry assignments"
        )
    industry_columns = active[["trade_date", "ts_code", "l1_code", "l1_name"]]
    return frame.merge(
        industry_columns,
        on=["trade_date", "ts_code"],
        how="left",
        validate="one_to_one",
    )


def label_files_from_report(report: dict[str, Any]) -> dict[tuple[int, int], Path]:
    label_summary = report.get("labels")
    if not label_summary or not label_summary.get("files"):
        raise RuntimeError("Passing quality report does not bind label files")
    result: dict[tuple[int, int], Path] = {}
    for raw_path in label_summary["files"]:
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"Bound label file does not exist: {path}")
        result[period_key(path)] = path
    return result


def attach_labels(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    labels = pd.read_parquet(
        path,
        columns=[
            "signal_date",
            "ts_code",
            "execution_date",
            "next_open_to_close",
            "next_close_to_close",
            "primary_label_available",
        ],
    ).rename(columns={"signal_date": "trade_date"})
    labels["trade_date"] = pd.to_datetime(labels["trade_date"])
    labels["ts_code"] = labels["ts_code"].astype(str)
    return frame.merge(labels, on=["trade_date", "ts_code"], how="left", validate="one_to_one")


def to_executor_schema(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.rename(
        columns={
            "trade_date": "dt",
            "ts_code": "Ticker",
            "volume_shares": "volume",
            "amount_cny": "amt",
            "total_share_shares": "total_shares",
            "float_share_shares": "free_float_shares",
            "adj_factor": "adjfactor",
            "total_mv_cny": "mkt_cap_ard",
            "circ_mv_cny": "float_mkt_cap",
            "turnover_rate_decimal": "turn",
            "dv_ratio_decimal": "dv_ratio",
            "dv_ttm_decimal": "dv_ttm",
        }
    )
    ordered = [
        "dt",
        "Ticker",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amt",
        "vwap",
        "pre_close",
        "pct_chg",
        "total_shares",
        "free_float_shares",
        "adjfactor",
        "mkt_cap_ard",
        "float_mkt_cap",
        "turn",
        "pe",
        "pe_ttm",
        "pb",
        "ps",
        "ps_ttm",
        "dv_ratio",
        "dv_ttm",
        "can_buy_open",
        "can_sell_open",
        "is_st",
        "universe_snapshot_date",
        "l1_code",
        "l1_name",
        "execution_date",
        "next_open_to_close",
        "next_close_to_close",
        "primary_label_available",
    ]
    return renamed[ordered].sort_values(["dt", "Ticker"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--universe-code", default="000300.SH")
    parser.add_argument("--start-date", default="20150101")
    parser.add_argument("--end-date", default="20221231")
    parser.add_argument(
        "--research-stage",
        choices=["discovery", "factor_validation", "synthesis_validation", "lockbox"],
        default="factor_validation",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    start = pd.Timestamp(args.start_date)
    end = pd.Timestamp(args.end_date)
    if start > end:
        raise ValueError("start-date must not be after end-date")
    stage_cap = STAGE_END_DATES.get(args.research_stage)
    if stage_cap is not None and end > stage_cap:
        raise ValueError(
            f"{args.research_stage} may not read dates after {stage_cap.date()}; got {end.date()}"
        )

    report_path, report = latest_passing_report(root)
    industry_path = Path(report["industry"]["path"])
    industry = pd.read_parquet(industry_path)
    industry["in_date"] = pd.to_datetime(industry["in_date"])
    industry["out_date"] = pd.to_datetime(industry["out_date"])
    universe_path, snapshots, members = load_universe_snapshots(root, args.universe_code)
    label_files = label_files_from_report(report)
    monthly_files = latest_monthly_silver(root)

    months = pd.period_range(start.to_period("M"), end.to_period("M"), freq="M")
    outputs: list[pd.DataFrame] = []
    source_files: list[Path] = []
    for position, period in enumerate(months, start=1):
        key = (period.year, period.month)
        source_path = monthly_files.get(key)
        label_path = label_files.get(key)
        if source_path is None or label_path is None:
            raise RuntimeError(f"Missing silver or label input for {period}")
        month = pd.read_parquet(source_path, columns=PANEL_COLUMNS)
        month["trade_date"] = pd.to_datetime(month["trade_date"])
        month["ts_code"] = month["ts_code"].astype(str)
        month = month.loc[month["trade_date"].between(start, end)].copy()

        selected: list[pd.DataFrame] = []
        for date, day in month.groupby("trade_date", sort=True):
            snapshot_date, active_members = active_universe_for_date(date, snapshots, members)
            if snapshot_date is None:
                continue
            active = day.loc[day["ts_code"].isin(active_members)].copy()
            active["universe_snapshot_date"] = snapshot_date
            selected.append(active)
        if not selected:
            continue
        month = pd.concat(selected, ignore_index=True)
        month = attach_industry(month, industry)
        month = attach_labels(month, label_path)
        if args.research_stage == "discovery":
            warmup = month["trade_date"] < pd.Timestamp("2016-01-01")
            month.loc[
                warmup,
                [
                    "execution_date",
                    "next_open_to_close",
                    "next_close_to_close",
                ],
            ] = pd.NA
            month.loc[warmup, "primary_label_available"] = False
        outputs.append(to_executor_schema(month))
        source_files.extend([source_path, label_path])
        print(
            f"[{position}/{len(months)}] {period}: {len(month):,} rows, "
            f"industry={month['l1_code'].notna().mean():.2%}",
            flush=True,
        )

    if not outputs:
        raise RuntimeError("No evaluator input rows were built")
    panel = pd.concat(outputs, ignore_index=True).drop_duplicates(["dt", "Ticker"])
    if panel.duplicated(["dt", "Ticker"]).any():
        raise RuntimeError("Evaluator input contains duplicate date/security keys")

    identity = "|".join(
        [
            report["snapshot_id"],
            args.universe_code,
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d"),
            args.research_stage,
        ]
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    output_dir = root / "gold" / "evaluator_inputs" / args.universe_code
    output_path = output_dir / (
        f"panel-{start:%Y%m%d}-{end:%Y%m%d}-{args.research_stage}-{digest}.parquet"
    )
    manifest_path = output_path.with_suffix(".manifest.json")
    if output_path.exists() and manifest_path.exists():
        print(f"Cached evaluator input: {output_path}")
        return
    write_parquet_immutable(panel, output_path)
    manifest = {
        "build_id": run_id(),
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "research_stage": args.research_stage,
        "label_visibility": (
            "2016-01-01_to_2020-12-31_only"
            if args.research_stage == "discovery"
            else "through_stage_end"
        ),
        "warmup_labels_masked": args.research_stage == "discovery",
        "factor_data_domains": [
            "market_price_volume",
            "turnover_size_liquidity",
            "valuation_dividend",
        ],
        "factor_fields": [
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            "pct_chg",
            "volume",
            "amt",
            "vwap",
            "turn",
            "pe",
            "pe_ttm",
            "pb",
            "ps",
            "ps_ttm",
            "dv_ratio",
            "dv_ttm",
        ],
        "range": [start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")],
        "universe_code": args.universe_code,
        "data_snapshot": report["snapshot_id"],
        "quality_report": str(report_path),
        "industry_path": str(industry_path),
        "industry_sha256": parquet_sha256(industry_path),
        "universe_path": str(universe_path),
        "universe_sha256": parquet_sha256(universe_path),
        "label_version": report["labels"]["label_version"],
        "output_path": str(output_path),
        "output_sha256": parquet_sha256(output_path),
        "rows": int(len(panel)),
        "dates": int(panel["dt"].nunique()),
        "securities": int(panel["Ticker"].nunique()),
        "first_date": panel["dt"].min().strftime("%Y-%m-%d"),
        "last_date": panel["dt"].max().strftime("%Y-%m-%d"),
        "industry_coverage": float(panel["l1_code"].notna().mean()),
        "primary_label_availability": float(panel["primary_label_available"].fillna(False).mean()),
        "source_file_count": len(set(source_files)),
        "schema": {column: str(dtype) for column, dtype in panel.dtypes.items()},
    }
    write_json_immutable(manifest, manifest_path)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
