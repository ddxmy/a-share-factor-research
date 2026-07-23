"""Shared configuration and safe I/O helpers for the Tushare data lake."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import pandas as pd
import tushare as ts


DEFAULT_ROOT = Path("/Users/mingyuxu/Desktop/因子挖掘/data_lake/tushare")
DEFAULT_START_DATE = "20150101"

ENDPOINT_FIELDS: dict[str, str] = {
    "daily": "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
    "daily_basic": (
        "ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,total_share,"
        "float_share,free_share,total_mv,circ_mv,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm"
    ),
    "adj_factor": "ts_code,trade_date,adj_factor",
    "stk_limit": "trade_date,ts_code,pre_close,up_limit,down_limit",
    "suspend_d": "ts_code,trade_date,suspend_timing,suspend_type",
    "stock_st": "ts_code,name,trade_date,type,type_name",
}

CORE_ENDPOINTS = tuple(ENDPOINT_FIELDS)
NONEMPTY_ENDPOINTS = ("daily", "daily_basic", "adj_factor", "stk_limit")
INDEX_CODES = ("000300.SH", "000905.SH")
INDEX_DAILY_FIELDS = (
    "ts_code,trade_date,close,open,high,low,pre_close,change,pct_chg,vol,amount"
)
STOCK_BASIC_FIELDS = (
    "ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,"
    "curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type"
)

PERMISSION_MARKERS = (
    "权限",
    "积分",
    "permission",
    "参数",
    "必选",
    "不存在",
    "invalid",
)


def normalize_date(value: str | pd.Timestamp) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


def latest_candidate_end_date() -> str:
    """Default conservatively to yesterday in Asia/Shanghai."""
    now = pd.Timestamp.now(tz="Asia/Shanghai")
    return (now.normalize() - pd.Timedelta(days=1)).strftime("%Y%m%d")


def is_a_share(code: str) -> bool:
    return bool(re.match(r"^(?:[036]\d{5}\.(?:SH|SZ)|[48]\d{5}\.BJ)$", str(code)))


def require_token() -> str:
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is not set. Export it before running the pipeline.")
    return token


def make_client():
    return ts.pro_api(require_token())


def request_frame(
    call: Callable[[], pd.DataFrame],
    *,
    retries: int = 3,
    base_delay: float = 1.0,
) -> pd.DataFrame:
    """Retry transient failures, but surface permission and parameter errors immediately."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            result = call()
            if not isinstance(result, pd.DataFrame):
                raise TypeError(f"Tushare returned {type(result).__name__}, expected DataFrame")
            return result
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            if any(marker.lower() in message for marker in PERMISSION_MARKERS):
                raise
            if attempt + 1 < retries:
                time.sleep(base_delay * (2**attempt))
    raise RuntimeError(f"Tushare request failed after {retries} attempts: {last_error}")


def sanitize_error(exc: Exception) -> str:
    message = " ".join(str(exc).split())
    token = os.environ.get("TUSHARE_TOKEN")
    if token:
        message = message.replace(token, "<redacted>")
    return message[:2000]


def month_periods(start_date: str, end_date: str) -> list[pd.Period]:
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start > end:
        raise ValueError("start_date must not be after end_date")
    return list(pd.period_range(start.to_period("M"), end.to_period("M"), freq="M"))


def partition_dir(root: Path, endpoint: str, period: pd.Period) -> Path:
    return root / "raw" / endpoint / f"year={period.year:04d}" / f"month={period.month:02d}"


def run_id() -> str:
    timestamp = pd.Timestamp.now(tz="Asia/Shanghai").strftime("%Y%m%dT%H%M%S%f")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def write_parquet_immutable(frame: pd.DataFrame, path: Path) -> None:
    """Atomically create a parquet file, refusing to replace an existing path."""
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing data: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        frame.to_parquet(temporary, index=False)
        os.link(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json_immutable(payload: dict[str, Any], path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing manifest: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.write("\n")


def parquet_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_partition_frames(directory: Path, columns: list[str] | None = None) -> pd.DataFrame:
    paths = sorted(directory.glob("*.parquet"))
    if not paths:
        return pd.DataFrame()
    frames = [pd.read_parquet(path, columns=columns) for path in paths]
    return pd.concat(frames, ignore_index=True)


def covered_dates(directory: Path) -> set[str]:
    covered: set[str] = set()
    for path in sorted((directory / "_manifests").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        covered.update(str(value) for value in payload.get("succeeded_dates", []))
    return covered


def parquet_data_dates(
    directory: Path,
    required_columns: set[str] | None = None,
) -> set[str]:
    """Return dates covered by immutable files that satisfy the current schema."""
    import pyarrow.parquet as pq

    dates: set[str] = set()
    for path in sorted(directory.glob("*.parquet")):
        if required_columns is not None:
            columns = set(pq.ParquetFile(path).schema.names)
            if not required_columns.issubset(columns):
                continue
        frame = pd.read_parquet(path, columns=["trade_date"])
        dates.update(frame["trade_date"].dropna().astype(str))
    return dates


def date_range_for_period(period: pd.Period, start_date: str, end_date: str) -> tuple[str, str]:
    start = max(pd.Timestamp(start_date), period.start_time)
    end = min(pd.Timestamp(end_date), period.end_time)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def stable_schema(frame: pd.DataFrame) -> dict[str, str]:
    return {column: str(dtype) for column, dtype in frame.dtypes.items()}


def unique_sorted(values: Iterable[str]) -> list[str]:
    return sorted(set(str(value) for value in values))
