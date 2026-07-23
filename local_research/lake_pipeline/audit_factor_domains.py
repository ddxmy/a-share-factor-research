#!/usr/bin/env python3
"""Audit optional formula-data domains before enabling them for a campaign."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "local_research" / "lake_pipeline"))

from common import DEFAULT_ROOT, run_id, write_json_immutable  # noqa: E402


VALUATION_FIELDS = ["pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio_decimal", "dv_ttm_decimal"]


def period_key(path: Path) -> tuple[int, int]:
    match = re.search(r"year=(\d{4})/month=(\d{2})", str(path))
    if match is None:
        raise ValueError(path)
    return int(match.group(1)), int(match.group(2))


def through_date(path: Path) -> str:
    match = re.search(r"part-through-(\d{8})-", path.name)
    return match.group(1) if match else "00000000"


def latest_monthly_files(root: Path) -> list[Path]:
    grouped: dict[tuple[int, int], list[Path]] = {}
    for path in (root / "silver" / "equity_daily").glob("year=*/month=*/part-through-*.parquet"):
        grouped.setdefault(period_key(path), []).append(path)
    return [
        max(
            paths,
            key=lambda path: (through_date(path), path.stat().st_mtime_ns, path.name),
        )
        for _, paths in sorted(grouped.items())
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--start-date", default="20150101")
    parser.add_argument("--end-date", default="20221231")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    start = pd.Timestamp(args.start_date)
    end = pd.Timestamp(args.end_date)
    paths = []
    for path in latest_monthly_files(root):
        year, month = period_key(path)
        period = pd.Period(year=year, month=month, freq="M")
        if period.start_time <= end and period.end_time >= start:
            paths.append(path)
    if not paths:
        raise RuntimeError("No silver files in requested audit range")

    rows = 0
    non_null = {field: 0 for field in VALUATION_FIELDS}
    missing_schema_months: list[str] = []
    duplicate_keys = 0
    monthly: list[dict[str, Any]] = []
    for path in paths:
        schema = set(pq.ParquetFile(path).schema.names)
        missing = sorted(set(VALUATION_FIELDS) - schema)
        period = f"{period_key(path)[0]:04d}-{period_key(path)[1]:02d}"
        if missing:
            missing_schema_months.append(period)
            monthly.append({"period": period, "path": str(path), "missing_fields": missing})
            continue
        frame = pd.read_parquet(path, columns=["trade_date", "ts_code", *VALUATION_FIELDS])
        frame["trade_date"] = pd.to_datetime(frame["trade_date"])
        frame = frame.loc[frame["trade_date"].between(start, end)]
        rows += len(frame)
        duplicate_keys += int(frame.duplicated(["trade_date", "ts_code"]).sum())
        coverage = {}
        for field in VALUATION_FIELDS:
            count = int(pd.to_numeric(frame[field], errors="coerce").notna().sum())
            non_null[field] += count
            coverage[field] = count / max(len(frame), 1)
        monthly.append({"period": period, "path": str(path), "rows": len(frame), "coverage": coverage})

    coverage = {field: count / max(rows, 1) for field, count in non_null.items()}
    hard_failures: list[str] = []
    if missing_schema_months:
        hard_failures.append("valuation_schema_missing_in_months")
    if duplicate_keys:
        hard_failures.append("duplicate_keys")
    if rows == 0:
        hard_failures.append("no_auditable_rows")
    if coverage["pb"] < 0.90:
        hard_failures.append("pb_coverage_below_90pct")
    if coverage["ps_ttm"] < 0.90:
        hard_failures.append("ps_ttm_coverage_below_90pct")

    report = {
        "audit_version": "factor_domain_audit_v1",
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "range": [start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")],
        "domain": "valuation_dividend",
        "status": "pass" if not hard_failures else "fail",
        "hard_failures": hard_failures,
        "rows": rows,
        "months": len(paths),
        "missing_schema_months": missing_schema_months,
        "duplicate_keys": duplicate_keys,
        "coverage": coverage,
        "monthly": monthly,
    }
    output = root / "manifests" / f"factor-domain-quality-{run_id()}.json"
    write_json_immutable(report, output)
    print(json.dumps({"report": str(output), **{key: report[key] for key in ("domain", "status", "rows", "coverage", "hard_failures")}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
