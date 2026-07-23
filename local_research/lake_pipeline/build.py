#!/usr/bin/env python3
"""Normalize immutable Tushare raw partitions into silver panels and gold labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from common import (
    CORE_ENDPOINTS,
    DEFAULT_ROOT,
    is_a_share,
    month_periods,
    parquet_sha256,
    partition_dir,
    read_partition_frames,
    run_id,
    stable_schema,
    write_json_immutable,
    write_parquet_immutable,
)


KEYS = ["trade_date", "ts_code"]


def largest_parquet(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    import pyarrow.parquet as pq

    return max(paths, key=lambda path: pq.ParquetFile(path).metadata.num_rows)


def normalize_key_types(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    result = frame.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"], format="%Y%m%d", errors="coerce")
    result["ts_code"] = result["ts_code"].astype(str)
    return result.dropna(subset=KEYS)


def deduplicate(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    return frame.drop_duplicates(KEYS, keep="last").sort_values(KEYS)


def raw_month(root: Path, endpoint: str, period: pd.Period) -> pd.DataFrame:
    return read_partition_frames(partition_dir(root, endpoint, period))


def raw_partition_tag(root: Path, period: pd.Period) -> str:
    digest = hashlib.sha256()
    for endpoint in CORE_ENDPOINTS:
        for path in sorted(partition_dir(root, endpoint, period).glob("*.parquet")):
            digest.update(endpoint.encode("utf-8"))
            digest.update(path.name.encode("utf-8"))
            digest.update(str(path.stat().st_size).encode("ascii"))
    return digest.hexdigest()[:12]


def historical_st_from_names(root: Path, period: pd.Period, trade_dates: pd.Series) -> pd.DataFrame:
    paths = sorted((root / "silver").glob("namechange-*.parquet"))
    source_path = largest_parquet(paths)
    if source_path is None:
        return pd.DataFrame(columns=KEYS + ["namechange_st_name"])
    names = pd.read_parquet(source_path)
    names = names.loc[names["name"].astype(str).str.contains("ST", case=False, na=False)].copy()
    names["start_date"] = pd.to_datetime(names["start_date"], format="%Y%m%d", errors="coerce")
    names["end_date"] = pd.to_datetime(names["end_date"], format="%Y%m%d", errors="coerce")
    names["end_date"] = names["end_date"].fillna(pd.Timestamp("2099-12-31"))
    month_start, month_end = period.start_time, period.end_time
    names = names.loc[(names["start_date"] <= month_end) & (names["end_date"] >= month_start)]
    dates = pd.DatetimeIndex(pd.to_datetime(trade_dates).dropna().unique()).sort_values()
    records: list[pd.DataFrame] = []
    for row in names[["ts_code", "name", "start_date", "end_date"]].itertuples(index=False):
        active = dates[(dates >= row.start_date) & (dates <= row.end_date)]
        if len(active):
            records.append(
                pd.DataFrame(
                    {
                        "trade_date": active,
                        "ts_code": str(row.ts_code),
                        "namechange_st_name": str(row.name),
                    }
                )
            )
    if not records:
        return pd.DataFrame(columns=KEYS + ["namechange_st_name"])
    return pd.concat(records, ignore_index=True).drop_duplicates(KEYS, keep="last")


def build_equity_month(root: Path, period: pd.Period) -> dict[str, Any]:
    source = {endpoint: raw_month(root, endpoint, period) for endpoint in CORE_ENDPOINTS}
    if source["daily"].empty:
        return {"period": str(period), "status": "missing_daily"}

    daily = deduplicate(normalize_key_types(source["daily"]))
    daily = daily.loc[daily["ts_code"].map(is_a_share)].copy()
    if daily.empty:
        return {"period": str(period), "status": "no_a_share_rows"}

    basic = deduplicate(normalize_key_types(source["daily_basic"]))
    adj = deduplicate(normalize_key_types(source["adj_factor"]))
    limits = deduplicate(normalize_key_types(source["stk_limit"]))
    if "pre_close" in limits.columns:
        limits = limits.rename(columns={"pre_close": "limit_pre_close"})

    suspension = normalize_key_types(source["suspend_d"])
    if suspension.empty:
        suspension = pd.DataFrame(columns=KEYS + ["is_suspended", "suspend_type"])
    else:
        suspension = (
            suspension.groupby(KEYS, as_index=False)
            .agg(
                suspend_type=("suspend_type", lambda values: "|".join(sorted(set(map(str, values))))),
            )
            .assign(is_suspended=True)
        )

    st = normalize_key_types(source["stock_st"])
    if st.empty:
        st = pd.DataFrame(columns=KEYS + ["is_st", "st_type", "st_type_name", "st_name"])
    else:
        rename = {"type": "st_type", "type_name": "st_type_name", "name": "st_name"}
        st = deduplicate(st.rename(columns=rename)).assign(is_st=True)

    panel = daily.merge(basic, on=KEYS, how="left", validate="one_to_one")
    panel = panel.merge(adj, on=KEYS, how="left", validate="one_to_one")
    panel = panel.merge(limits, on=KEYS, how="left", validate="one_to_one")
    panel = panel.merge(suspension, on=KEYS, how="left", validate="one_to_one")
    panel = panel.merge(st, on=KEYS, how="left", validate="one_to_one")
    historical_st = historical_st_from_names(root, period, panel["trade_date"])
    panel = panel.merge(historical_st, on=KEYS, how="left", validate="one_to_one")

    # Tushare units: vol=100 shares, amount=thousand CNY, share/mv fields=10k units.
    panel["volume_shares"] = pd.to_numeric(panel["vol"], errors="coerce") * 100.0
    panel["amount_cny"] = pd.to_numeric(panel["amount"], errors="coerce") * 1_000.0
    panel["vwap"] = panel["amount_cny"] / panel["volume_shares"].replace(0, np.nan)
    for column in ("total_share", "float_share", "free_share"):
        if column in panel:
            panel[f"{column}_shares"] = pd.to_numeric(panel[column], errors="coerce") * 10_000.0
    for column in ("total_mv", "circ_mv"):
        if column in panel:
            panel[f"{column}_cny"] = pd.to_numeric(panel[column], errors="coerce") * 10_000.0
    for column in ("turnover_rate", "turnover_rate_f"):
        if column in panel:
            panel[f"{column}_decimal"] = pd.to_numeric(panel[column], errors="coerce") / 100.0
    for column in ("pe", "pe_ttm", "pb", "ps", "ps_ttm"):
        if column in panel:
            panel[column] = pd.to_numeric(panel[column], errors="coerce")
    for column in ("dv_ratio", "dv_ttm"):
        if column in panel:
            panel[f"{column}_decimal"] = pd.to_numeric(panel[column], errors="coerce") / 100.0

    panel["is_suspended"] = panel.get("is_suspended", False).astype("boolean").fillna(False).astype(bool)
    panel["is_st"] = (
        panel.get("is_st", False).astype("boolean").fillna(False)
        | panel["namechange_st_name"].notna()
    ).astype(bool)
    positive_prices = panel[["open", "close"]].gt(0).all(axis=1)
    tolerance = 1e-10
    panel["can_buy_open"] = (
        positive_prices
        & ~panel["is_suspended"]
        & (panel["up_limit"].isna() | (panel["open"] < panel["up_limit"] - tolerance))
    )
    panel["can_sell_open"] = (
        positive_prices
        & ~panel["is_suspended"]
        & (panel["down_limit"].isna() | (panel["open"] > panel["down_limit"] + tolerance))
    )
    panel = panel.sort_values(KEYS).reset_index(drop=True)

    through = panel["trade_date"].max().strftime("%Y%m%d")
    silver_dir = root / "silver" / "equity_daily" / f"year={period.year:04d}" / f"month={period.month:02d}"
    namechange_path = largest_parquet(sorted((root / "silver").glob("namechange-*.parquet")))
    reference_tag = parquet_sha256(namechange_path)[:12] if namechange_path is not None else "none"
    source_tag = raw_partition_tag(root, period)
    existing = sorted(
        silver_dir.glob(f"part-through-{through}-ref-{reference_tag}-src-{source_tag}-*.parquet")
    )
    if existing:
        return {
            "period": str(period),
            "status": "cached",
            "rows": int(len(panel)),
            "through": through,
            "path": str(existing[-1]),
        }

    build_id = run_id()
    panel_path = silver_dir / (
        f"part-through-{through}-ref-{reference_tag}-src-{source_tag}-{build_id}.parquet"
    )
    write_parquet_immutable(panel, panel_path)
    tradability_columns = KEYS + [
        "is_suspended",
        "is_st",
        "up_limit",
        "down_limit",
        "can_buy_open",
        "can_sell_open",
    ]
    tradability = panel[tradability_columns].copy()
    tradability_dir = root / "silver" / "tradability" / f"year={period.year:04d}" / f"month={period.month:02d}"
    tradability_path = tradability_dir / (
        f"part-through-{through}-ref-{reference_tag}-src-{source_tag}-{build_id}.parquet"
    )
    write_parquet_immutable(tradability, tradability_path)
    manifest = {
        "build_id": build_id,
        "period": str(period),
        "through": through,
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "panel_path": str(panel_path),
        "panel_sha256": parquet_sha256(panel_path),
        "tradability_path": str(tradability_path),
        "tradability_sha256": parquet_sha256(tradability_path),
        "rows": int(len(panel)),
        "dates": int(panel["trade_date"].nunique()),
        "securities": int(panel["ts_code"].nunique()),
        "schema": stable_schema(panel),
        "source_rows": {endpoint: int(len(frame)) for endpoint, frame in source.items()},
    }
    write_json_immutable(manifest, silver_dir / "_manifests" / f"build-{build_id}.json")
    return {"period": str(period), "status": "built", **manifest}


def latest_reference_snapshot(root: Path) -> Path | None:
    snapshots = sorted((root / "raw" / "reference_snapshot").glob("snapshot=*"))
    for snapshot in reversed(snapshots):
        manifest_path = snapshot / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("complete") is True:
            return snapshot
    return None


def write_versioned_reference(frame: pd.DataFrame, directory: Path, stem: str) -> Path:
    normalized = frame.reset_index(drop=True)
    hashed = pd.util.hash_pandas_object(normalized, index=False).values.tobytes()
    digest = hashlib.sha256(hashed).hexdigest()[:16]
    path = directory / f"{stem}-{digest}.parquet"
    if path.exists():
        return path
    write_parquet_immutable(frame, path)
    return path


def normalize_industry_membership(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize SW2021 membership into inclusive point-in-time intervals."""
    required = {"l1_code", "l1_name", "ts_code", "in_date", "out_date", "is_new"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"Industry membership missing required columns: {missing}")
    result = frame.copy()
    result["ts_code"] = result["ts_code"].astype(str)
    result["in_date"] = pd.to_datetime(result["in_date"], format="%Y%m%d", errors="coerce")
    result["out_date"] = pd.to_datetime(result["out_date"], format="%Y%m%d", errors="coerce")
    if result["in_date"].isna().any():
        raise RuntimeError("Industry membership contains unparseable in_date values")
    result["classification_version"] = "SW2021"
    result["source"] = "tushare.index_member_all"
    return (
        result.drop_duplicates(["l1_code", "ts_code", "in_date", "out_date", "is_new"])
        .sort_values(["ts_code", "in_date", "out_date", "l1_code"], na_position="last")
        .reset_index(drop=True)
    )


