"""One-command orchestration for an auditable A-share factor research run."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Sequence
from uuid import uuid4

import numpy as np
import pandas as pd

from . import performance_records
from .config import ResolvedPaths, load_profile, resolve_data_root
from .data import attach_forward_labels, load_research_panel
from .evaluation import classify_factor, evaluate_ic
from .portfolio import simulate_portfolios
from .processing import prepare_factor_cross_sections
from .registry import (
    REGISTRY_PATH,
    FactorDefinition,
    compute_raw_factor,
    load_factor_definition,
    required_history_sessions,
)
from .reporting import REQUIRED_ARTIFACTS, write_report_bundle


_FROZEN_DAILY_BASELINE_PROFILE = (
    Path(__file__).resolve().parents[2] / "config" / "daily_baseline.yaml"
)


def run_factor(
    factor_id: str,
    profile_path: str | Path,
    start: str,
    end: str,
    output_root: str | Path | None = None,
) -> Path:
    """Run one registered factor and atomically publish its report directory."""
    definition = load_factor_definition(factor_id)
    _validate_factor_path_component(definition.factor_id)
    profile_path = Path(profile_path).expanduser().resolve(strict=True)
    profile = load_profile(profile_path)
    paths = resolve_data_root()
    resolved_output_root = _resolve_output_root(paths, output_root)
    factor_output_directory = _resolve_factor_output_directory(
        paths, resolved_output_root, definition.factor_id
    )
    _validate_catalog(paths)
    _validate_required_fields(paths.daily_panel, definition)

    requested_start = _as_date(start, "start")
    requested_end = _as_date(end, "end")
    if requested_start > requested_end:
        raise ValueError("start must not be after end")
    history_start = _history_start_bound(
        paths.daily_panel, requested_start, required_history_sessions(definition)
    )
    benchmark_open = pd.read_parquet(paths.csi300_open)
    label_end = _label_end_bound(benchmark_open, requested_end, max(profile.horizons))
    loaded_panel = load_research_panel(paths, history_start, label_end)
    raw_factor = compute_raw_factor(
        definition.factor_id,
        _factor_input_panel(loaded_panel, requested_end),
    )
    prepared_factor = prepare_factor_cross_sections(raw_factor, definition)
    labelled = attach_forward_labels(loaded_panel, benchmark_open, profile.horizons)
    research_panel = labelled.merge(
        prepared_factor[
            [
                "trade_date",
                "security_id",
                "raw_value",
                "winsorized_value",
                "zscore_value",
                "directed_score",
            ]
        ],
        on=["trade_date", "security_id"],
        how="left",
        validate="one_to_one",
    )
    research_panel = research_panel.loc[
        research_panel["signal_date"].between(requested_start, requested_end)
    ].sort_values(["signal_date", "security_id"], kind="mergesort").reset_index(drop=True)

    ic_evaluation = evaluate_ic(
        research_panel, profile.horizons, eligibility=("basic", "tradable")
    )
    portfolio_simulations = tuple(
        simulate_portfolios(
            research_panel,
            horizon_days=horizon,
            top_k=profile.top_k,
            quintiles=profile.quintiles,
            one_way_cost_bps=profile.one_way_cost_bps,
        )
        for horizon in profile.holding_period_days
    )
    decision = classify_factor(ic_evaluation, definition, profile.test_years)

    created_at = datetime.now(timezone.utc)
    run_id = f"{created_at:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    summary = _build_summary(
        run_id=run_id,
        created_at=created_at,
        definition=definition,
        profile=profile,
        paths=paths,
        profile_path=profile_path,
        start=start,
        end=end,
        decision=decision,
        run_type=_run_type_for_profile(profile_path),
    )
    data_quality = _build_data_quality(research_panel, profile.horizons)
    published_run = _publish_atomically(
        factor_output_directory,
        run_id=run_id,
        summary=summary,
        data_quality=data_quality,
        ic_evaluation=ic_evaluation,
        portfolio_simulations=portfolio_simulations,
    )
    performance_records.record_successful_run(paths.data_root, published_run)
    return published_run


def _as_date(value: str | pd.Timestamp, name: str) -> pd.Timestamp:
    date = pd.to_datetime(value, errors="coerce")
    if pd.isna(date):
        raise ValueError(f"{name} must be a parseable date")
    return pd.Timestamp(date)


def _history_start_bound(
    daily_panel_path: Path, requested_start: pd.Timestamp, history_sessions: int
) -> pd.Timestamp:
    dates = _catalog_dates(daily_panel_path)
    earlier_dates = dates.loc[dates < requested_start]
    if history_sessions == 0 or earlier_dates.empty:
        return requested_start
    return pd.Timestamp(earlier_dates.iloc[max(0, len(earlier_dates) - history_sessions)])


def _label_end_bound(
    benchmark_open: pd.DataFrame, requested_end: pd.Timestamp, max_horizon: int
) -> pd.Timestamp:
    benchmark_dates = pd.to_datetime(benchmark_open["trade_date"], errors="coerce")
    if benchmark_dates.isna().any():
        raise ValueError("CSI 300 open contains an unparsable trade_date")
    dates = pd.Series(benchmark_dates.drop_duplicates().sort_values().to_numpy())
    requested_dates = dates.loc[dates <= requested_end]
    if requested_dates.empty:
        return requested_end
    last_requested_date = requested_dates.iloc[-1]
    last_position = int(dates.searchsorted(last_requested_date, side="left"))
    return pd.Timestamp(dates.iloc[min(last_position + max_horizon + 1, len(dates) - 1)])


def _catalog_dates(path: Path) -> pd.Series:
    dates = pd.to_datetime(pd.read_parquet(path, columns=["trade_date"])["trade_date"], errors="coerce")
    if dates.isna().any():
        raise ValueError("daily panel contains an unparsable trade_date")
    return pd.Series(dates.drop_duplicates().sort_values().to_numpy())


def _factor_input_panel(panel: pd.DataFrame, requested_end: pd.Timestamp) -> pd.DataFrame:
    """Return only signal-time data available to a researcher factor callable."""
    forbidden_columns = {
        "signal_date",
        "basic_eligible",
        "tradable_next_open",
        "entry_date",
    }
    safe_columns = [
        column
        for column in panel.columns
        if column not in forbidden_columns
        and not column.startswith("label_end_date_")
        and not column.startswith("label_excess_o2o_")
    ]
    return (
        panel.loc[panel["trade_date"] <= requested_end, safe_columns]
        .sort_values(["trade_date", "security_id"], kind="mergesort")
        .reset_index(drop=True)
    )


def _resolve_output_root(paths: ResolvedPaths, output_root: str | Path | None) -> Path:
    data_root = paths.data_root.resolve(strict=True)
    canonical_runs_root = (data_root / "runs").resolve(strict=False)
    candidate = (
        canonical_runs_root
        if output_root is None
        else Path(output_root).expanduser().resolve(strict=False)
    )
    if candidate != canonical_runs_root:
        raise ValueError(
            "output_root must resolve exactly to A_SHARE_DATA_ROOT/runs so every "
            "successful run is recordable."
        )
    return canonical_runs_root


def _resolve_factor_output_directory(
    paths: ResolvedPaths, output_root: Path, factor_id: str
) -> Path:
    data_root = paths.data_root.resolve(strict=True)
    factor_directory = (output_root / factor_id).resolve(strict=False)
    if not factor_directory.is_relative_to(data_root):
        raise ValueError("factor output directory must remain below A_SHARE_DATA_ROOT")
    return factor_directory


def _validate_catalog(paths: ResolvedPaths) -> None:
    for path in (
        paths.daily_panel,
        paths.pit_csi300,
        paths.csi300_open,
        paths.open_eligibility,
    ):
        if not path.is_file():
            raise FileNotFoundError(f"Required private catalog input is missing: {path.name}")


def _validate_required_fields(daily_panel: Path, definition: FactorDefinition) -> None:
    columns = set(pd.read_parquet(daily_panel, columns=[]).columns)
    if not columns:
        import pyarrow.parquet as parquet

        columns = set(parquet.read_schema(daily_panel).names)
    missing = set(definition.required_daily_fields).difference(columns)
    if missing:
        raise ValueError(
            f"Daily panel is missing fields required by {definition.factor_id}: "
            + ", ".join(sorted(missing))
        )


def _validate_factor_path_component(factor_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", factor_id):
        raise ValueError(f"Factor ID is unsafe for an output path: {factor_id!r}")


def _build_summary(
    *,
    run_id: str,
    created_at: datetime,
    definition: FactorDefinition,
    profile,
    paths: ResolvedPaths,
    profile_path: Path,
    start: str,
    end: str,
    decision: str,
    run_type: str,
) -> dict[str, object]:
    input_paths = {
        "profile": profile_path,
        "factor_registry": REGISTRY_PATH,
        "daily_panel": paths.daily_panel,
        "pit_csi300": paths.pit_csi300,
        "csi300_open": paths.csi300_open,
        "open_eligibility": paths.open_eligibility,
    }
    return {
        "schema_version": 1,
        "run_id": run_id,
        "created_at_utc": created_at.isoformat(),
        "factor_id": definition.factor_id,
        "decision": decision,
        "run_type": run_type,
        "date_range": {"start": str(start), "end": str(end)},
        "registry": {
            "factor_id": definition.factor_id,
            "formula_definition": definition.formula_definition,
            "required_daily_fields": list(definition.required_daily_fields),
            "signal_availability": definition.signal_availability,
            "economic_hypothesis": definition.economic_hypothesis,
            "pre_registered_direction": definition.pre_registered_direction,
            "status": definition.status,
        },
        "profile": asdict(profile),
        "input_sha256": {name: _sha256(path) for name, path in input_paths.items()},
        "git_revision": _git_revision(),
        "artifacts": list(REQUIRED_ARTIFACTS),
    }


def _run_type_for_profile(profile_path: Path) -> str:
    """Classify only the repository's frozen daily baseline as formal evidence."""
    return (
        "formal"
        if profile_path == _FROZEN_DAILY_BASELINE_PROFILE.resolve(strict=True)
        else "experimental"
    )


