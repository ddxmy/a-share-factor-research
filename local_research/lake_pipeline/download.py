#!/usr/bin/env python3
"""Resumable, immutable Tushare downloader for the local A-share data lake."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from common import (
    CORE_ENDPOINTS,
    DEFAULT_ROOT,
    DEFAULT_START_DATE,
    ENDPOINT_FIELDS,
    INDEX_CODES,
    INDEX_DAILY_FIELDS,
    NONEMPTY_ENDPOINTS,
    PERMISSION_MARKERS,
    STOCK_BASIC_FIELDS,
    covered_dates,
    date_range_for_period,
    latest_candidate_end_date,
    make_client,
    month_periods,
    normalize_date,
    parquet_sha256,
    parquet_data_dates,
    partition_dir,
    request_frame,
    run_id,
    sanitize_error,
    stable_schema,
    write_json_immutable,
    write_parquet_immutable,
)


def is_nonretryable_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker.lower() in lowered for marker in PERMISSION_MARKERS)


def persist_batch(
    frame: pd.DataFrame,
    directory: Path,
    batch_id: str,
    metadata: dict[str, Any],
) -> tuple[Path | None, Path]:
    data_path: Path | None = None
    if not frame.empty:
        data_path = directory / f"batch-{batch_id}.parquet"
        write_parquet_immutable(frame, data_path)
        metadata.update(
            {
                "data_file": str(data_path),
                "data_sha256": parquet_sha256(data_path),
                "rows": int(len(frame)),
                "columns": list(frame.columns),
                "schema": stable_schema(frame),
            }
        )
    else:
        metadata.update({"data_file": None, "rows": 0, "columns": [], "schema": {}})
    manifest_path = directory / "_manifests" / f"request-{batch_id}.json"
    write_json_immutable(metadata, manifest_path)
    return data_path, manifest_path


def fetch_trade_calendar(pro, start_date: str, end_date: str) -> pd.DataFrame:
    calendar = request_frame(
        lambda: pro.trade_cal(
            exchange="SSE",
            start_date=start_date,
            end_date=end_date,
            fields="exchange,cal_date,is_open,pretrade_date",
        )
    )
    if calendar.empty:
        raise RuntimeError("trade_cal returned no rows")
    calendar["cal_date"] = calendar["cal_date"].astype(str)
    return calendar.sort_values("cal_date").drop_duplicates(["exchange", "cal_date"])


def fetch_industry_members(
    pro,
    pause: float,
    page_size: int = 2_000,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch current and historical SW2021 membership intervals without the default-Y trap."""
    frames: list[pd.DataFrame] = []
    page_counts: dict[str, int] = {}
    row_counts: dict[str, int] = {}
    for is_new in ("Y", "N"):
        offset = 0
        pages = 0
        rows = 0
        while True:
            frame = request_frame(
                lambda is_new=is_new, offset=offset: pro.index_member_all(
                    is_new=is_new,
                    limit=page_size,
                    offset=offset,
                )
            )
            pages += 1
            rows += len(frame)
            if not frame.empty:
                frames.append(frame)
            if len(frame) < page_size:
                break
            offset += page_size
            time.sleep(pause)
        page_counts[is_new] = pages
        row_counts[is_new] = rows
        time.sleep(pause)

    if not frames:
        raise RuntimeError("index_member_all returned no current or historical rows")
    members = pd.concat(frames, ignore_index=True)
    required = {"l1_code", "ts_code", "in_date", "out_date", "is_new"}
    missing = sorted(required - set(members.columns))
    if missing:
        raise RuntimeError(f"index_member_all missing required columns: {missing}")
    members = members.drop_duplicates(
        ["l1_code", "ts_code", "in_date", "out_date", "is_new"]
    ).sort_values(["ts_code", "in_date", "out_date", "l1_code"], na_position="last")
    observed_flags = set(members["is_new"].dropna().astype(str))
    if not {"Y", "N"}.issubset(observed_flags):
        raise RuntimeError(
            f"index_member_all must contain both current and historical rows; got {observed_flags}"
        )
    return members.reset_index(drop=True), {
        "is_new": ["Y", "N"],
        "page_size": page_size,
        "pages_by_flag": page_counts,
        "rows_by_flag_before_deduplication": row_counts,
    }