def build_reference_tables(root: Path) -> dict[str, Any]:
    snapshot = latest_reference_snapshot(root)
    if snapshot is None:
        return {"status": "missing_reference_snapshot"}
    outputs: dict[str, Any] = {"status": "built", "source_snapshot": str(snapshot), "files": {}}
    mappings = {
        "trade_cal.parquet": (root / "silver", "trade_calendar"),
        "stock_basic.parquet": (root / "silver", "security_master"),
        "index_classify_sw2014_l1.parquet": (
            root / "silver",
            "industry_classification_sw2014_l1",
        ),
        "index_classify_sw2021_l1.parquet": (
            root / "silver",
            "industry_classification_sw2021_l1",
        ),
        "index_member_all_sw2021_l1.parquet": (root / "silver", "industry_membership"),
        "namechange.parquet": (root / "silver", "namechange"),
    }
    for source_name, (directory, stem) in mappings.items():
        source_path = snapshot / source_name
        if not source_path.exists():
            outputs["files"][stem] = {"status": "missing_source"}
            continue
        frame = pd.read_parquet(source_path)
        if stem == "industry_membership":
            frame = normalize_industry_membership(frame)
        path = write_versioned_reference(frame, directory, stem)
        outputs["files"][stem] = {
            "path": str(path),
            "rows": int(len(frame)),
            "sha256": parquet_sha256(path),
        }

    for index_code in ("000300.SH", "000905.SH"):
        safe_code = index_code.replace(".", "_")
        endpoint = f"index_weight_{safe_code}"
        paths = sorted((root / "raw" / endpoint).glob("year=*/month=*/*.parquet"))
        if not paths:
            outputs["files"][endpoint] = {"status": "missing_source"}
            continue
        frame = pd.concat((pd.read_parquet(path) for path in paths), ignore_index=True)
        frame = frame.drop_duplicates(["index_code", "trade_date", "con_code"]).sort_values(
            ["trade_date", "con_code"]
        )
        directory = root / "silver" / "universe_membership" / index_code
        path = write_versioned_reference(frame, directory, "index_weight")
        outputs["files"][endpoint] = {
            "path": str(path),
            "rows": int(len(frame)),
            "sha256": parquet_sha256(path),
        }
    return outputs


