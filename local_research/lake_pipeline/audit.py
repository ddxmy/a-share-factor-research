#!/usr/bin/env python3
"""Audit silver A-share panels and create a reproducible data snapshot manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from common import DEFAULT_ROOT, is_a_share, parquet_sha256, run_id, write_json_immutable


def period_key(path: Path) -> tuple[int, int]:
    text = str(path)
    year = int(re.search(r"year=(\d{4})", text).group(1))
    month = int(re.search(r"month=(\d{2})", text).group(1))
    return year, month


def through_date(path: Path) -> str:
    match = re.search(r"part-through-(\d{8})-", path.name)
    return match.group(1) if match else "00000000"


def latest_monthly_files(root: Path) -> list[Path]:
    grouped: dict[tuple[int, int], list[Path]] = {}
    for path in (root / "silver" / "equity_daily").glob("year=*/month=*/part-through-*.parquet"):
        grouped.setdefault(period_key(path), []).append(path)
    selected = []
    for key in sorted(grouped):
        selected.append(
            max(
                grouped[key],
                key=lambda path: (through_date(path), path.stat().st_mtime_ns, path.name),
            )
        )
    return selected


def latest_file(directory: Path, pattern: str) -> Path | None:
    paths = sorted(directory.glob(pattern))
    return max(paths, key=lambda path: pq.ParquetFile(path).metadata.num_rows) if paths else None


def latest_built_reference_path(root: Path, stem: str) -> Path | None:
    for manifest_path in reversed(sorted((root / "manifests").glob("build-run-*.json"))):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        file_record = manifest.get("reference", {}).get("files", {}).get(stem, {})
        candidate = Path(file_record["path"]) if file_record.get("path") else None
        if candidate is not None and candidate.exists():
            return candidate
    return None


def load_industry_intervals(root: Path) -> tuple[Path | None, pd.DataFrame, dict[str, Any]]:
    path = latest_built_reference_path(root, "industry_membership")
    if path is None:
        path = latest_file(root / "silver", "industry_membership-*.parquet")
    if path is None:
        return None, pd.DataFrame(), {"status": "missing"}
    frame = pd.read_parquet(path)
    required = {"ts_code", "l1_code", "in_date", "out_date", "is_new"}
    missing = sorted(required - set(frame.columns))
    if missing:
        return path, pd.DataFrame(), {
            "status": "invalid_schema",
            "path": str(path),
            "missing_columns": missing,
        }

    frame = frame.copy()
    frame["ts_code"] = frame["ts_code"].astype(str)
    frame["in_date"] = pd.to_datetime(frame["in_date"], format="%Y%m%d", errors="coerce")
    frame["out_date"] = pd.to_datetime(frame["out_date"], format="%Y%m%d", errors="coerce")
    duplicate_intervals = int(
        frame.duplicated(["ts_code", "l1_code", "in_date", "out_date", "is_new"]).sum()
    )
    invalid_intervals = int(
        (
            frame["in_date"].isna()
            | (frame["out_date"].notna() & (frame["out_date"] < frame["in_date"]))
        ).sum()
    )
    ordered = frame.dropna(subset=["in_date"]).sort_values(["ts_code", "in_date", "out_date"])
    inclusive_end = ordered["out_date"].fillna(pd.Timestamp("2099-12-31"))
    prior_max_end = inclusive_end.groupby(ordered["ts_code"]).cummax().groupby(
        ordered["ts_code"]
    ).shift(1)
    overlapping_intervals = int((ordered["in_date"] <= prior_max_end).sum())
    flags = frame["is_new"].astype(str)
    quality = {
        "status": "available",
        "path": str(path),
        "sha256": parquet_sha256(path),
        "rows": int(len(frame)),
        "securities": int(frame["ts_code"].nunique()),
        "l1_industries": int(frame["l1_code"].nunique()),
        "current_rows": int(flags.eq("Y").sum()),
        "historical_rows": int(flags.eq("N").sum()),
        "historical_rows_without_out_date": int(
            (flags.eq("N") & frame["out_date"].isna()).sum()
        ),
        "current_rows_with_out_date": int(
            (flags.eq("Y") & frame["out_date"].notna()).sum()
        ),
        "duplicate_intervals": duplicate_intervals,
        "invalid_intervals": invalid_intervals,
        "overlapping_intervals": overlapping_intervals,
        "first_in_date": (
            frame["in_date"].min().strftime("%Y-%m-%d")
            if frame["in_date"].notna().any()
            else None
        ),
        "last_in_date": (
            frame["in_date"].max().strftime("%Y-%m-%d")
            if frame["in_date"].notna().any()
            else None
        ),
        "classification_versions": sorted(
            frame.get("classification_version", pd.Series(dtype=str))
            .dropna()
            .astype(str)
            .unique()
        ),
    }
    return path, frame, quality


def attach_industry_coverage(
    frame: pd.DataFrame,
    daily: pd.DataFrame,
    industry: pd.DataFrame,
) -> tuple[pd.DataFrame, int, int]:
    if industry.empty:
        daily = daily.copy()
        daily["industry_covered"] = 0
        daily["industry_coverage"] = 0.0
        return daily, 0, 0
    intervals = industry[["ts_code", "in_date", "out_date"]]
    joined = frame[["trade_date", "ts_code"]].merge(
        intervals,
        on="ts_code",
        how="left",
        validate="many_to_many",
    )
    active = joined.loc[
        joined["in_date"].notna()
        & (joined["trade_date"] >= joined["in_date"])
        & (joined["out_date"].isna() | (joined["trade_date"] <= joined["out_date"]))
    ]
    active_counts = active.groupby(["trade_date", "ts_code"]).size()
    multiple_assignments = int(active_counts.gt(1).sum())
    covered = active_counts.reset_index()[["trade_date", "ts_code"]]
    covered_by_date = covered.groupby("trade_date").size().rename("industry_covered")
    result = daily.merge(covered_by_date, on="trade_date", how="left")
    result["industry_covered"] = result["industry_covered"].fillna(0).astype(int)
    result["industry_coverage"] = result["industry_covered"] / result["rows"].clip(lower=1)
    return result, int(len(covered)), multiple_assignments


def audit_month(
    path: Path,
    industry: pd.DataFrame,
) -> tuple[dict[str, Any], pd.DataFrame, set[str]]:
    columns = [
        "trade_date",
        "ts_code",
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "adj_factor",
        "turnover_rate",
        "total_mv",
        "circ_mv",
        "up_limit",
        "down_limit",
        "can_buy_open",
        "can_sell_open",
    ]
    frame = pd.read_parquet(path, columns=columns)
    frame["trade_date"] = pd.to_datetime(frame["trade_date"])
    duplicate_rows = int(frame.duplicated(["trade_date", "ts_code"]).sum())
    nonpositive = int((frame[["open", "high", "low", "close", "pre_close"]].le(0)).any(axis=1).sum())
    high_violation = frame["high"] + 1e-10 < frame[["open", "low", "close"]].max(axis=1)
    low_violation = frame["low"] - 1e-10 > frame[["open", "high", "close"]].min(axis=1)
    daily = (
        frame.groupby("trade_date")
        .agg(
            rows=("ts_code", "size"),
            securities=("ts_code", "nunique"),
            adj_missing=("adj_factor", lambda values: int(values.isna().sum())),
            turnover_missing=("turnover_rate", lambda values: int(values.isna().sum())),
            limit_missing=("up_limit", lambda values: int(values.isna().sum())),
            buyable_open=("can_buy_open", "sum"),
            sellable_open=("can_sell_open", "sum"),
        )
        .reset_index()
    )
    daily, industry_covered_rows, industry_multiple_assignments = attach_industry_coverage(
        frame, daily, industry
    )
    result = {
        "period": f"{period_key(path)[0]:04d}-{period_key(path)[1]:02d}",
        "path": str(path),
        "sha256": parquet_sha256(path),
        "rows": int(len(frame)),
        "dates": int(frame["trade_date"].nunique()),
        "securities": int(frame["ts_code"].nunique()),
        "first_date": frame["trade_date"].min().strftime("%Y-%m-%d"),
        "last_date": frame["trade_date"].max().strftime("%Y-%m-%d"),
        "duplicate_keys": duplicate_rows,
        "nonpositive_price_rows": nonpositive,
        "ohlc_violation_rows": int((high_violation | low_violation).sum()),
        "missing_adj_factor": int(frame["adj_factor"].isna().sum()),
        "missing_daily_basic": int(frame["turnover_rate"].isna().sum()),
        "missing_limit": int(frame["up_limit"].isna().sum()),
        "invalid_a_share_codes": int((~frame["ts_code"].map(is_a_share)).sum()),
        "industry_covered_rows": industry_covered_rows,
        "industry_coverage": industry_covered_rows / max(len(frame), 1),
        "industry_multiple_assignments": industry_multiple_assignments,
    }
    return result, daily, set(frame["ts_code"].astype(str))


def universe_quality(
    root: Path,
    index_code: str,
    industry: pd.DataFrame,
) -> dict[str, Any]:
    directory = root / "silver" / "universe_membership" / index_code
    path = latest_file(directory, "index_weight-*.parquet")
    if path is None:
        return {"index_code": index_code, "status": "missing"}
    frame = pd.read_parquet(path)
    quality = (
        frame.groupby("trade_date")
        .agg(member_count=("con_code", "nunique"), weight_sum=("weight", "sum"))
        .reset_index()
    )
    expected = 300 if index_code == "000300.SH" else 500
    snapshot_months = set(pd.to_datetime(quality["trade_date"]).dt.to_period("M").astype(str))
    current_month = pd.Period(pd.Timestamp.now(tz="Asia/Shanghai").strftime("%Y-%m"), freq="M")
    expected_months = set(
        pd.period_range("2015-01", current_month - 1, freq="M").astype(str)
    )
    result = {
        "index_code": index_code,
        "status": "available",
        "path": str(path),
        "snapshots": int(len(quality)),
        "first_snapshot": str(quality["trade_date"].min()),
        "last_snapshot": str(quality["trade_date"].max()),
        "member_count_min": int(quality["member_count"].min()),
        "member_count_max": int(quality["member_count"].max()),
        "expected_members": expected,
        "snapshots_with_expected_members": int(quality["member_count"].eq(expected).sum()),
        "missing_completed_months": sorted(expected_months - snapshot_months),
        "weight_sum_min": float(quality["weight_sum"].min()),
        "weight_sum_max": float(quality["weight_sum"].max()),
    }
    if industry.empty:
        result.update(
            {
                "industry_observation_coverage": None,
                "industry_snapshot_coverage_min": None,
                "industry_multiple_assignments": None,
            }
        )
        return result

    keys = frame[["trade_date", "con_code"]].rename(columns={"con_code": "ts_code"}).copy()
    keys["trade_date"] = pd.to_datetime(keys["trade_date"], format="%Y%m%d", errors="coerce")
    joined = keys.merge(
        industry[["ts_code", "in_date", "out_date"]],
        on="ts_code",
        how="left",
        validate="many_to_many",
    )
    active = joined.loc[
        joined["in_date"].notna()
        & (joined["trade_date"] >= joined["in_date"])
        & (joined["out_date"].isna() | (joined["trade_date"] <= joined["out_date"]))
    ]
    active_counts = active.groupby(["trade_date", "ts_code"]).size()
    covered = active_counts.reset_index()[["trade_date", "ts_code"]]
    total_by_date = keys.groupby("trade_date").size()
    covered_by_date = (
        covered.groupby("trade_date").size().reindex(total_by_date.index, fill_value=0)
    )
    coverage_by_date = covered_by_date / total_by_date.clip(lower=1)
    result.update(
        {
            "industry_observation_coverage": len(covered) / max(len(keys), 1),
            "industry_snapshot_coverage_min": float(coverage_by_date.min()),
            "industry_snapshot_coverage_median": float(coverage_by_date.median()),
            "industry_multiple_assignments": int(active_counts.gt(1).sum()),
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    paths = latest_monthly_files(root)
    if not paths:
        raise RuntimeError("No silver equity_daily files found")
    industry_path, industry, industry_quality = load_industry_intervals(root)

    monthly: list[dict[str, Any]] = []
    daily_frames: list[pd.DataFrame] = []
    securities: set[str] = set()
    for position, path in enumerate(paths, start=1):
        result, daily, codes = audit_month(path, industry)
        monthly.append(result)
        daily_frames.append(daily)
        securities.update(codes)
        print(f"[audit {position}/{len(paths)}] {result['period']}: {result['rows']:,} rows", flush=True)

    daily = pd.concat(daily_frames, ignore_index=True).sort_values("trade_date")
    calendar_path = latest_file(root / "silver", "trade_calendar-*.parquet")
    missing_open_dates: list[str] = []
    if calendar_path is not None:
        calendar = pd.read_parquet(calendar_path)
        open_dates = pd.to_datetime(
            calendar.loc[calendar["is_open"].astype(int).eq(1), "cal_date"],
            format="%Y%m%d",
            errors="coerce",
        )
        covered = set(daily["trade_date"])
        minimum, maximum = daily["trade_date"].min(), daily["trade_date"].max()
        missing_open_dates = [
            date.strftime("%Y-%m-%d")
            for date in open_dates
            if minimum <= date <= maximum and date not in covered
        ]

    industry_codes = set(industry["ts_code"].dropna().astype(str)) if not industry.empty else set()
    industry_security_coverage = (
        len(securities & industry_codes) / max(len(securities), 1) if industry_codes else None
    )
    industry_observation_coverage = (
        int(daily["industry_covered"].sum()) / max(int(daily["rows"].sum()), 1)
        if "industry_covered" in daily
        else None
    )

    totals = {
        "rows": int(sum(item["rows"] for item in monthly)),
        "dates": int(daily["trade_date"].nunique()),
        "securities": int(len(securities)),
        "first_date": daily["trade_date"].min().strftime("%Y-%m-%d"),
        "last_date": daily["trade_date"].max().strftime("%Y-%m-%d"),
        "duplicate_keys": int(sum(item["duplicate_keys"] for item in monthly)),
        "nonpositive_price_rows": int(sum(item["nonpositive_price_rows"] for item in monthly)),
        "ohlc_violation_rows": int(sum(item["ohlc_violation_rows"] for item in monthly)),
        "missing_adj_factor": int(sum(item["missing_adj_factor"] for item in monthly)),
        "missing_daily_basic": int(sum(item["missing_daily_basic"] for item in monthly)),
        "missing_limit": int(sum(item["missing_limit"] for item in monthly)),
        "missing_open_dates": missing_open_dates,
        "industry_security_coverage_ever": industry_security_coverage,
        "industry_observation_coverage": industry_observation_coverage,
        "industry_daily_coverage_min": (
            float(daily["industry_coverage"].min()) if "industry_coverage" in daily else None
        ),
        "industry_daily_coverage_median": (
            float(daily["industry_coverage"].median()) if "industry_coverage" in daily else None
        ),
        "industry_multiple_assignments": int(
            sum(item["industry_multiple_assignments"] for item in monthly)
        ),
    }
    totals["missing_daily_basic_rate"] = totals["missing_daily_basic"] / max(totals["rows"], 1)
    totals["missing_limit_rate"] = totals["missing_limit"] / max(totals["rows"], 1)
    hard_failures = []
    if totals["duplicate_keys"]:
        hard_failures.append("duplicate_keys")
    if totals["missing_open_dates"]:
        hard_failures.append("missing_open_dates")
    if totals["ohlc_violation_rows"]:
        hard_failures.append("ohlc_violations")
    if totals["missing_adj_factor"]:
        hard_failures.append("missing_adj_factor")
    if totals["missing_daily_basic_rate"] > 0.001:
        hard_failures.append("daily_basic_missing_rate_above_0.1pct")
    if totals["missing_limit_rate"] > 0.001:
        hard_failures.append("price_limit_missing_rate_above_0.1pct")
    if industry_quality.get("status") != "available":
        hard_failures.append("industry_membership_missing_or_invalid")
    else:
        if not industry_quality["historical_rows"]:
            hard_failures.append("industry_history_missing")
        if industry_quality["historical_rows_without_out_date"]:
            hard_failures.append("historical_industry_rows_without_out_date")
        if industry_quality["current_rows_with_out_date"]:
            hard_failures.append("current_industry_rows_with_out_date")
        if industry_quality["duplicate_intervals"]:
            hard_failures.append("duplicate_industry_intervals")
        if industry_quality["invalid_intervals"]:
            hard_failures.append("invalid_industry_intervals")
        if industry_quality["overlapping_intervals"]:
            hard_failures.append("overlapping_industry_intervals")
    if industry_observation_coverage is None or industry_observation_coverage < 0.98:
        hard_failures.append("industry_observation_coverage_below_98pct")
    if totals["industry_multiple_assignments"]:
        hard_failures.append("multiple_active_industry_assignments")

    digest = hashlib.sha256()
    for item in monthly:
        digest.update(item["sha256"].encode("ascii"))
    if industry_path is not None:
        digest.update(parquet_sha256(industry_path).encode("ascii"))
    if calendar_path is not None:
        digest.update(parquet_sha256(calendar_path).encode("ascii"))
    build_manifest_path = None
    for candidate in reversed(sorted((root / "manifests").glob("build-run-*.json"))):
        candidate_manifest = json.loads(candidate.read_text(encoding="utf-8"))
        candidate_labels = candidate_manifest.get("labels", [])
        if candidate_labels and any(item.get("rows") for item in candidate_labels):
            build_manifest_path = candidate
            break
    label_summary: dict[str, Any] | None = None
    if build_manifest_path is not None:
        build_manifest = json.loads(build_manifest_path.read_text(encoding="utf-8"))
        labels = build_manifest.get("labels", [])
        if labels:
            label_rows = int(sum(item.get("rows", 0) for item in labels))
            primary_available = int(sum(item.get("primary_available", 0) for item in labels))
            for item in labels:
                if item.get("sha256"):
                    digest.update(item["sha256"].encode("ascii"))
            label_summary = {
                "build_manifest": str(build_manifest_path),
                "label_version": labels[0].get("label_version"),
                "months": len(labels),
                "rows": label_rows,
                "primary_available": primary_available,
                "primary_available_rate": primary_available / max(label_rows, 1),
                "files": [item.get("path") for item in labels],
            }
            if label_rows != totals["rows"]:
                hard_failures.append("label_row_count_mismatch")
            if label_summary["primary_available_rate"] < 0.90:
                hard_failures.append("primary_label_availability_below_90pct")
    universes = [
        universe_quality(root, "000300.SH", industry),
        universe_quality(root, "000905.SH", industry),
    ]
    for universe in universes:
        if universe.get("missing_completed_months"):
            hard_failures.append(f"missing_{universe['index_code']}_weight_months")
        universe_industry_coverage = universe.get("industry_observation_coverage")
        if universe_industry_coverage is None or universe_industry_coverage < 0.98:
            hard_failures.append(
                f"industry_coverage_below_98pct_in_{universe['index_code']}"
            )
        if universe.get("industry_multiple_assignments"):
            hard_failures.append(
                f"multiple_active_industry_assignments_in_{universe['index_code']}"
            )
        if universe.get("path"):
            digest.update(parquet_sha256(Path(universe["path"])).encode("ascii"))
    snapshot_id = f"tushare-silver-{totals['first_date']}-{totals['last_date']}-{digest.hexdigest()[:16]}"
    report = {
        "snapshot_id": snapshot_id,
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "root": str(root),
        "status": "pass" if not hard_failures else "fail",
        "hard_failures": hard_failures,
        "totals": totals,
        "industry": industry_quality,
        "labels": label_summary,
        "universes": universes,
        "monthly": monthly,
        "daily_count_summary": {
            "min": int(daily["securities"].min()),
            "median": float(daily["securities"].median()),
            "max": int(daily["securities"].max()),
        },
    }
    report_id = run_id()
    json_path = root / "manifests" / f"data-quality-{report_id}.json"
    write_json_immutable(report, json_path)
    markdown_path = root / "manifests" / f"data-quality-{report_id}.md"
    markdown = f"""# Tushare Data-Lake Quality Report

