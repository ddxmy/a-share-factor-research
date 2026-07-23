#!/usr/bin/env python3
"""Build a point-in-time liquid all-A transfer panel.

Universe definition: the top 1,000 securities each date by trailing 20-observation
median trading amount, with at least 10 observations. The ranking uses data
available through the signal-date close and is used only as a transfer universe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from build_input_panel import (
    PANEL_COLUMNS,
    attach_industry,
    attach_labels,
    label_files_from_report,
    latest_monthly_silver,
    latest_passing_report,
    period_key,
    to_executor_schema,
)

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "local_research" / "lake_pipeline"))

from common import DEFAULT_ROOT, parquet_sha256, run_id, write_json_immutable, write_parquet_immutable  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--start-date", default="20150101")
    parser.add_argument("--end-date", default="20221231")
    parser.add_argument("--top-n", type=int, default=1000)
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--min-observations", type=int, default=10)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    start = pd.Timestamp(args.start_date)
    end = pd.Timestamp(args.end_date)
    if end > pd.Timestamp("2022-12-31"):
        raise ValueError("factor-validation transfer panel may not read after 2022-12-31")
    if args.top_n <= 0 or args.window <= 1 or args.min_observations <= 0:
        raise ValueError("Invalid liquid-universe parameters")

    report_path, report = latest_passing_report(root)
    industry_path = Path(report["industry"]["path"])
    industry = pd.read_parquet(industry_path)
    industry["in_date"] = pd.to_datetime(industry["in_date"])
    industry["out_date"] = pd.to_datetime(industry["out_date"])
    monthly_files = latest_monthly_silver(root)
    label_files = label_files_from_report(report)
    periods = list(pd.period_range(start.to_period("M"), end.to_period("M"), freq="M"))

    outputs: list[pd.DataFrame] = []
    source_files: set[Path] = set()
    for position, period in enumerate(periods, start=1):
        key = (period.year, period.month)
        current_path = monthly_files.get(key)
        label_path = label_files.get(key)
        if current_path is None or label_path is None:
            raise RuntimeError(f"Missing silver or label input for {period}")

        history_periods = [period - 2, period - 1, period]
        history_paths = [
            monthly_files[(item.year, item.month)]
            for item in history_periods
            if (item.year, item.month) in monthly_files
        ]
        history = pd.concat(
            [
                pd.read_parquet(path, columns=["trade_date", "ts_code", "amount_cny"])
                for path in history_paths
            ],
            ignore_index=True,
        )
        history["trade_date"] = pd.to_datetime(history["trade_date"])
        history["ts_code"] = history["ts_code"].astype(str)
        history = history.sort_values(["ts_code", "trade_date"])
        history["trailing_median_amount"] = (
            history.groupby("ts_code", sort=False)["amount_cny"]
            .rolling(args.window, min_periods=args.min_observations)
            .median()
            .reset_index(level=0, drop=True)
        )
        history = history.loc[
            history["trade_date"].dt.to_period("M").eq(period),
            ["trade_date", "ts_code", "trailing_median_amount"],
        ]

        month = pd.read_parquet(current_path, columns=PANEL_COLUMNS)
        month["trade_date"] = pd.to_datetime(month["trade_date"])
        month["ts_code"] = month["ts_code"].astype(str)
        month = month.loc[month["trade_date"].between(start, end)].merge(
            history,
            on=["trade_date", "ts_code"],
            how="left",
            validate="one_to_one",
        )
        selected = (
            month.dropna(subset=["trailing_median_amount"])
            .sort_values(
                ["trade_date", "trailing_median_amount", "ts_code"],
                ascending=[True, False, True],
            )
            .groupby("trade_date", sort=True, as_index=False)
            .head(args.top_n)
            .drop(columns="trailing_median_amount")
        )
        selected["universe_snapshot_date"] = selected["trade_date"]
        selected = attach_industry(selected, industry)
        selected = attach_labels(selected, label_path)
        outputs.append(to_executor_schema(selected))
        source_files.update(history_paths)
        source_files.add(label_path)
        print(
            f"[{position}/{len(periods)}] {period}: {len(selected):,} rows, "
            f"industry={selected['l1_code'].notna().mean():.2%}",
            flush=True,
        )

    panel = pd.concat(outputs, ignore_index=True).drop_duplicates(["dt", "Ticker"])
    identity = "|".join(
        [
            report["snapshot_id"],
            f"LIQUID_ALL_A_TOP{args.top_n}",
            str(args.window),
            str(args.min_observations),
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d"),
        ]
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    universe_code = f"LIQUID_ALL_A_TOP{args.top_n}"
    output_dir = root / "gold" / "evaluator_inputs" / universe_code
    output_path = output_dir / (
        f"panel-{start:%Y%m%d}-{end:%Y%m%d}-factor_validation-{digest}.parquet"
    )
    manifest_path = output_path.with_suffix(".manifest.json")
    if output_path.exists() and manifest_path.exists():
        print(f"Cached evaluator input: {output_path}")
        return
    write_parquet_immutable(panel, output_path)
    universe_definition = {
        "ranking_field": "trailing_median_amount",
        "window_observations": args.window,
        "minimum_observations": args.min_observations,
        "top_n": args.top_n,
        "information_cutoff": "signal_date_close",
    }
    universe_sha256 = hashlib.sha256(
        json.dumps(universe_definition, sort_keys=True).encode("utf-8")
    ).hexdigest()
    manifest = {
        "build_id": run_id(),
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "research_stage": "factor_validation",
        "range": [start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")],
        "universe_code": universe_code,
        "universe_definition": universe_definition,
        "universe_sha256": universe_sha256,
        "data_snapshot": report["snapshot_id"],
        "quality_report": str(report_path),
        "industry_path": str(industry_path),
        "industry_sha256": parquet_sha256(industry_path),
        "label_version": report["labels"]["label_version"],
        "output_path": str(output_path),
        "output_sha256": parquet_sha256(output_path),
        "rows": int(len(panel)),
        "dates": int(panel["dt"].nunique()),
        "securities": int(panel["Ticker"].nunique()),
        "first_date": panel["dt"].min().strftime("%Y-%m-%d"),
        "last_date": panel["dt"].max().strftime("%Y-%m-%d"),
        "industry_coverage": float(panel["l1_code"].notna().mean()),
        "primary_label_availability": float(
            panel["primary_label_available"].fillna(False).mean()
        ),
        "source_file_count": len(source_files),
        "schema": {column: str(dtype) for column, dtype in panel.dtypes.items()},
    }
    write_json_immutable(manifest, manifest_path)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