def download_reference_snapshot(
    pro,
    root: Path,
    start_date: str,
    end_date: str,
    calendar: pd.DataFrame,
    pause: float,
) -> dict[str, Any]:
    snapshot_id = run_id()
    directory = root / "raw" / "reference_snapshot" / f"snapshot={snapshot_id}"
    directory.mkdir(parents=True, exist_ok=False)
    records: list[dict[str, Any]] = []

    def save(name: str, frame: pd.DataFrame, params: dict[str, Any]) -> None:
        path = directory / f"{name}.parquet"
        write_parquet_immutable(frame, path)
        records.append(
            {
                "endpoint": name,
                "params": params,
                "rows": int(len(frame)),
                "columns": list(frame.columns),
                "sha256": parquet_sha256(path),
                "status": "success",
            }
        )

    save(
        "trade_cal",
        calendar,
        {"exchange": "SSE", "start_date": start_date, "end_date": end_date},
    )

    stock_frames: list[pd.DataFrame] = []
    for status in ("L", "D", "P"):
        try:
            stock_frames.append(
                request_frame(
                    lambda status=status: pro.stock_basic(
                        exchange="", list_status=status, fields=STOCK_BASIC_FIELDS
                    )
                )
            )
        except Exception as exc:
            records.append(
                {
                    "endpoint": "stock_basic",
                    "params": {"list_status": status},
                    "status": "failure",
                    "error": sanitize_error(exc),
                }
            )
        time.sleep(pause)
    if stock_frames:
        stock_basic = pd.concat(stock_frames, ignore_index=True).drop_duplicates(
            ["ts_code", "list_status", "list_date", "delist_date"]
        )
        save("stock_basic", stock_basic, {"list_status": ["L", "D", "P"]})

    try:
        classifications: dict[str, pd.DataFrame] = {}
        for version in ("SW2014", "SW2021"):
            classification = request_frame(
                lambda version=version: pro.index_classify(level="L1", src=version)
            )
            classifications[version] = classification
            save(
                f"index_classify_{version.lower()}_l1",
                classification,
                {"level": "L1", "src": version},
            )
            time.sleep(pause)

        members, member_params = fetch_industry_members(pro, pause)
        sw2021_codes = set(
            classifications["SW2021"]["index_code"].dropna().astype(str)
        )
        unexpected_codes = sorted(set(members["l1_code"].astype(str)) - sw2021_codes)
        if unexpected_codes:
            raise RuntimeError(
                f"index_member_all contains L1 codes outside the SW2021 codebook: {unexpected_codes}"
            )
        member_params.update(
            {
                "classification_version": "SW2021",
                "l1_codes": int(members["l1_code"].nunique()),
            }
        )
        save("index_member_all_sw2021_l1", members, member_params)
    except Exception as exc:
        records.append(
            {
                "endpoint": "index_member_all",
                "params": {
                    "classification_versions": ["SW2014", "SW2021"],
                    "membership_version": "SW2021",
                    "is_new": ["Y", "N"],
                },
                "status": "failure",
                "error": sanitize_error(exc),
            }
        )

    try:
        # The endpoint is capped, so request yearly slices. Start before the research
        # window to retain ST intervals already active on 2015-01-01.
        name_frames: list[pd.DataFrame] = []
        final_year = pd.Timestamp(end_date).year
        for year in range(1990, final_year + 1):
            year_start = f"{year:04d}0101"
            year_end = min(f"{year:04d}1231", end_date)
            if year_start > end_date:
                break
            name_frames.append(
                request_frame(
                    lambda year_start=year_start, year_end=year_end: pro.namechange(
                        start_date=year_start, end_date=year_end
                    )
                )
            )
            time.sleep(pause)
        names = pd.concat(name_frames, ignore_index=True).drop_duplicates(
            ["ts_code", "name", "start_date", "end_date", "ann_date"]
        )
        save(
            "namechange",
            names,
            {"start_date": "19900101", "end_date": end_date, "slicing": "calendar_year"},
        )
    except Exception as exc:
        records.append(
            {
                "endpoint": "namechange",
                "params": {"start_date": start_date, "end_date": end_date},
                "status": "failure",
                "error": sanitize_error(exc),
            }
        )

    manifest = {
        "snapshot_id": snapshot_id,
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "requested_range": [start_date, end_date],
        "records": records,
        "complete": all(record["status"] == "success" for record in records),
    }
    write_json_immutable(manifest, directory / "manifest.json")
    return manifest