def parse_period_from_path(path: Path) -> pd.Period:
    year = int(re.search(r"year=(\d{4})", str(path)).group(1))
    month = int(re.search(r"month=(\d{2})", str(path)).group(1))
    return pd.Period(year=year, month=month, freq="M")


def latest_silver_path(root: Path, period: pd.Period) -> Path | None:
    directory = root / "silver" / "equity_daily" / f"year={period.year:04d}" / f"month={period.month:02d}"
    paths = list(directory.glob("part-through-*.parquet"))
    if not paths:
        return None

    def version_key(path: Path) -> tuple[str, int, str]:
        match = re.search(r"part-through-(\d{8})-", path.name)
        through = match.group(1) if match else "00000000"
        return through, path.stat().st_mtime_ns, path.name

    return max(paths, key=version_key)


def latest_trade_calendar(root: Path) -> pd.DataFrame:
    paths = sorted((root / "silver").glob("trade_calendar-*.parquet"))
    path = largest_parquet(paths)
    if path is None:
        raise RuntimeError("No silver trade calendar; build references first")
    calendar = pd.read_parquet(path)
    calendar["cal_date"] = pd.to_datetime(calendar["cal_date"], format="%Y%m%d", errors="coerce")
    return calendar.loc[calendar["is_open"].astype(int).eq(1)].sort_values("cal_date")