- Snapshot: `{snapshot_id}`
- Status: `{report['status']}`
- Range: {totals['first_date']} to {totals['last_date']}
- Rows: {totals['rows']:,}
- Trading dates: {totals['dates']:,}
- Securities: {totals['securities']:,}
- Duplicate keys: {totals['duplicate_keys']:,}
- Missing open dates: {len(totals['missing_open_dates']):,}
- OHLC violations: {totals['ohlc_violation_rows']:,}
- Missing adjustment factors: {totals['missing_adj_factor']:,}
- Missing daily-basic rows: {totals['missing_daily_basic']:,}
- Missing price-limit rows: {totals['missing_limit']:,}
- Missing daily-basic rate: {totals['missing_daily_basic_rate']:.4%}
- Missing price-limit rate: {totals['missing_limit_rate']:.4%}
- Industry interval rows: {industry_quality.get('rows', 'unavailable')}
- Historical industry rows: {industry_quality.get('historical_rows', 'unavailable')}
- Industry security coverage (ever observed): {industry_security_coverage if industry_security_coverage is not None else 'unavailable'}
- Industry observation coverage (point-in-time): {industry_observation_coverage if industry_observation_coverage is not None else 'unavailable'}
- Minimum daily industry coverage: {totals['industry_daily_coverage_min']}
- Multiple active industry assignments: {totals['industry_multiple_assignments']}
- Primary label availability: {label_summary['primary_available_rate'] if label_summary else 'unavailable'}

Hard failures: {', '.join(hard_failures) if hard_failures else 'none'}
"""
    # Markdown is an immutable report too; use exclusive creation semantics.
    if markdown_path.exists():
        raise FileExistsError(f"Refusing to overwrite report: {markdown_path}")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = markdown_path.open("x", encoding="utf-8")
    with descriptor:
        descriptor.write(markdown)
    print(json.dumps({"report": str(json_path), "snapshot_id": snapshot_id, "status": report["status"]}, indent=2))


if __name__ == "__main__":
    main()