def download_daily_partition(
    pro,
    root: Path,
    endpoint: str,
    period: pd.Period,
    dates: list[str],
    pause: float,
) -> dict[str, Any]:
    directory = partition_dir(root, endpoint, period)
    fields = ENDPOINT_FIELDS[endpoint]
    required_columns = set(fields.split(","))
    already_covered = (
        parquet_data_dates(directory, required_columns)
        if endpoint in NONEMPTY_ENDPOINTS
        else covered_dates(directory)
    )
    missing = [date for date in dates if date not in already_covered]
    batch_id = run_id()
    frames: list[pd.DataFrame] = []
    succeeded: list[str] = []
    failures: list[dict[str, str]] = []
    if not missing:
        return {
            "endpoint": endpoint,
            "period": str(period),
            "requested": 0,
            "succeeded": 0,
            "failures": 0,
            "status": "cached",
        }

    method = getattr(pro, endpoint)
    for date in missing:
        try:
            def fetch(date=date):
                result = method(trade_date=date, fields=fields)
                if endpoint in NONEMPTY_ENDPOINTS and result.empty:
                    raise RuntimeError(f"{endpoint} returned an unexpected empty frame for {date}")
                return result

            frame = request_frame(fetch)
            if not frame.empty:
                frames.append(frame)
            succeeded.append(date)
        except Exception as exc:
            error = sanitize_error(exc)
            failures.append({"trade_date": date, "error": error})
            if is_nonretryable_error(error):
                break
        time.sleep(pause)

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not combined.empty and {"ts_code", "trade_date"}.issubset(combined.columns):
        combined = combined.drop_duplicates(["ts_code", "trade_date"]).sort_values(
            ["trade_date", "ts_code"]
        )
    metadata = {
        "batch_id": batch_id,
        "endpoint": endpoint,
        "period": str(period),
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "requested_dates": missing,
        "succeeded_dates": succeeded,
        "row_counts_by_date": {
            str(date): int(count)
            for date, count in (
                combined.groupby("trade_date").size().items() if not combined.empty else []
            )
        },
        "failures": failures,
        "complete": not failures and len(succeeded) == len(missing),
    }
    persist_batch(combined, directory, batch_id, metadata)
    return {
        "endpoint": endpoint,
        "period": str(period),
        "requested": len(missing),
        "succeeded": len(succeeded),
        "failures": len(failures),
        "rows": len(combined),
        "status": "complete" if not failures else "partial",
    }