def build_label_month(root: Path, period: pd.Period, label_version: str) -> dict[str, Any]:
    current_path = latest_silver_path(root, period)
    if current_path is None:
        return {"period": str(period), "status": "missing_silver"}
    next_path = latest_silver_path(root, period + 1)
    current = pd.read_parquet(
        current_path,
        columns=KEYS + ["open", "close", "adj_factor", "can_buy_open", "can_sell_open", "is_st"],
    )
    lookup_frames = [current]
    if next_path is not None:
        lookup_frames.append(
            pd.read_parquet(
                next_path,
                columns=KEYS + ["open", "close", "adj_factor", "can_buy_open", "can_sell_open", "is_st"],
            )
        )
    lookup = pd.concat(lookup_frames, ignore_index=True).drop_duplicates(KEYS, keep="last")
    calendar = latest_trade_calendar(root)
    open_dates = calendar["cal_date"].drop_duplicates().sort_values().tolist()
    next_date = dict(zip(open_dates[:-1], open_dates[1:]))
    labels = current[KEYS + ["close", "adj_factor"]].copy()
    labels = labels.rename(columns={"trade_date": "signal_date", "close": "signal_close", "adj_factor": "signal_adj_factor"})
    labels["execution_date"] = labels["signal_date"].map(next_date)
    execution = lookup.rename(
        columns={
            "trade_date": "execution_date",
            "open": "execution_open",
            "close": "execution_close",
            "adj_factor": "execution_adj_factor",
            "can_buy_open": "execution_can_buy_open",
            "can_sell_open": "execution_can_sell_open",
            "is_st": "execution_is_st",
        }
    )
    labels = labels.merge(execution, on=["execution_date", "ts_code"], how="left", validate="many_to_one")
    labels["next_open_to_close"] = labels["execution_close"] / labels["execution_open"] - 1.0
    labels["next_close_to_close"] = (
        labels["execution_close"] * labels["execution_adj_factor"]
        / (labels["signal_close"] * labels["signal_adj_factor"])
        - 1.0
    )
    execution_can_buy = labels["execution_can_buy_open"].astype("boolean").fillna(False)
    execution_can_sell = labels["execution_can_sell_open"].astype("boolean").fillna(False)
    execution_is_st = labels["execution_is_st"].astype("boolean").fillna(True)
    labels["primary_label_available"] = (
        labels["next_open_to_close"].notna()
        & execution_can_buy
        & execution_can_sell
        & ~execution_is_st
    )
    through = labels["signal_date"].max().strftime("%Y%m%d")
    output_dir = root / "gold" / "labels" / label_version / f"year={period.year:04d}" / f"month={period.month:02d}"
    source_text = "|".join(str(path) for path in [current_path, next_path] if path is not None)
    source_tag = hashlib.sha256(source_text.encode("utf-8")).hexdigest()[:12]
    existing = sorted(output_dir.glob(f"part-through-{through}-src-{source_tag}-*.parquet"))
    if existing:
        path = existing[-1]
        return {
            "label_version": label_version,
            "period": str(period),
            "status": "cached",
            "path": str(path),
            "sha256": parquet_sha256(path),
            "rows": int(len(labels)),
            "primary_available": int(labels["primary_label_available"].sum()),
            "source_silver": [
                str(source_path)
                for source_path in [current_path, next_path]
                if source_path is not None
            ],
        }
    identifier = run_id()
    path = output_dir / f"part-through-{through}-src-{source_tag}-{identifier}.parquet"
    write_parquet_immutable(labels, path)
    manifest = {
        "label_version": label_version,
        "period": str(period),
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "path": str(path),
        "sha256": parquet_sha256(path),
        "rows": int(len(labels)),
        "primary_available": int(labels["primary_label_available"].sum()),
        "source_silver": [str(path) for path in [current_path, next_path] if path is not None],
        "definitions": {
            "primary": "execution_close / execution_open - 1",
            "secondary": "adjusted_execution_close / adjusted_signal_close - 1",
            "alignment": "signal at t close; execution and return on the next market trading day",
        },
    }
    write_json_immutable(manifest, output_dir / "_manifests" / f"build-{identifier}.json")
    return {"period": str(period), "status": "built", **manifest}