def _build_data_quality(panel: pd.DataFrame, horizons: tuple[int, ...]) -> pd.DataFrame:
    records: list[dict[str, object]] = [
        {"metric": "panel_rows", "value": len(panel)},
        {"metric": "signal_dates", "value": panel["signal_date"].nunique()},
        {"metric": "security_ids", "value": panel["security_id"].nunique()},
        {"metric": "basic_eligible_rows", "value": int(panel["basic_eligible"].sum())},
        {
            "metric": "tradable_next_open_rows",
            "value": int(panel["tradable_next_open"].sum()),
        },
        {
            "metric": "finite_directed_score_rows",
            "value": int(np.isfinite(panel["directed_score"].to_numpy(dtype=float)).sum()),
        },
    ]
    for horizon in horizons:
        label = pd.to_numeric(panel[f"label_excess_o2o_{horizon}d"], errors="coerce")
        records.append(
            {
                "metric": f"finite_label_{horizon}d_rows",
                "value": int(np.isfinite(label.to_numpy(dtype=float)).sum()),
            }
        )
    return pd.DataFrame.from_records(records, columns=["metric", "value"])


def _publish_atomically(
    factor_directory: Path,
    *,
    run_id: str,
    summary: dict[str, object],
    data_quality: pd.DataFrame,
    ic_evaluation,
    portfolio_simulations,
) -> Path:
    factor_directory.mkdir(parents=True, exist_ok=True)
    final_directory = factor_directory / run_id
    staging_directory = Path(
        tempfile.mkdtemp(prefix=f".{run_id}-", dir=factor_directory)
    )
    try:
        write_report_bundle(
            staging_directory,
            summary=summary,
            data_quality=data_quality,
            ic_evaluation=ic_evaluation,
            portfolio_simulations=portfolio_simulations,
        )
        missing = [
            artifact for artifact in REQUIRED_ARTIFACTS if not (staging_directory / artifact).is_file()
        ]
        if missing:
            raise RuntimeError("Report bundle is incomplete: " + ", ".join(missing))
        staging_directory.replace(final_directory)
    except BaseException:
        shutil.rmtree(staging_directory, ignore_errors=True)
        raise
    return final_directory


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_revision() -> str | None:
    repository_root = Path(__file__).resolve().parents[3]
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factor", required=True, help="Registered factor ID, for example REV5")
    parser.add_argument("--profile", required=True, type=Path, help="Frozen YAML research profile")
    parser.add_argument("--start", required=True, help="First signal date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="Last signal date (YYYY-MM-DD)")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Canonical run root only (A_SHARE_DATA_ROOT/runs; default: that path)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    output = run_factor(
        arguments.factor,
        arguments.profile,
        arguments.start,
        arguments.end,
        arguments.output_root,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