def download_index_partition(
    pro,
    root: Path,
    endpoint: str,
    index_code: str,
    period: pd.Period,
    start_date: str,
    end_date: str,
    pause: float,
) -> dict[str, Any]:
    safe_code = index_code.replace(".", "_")
    logical_endpoint = f"{endpoint}_{safe_code}"
    directory = partition_dir(root, logical_endpoint, period)
    marker = f"{index_code}:{period}"
    has_data = any(directory.glob("*.parquet"))
    complete_month = period.end_time <= pd.Timestamp(end_date)
    require_nonempty = endpoint == "index_daily" or complete_month
    if has_data or (not require_nonempty and marker in covered_dates(directory)):
        return {"endpoint": logical_endpoint, "period": str(period), "status": "cached"}
    month_start, month_end = date_range_for_period(period, start_date, end_date)
    batch_id = run_id()
    failures: list[dict[str, str]] = []
    frame = pd.DataFrame()
    try:
        if endpoint == "index_weight":
            def fetch_weight():
                result = pro.index_weight(
                    index_code=index_code, start_date=month_start, end_date=month_end
                )
                if require_nonempty and result.empty:
                    raise RuntimeError(
                        f"index_weight returned an unexpected empty frame for {index_code} {period}"
                    )
                return result

            frame = request_frame(fetch_weight)
        elif endpoint == "index_daily":
            def fetch_daily():
                result = pro.index_daily(
                    ts_code=index_code,
                    start_date=month_start,
                    end_date=month_end,
                    fields=INDEX_DAILY_FIELDS,
                )
                if result.empty:
                    raise RuntimeError(
                        f"index_daily returned an unexpected empty frame for {index_code} {period}"
                    )
                return result

            frame = request_frame(fetch_daily)
        else:
            raise ValueError(f"Unsupported index endpoint: {endpoint}")
    except Exception as exc:
        failures.append({"request": marker, "error": sanitize_error(exc)})
    if not frame.empty:
        keys = ["trade_date", "con_code"] if endpoint == "index_weight" else ["trade_date", "ts_code"]
        frame = frame.drop_duplicates(keys).sort_values(keys)
    metadata = {
        "batch_id": batch_id,
        "endpoint": endpoint,
        "index_code": index_code,
        "period": str(period),
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "requested_dates": [marker],
        "succeeded_dates": [] if failures else [marker],
        "failures": failures,
        "complete": not failures,
    }
    persist_batch(frame, directory, batch_id, metadata)
    time.sleep(pause)
    return {
        "endpoint": logical_endpoint,
        "period": str(period),
        "status": "complete" if not failures else "partial",
        "rows": len(frame),
        "failures": len(failures),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=latest_candidate_end_date())
    parser.add_argument(
        "--endpoints",
        default=",".join(CORE_ENDPOINTS),
        help="Comma-separated daily endpoints or 'core'",
    )
    parser.add_argument("--pause", type=float, default=0.15)
    parser.add_argument("--max-months", type=int)
    parser.add_argument("--skip-reference", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    start_date = normalize_date(args.start_date)
    end_date = normalize_date(args.end_date)
    if pd.Timestamp(start_date) > pd.Timestamp(end_date):
        raise ValueError("start-date must not be after end-date")
    root = Path(args.root).resolve()
    endpoint_names = list(CORE_ENDPOINTS) if args.endpoints == "core" else [
        item.strip() for item in args.endpoints.split(",") if item.strip()
    ]
    unknown = sorted(set(endpoint_names) - set(CORE_ENDPOINTS))
    if unknown:
        raise ValueError(f"Unknown daily endpoints: {unknown}")

    periods = month_periods(start_date, end_date)
    if args.max_months is not None:
        periods = periods[: args.max_months]
    if args.dry_run:
        print(
            json.dumps(
                {
                    "root": str(root),
                    "range": [start_date, end_date],
                    "periods": [str(period) for period in periods],
                    "daily_endpoints": endpoint_names,
                    "reference": not args.skip_reference,
                    "indexes": [] if args.skip_index else list(INDEX_CODES),
                },
                indent=2,
            )
        )
        return

    pro = make_client()
    calendar = fetch_trade_calendar(pro, start_date, end_date)
    open_dates = set(calendar.loc[calendar["is_open"].astype(int).eq(1), "cal_date"])
    summary: dict[str, Any] = {
        "run_id": run_id(),
        "started_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "root": str(root),
        "range": [start_date, end_date],
        "periods": [str(period) for period in periods],
        "daily_endpoints": endpoint_names,
        "results": [],
    }

    if not args.skip_reference:
        summary["reference_snapshot"] = download_reference_snapshot(
            pro, root, start_date, end_date, calendar, args.pause
        )

    total_tasks = len(periods) * (len(endpoint_names) + (0 if args.skip_index else 4))
    completed = 0
    for period in periods:
        month_start, month_end = date_range_for_period(period, start_date, end_date)
        dates = sorted(date for date in open_dates if month_start <= date <= month_end)
        for endpoint in endpoint_names:
            result = download_daily_partition(
                pro, root, endpoint, period, dates, args.pause
            )
            summary["results"].append(result)
            completed += 1
            print(
                f"[{completed}/{total_tasks}] {endpoint} {period}: "
                f"{result['status']} rows={result.get('rows', 0)} failures={result.get('failures', 0)}",
                flush=True,
            )
        if not args.skip_index:
            for index_code in INDEX_CODES:
                for endpoint in ("index_weight", "index_daily"):
                    result = download_index_partition(
                        pro,
                        root,
                        endpoint,
                        index_code,
                        period,
                        start_date,
                        end_date,
                        args.pause,
                    )
                    summary["results"].append(result)
                    completed += 1
                    print(
                        f"[{completed}/{total_tasks}] {result['endpoint']} {period}: "
                        f"{result['status']} rows={result.get('rows', 0)}",
                        flush=True,
                    )

    summary["finished_at"] = pd.Timestamp.now(tz="Asia/Shanghai").isoformat()
    summary["failure_count"] = int(
        sum(result.get("failures", 0) for result in summary["results"])
    )
    summary_path = root / "manifests" / f"download-run-{summary['run_id']}.json"
    write_json_immutable(summary, summary_path)
    print(f"Run manifest: {summary_path}")
    if summary["failure_count"]:
        print("WARNING: partial download; rerun the same command to retry only failed dates.")


if __name__ == "__main__":
    main()