def available_raw_periods(root: Path) -> list[pd.Period]:
    paths = sorted((root / "raw" / "daily").glob("year=*/month=*"))
    return sorted({parse_period_from_path(path) for path in paths})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--max-months", type=int)
    parser.add_argument("--skip-labels", action="store_true")
    parser.add_argument("--reference-only", action="store_true")
    parser.add_argument("--label-version", default="next_open_close_v1")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.reference_only:
        results = {
            "build_id": run_id(),
            "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
            "root": str(root),
            "periods": [],
            "reference": build_reference_tables(root),
            "silver": [],
            "labels": [],
        }
        manifest_path = root / "manifests" / f"build-run-{results['build_id']}.json"
        write_json_immutable(results, manifest_path)
        print(f"Build manifest: {manifest_path}")
        return
    periods = available_raw_periods(root)
    if args.start_date and args.end_date:
        allowed = set(month_periods(args.start_date, args.end_date))
        periods = [period for period in periods if period in allowed]
    elif args.start_date or args.end_date:
        raise ValueError("Provide both --start-date and --end-date, or neither")
    if args.max_months is not None:
        periods = periods[: args.max_months]
    if not periods:
        raise RuntimeError("No raw daily partitions found")

    results: dict[str, Any] = {
        "build_id": run_id(),
        "created_at": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "root": str(root),
        "periods": [str(period) for period in periods],
        "reference": build_reference_tables(root),
        "silver": [],
        "labels": [],
    }
    for position, period in enumerate(periods, start=1):
        result = build_equity_month(root, period)
        results["silver"].append(result)
        print(f"[silver {position}/{len(periods)}] {period}: {result['status']}", flush=True)
    if not args.skip_labels:
        for position, period in enumerate(periods, start=1):
            result = build_label_month(root, period, args.label_version)
            results["labels"].append(result)
            print(f"[labels {position}/{len(periods)}] {period}: {result['status']}", flush=True)

    manifest_path = root / "manifests" / f"build-run-{results['build_id']}.json"
    write_json_immutable(results, manifest_path)
    print(f"Build manifest: {manifest_path}")


if __name__ == "__main__":
    main()
