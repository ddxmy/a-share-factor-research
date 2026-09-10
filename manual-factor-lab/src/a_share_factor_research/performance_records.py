"""Append-only private scoreboards derived from complete immutable run bundles."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any
from uuid import uuid4

import duckdb
import pandas as pd

from .reporting import REQUIRED_ARTIFACTS


_HORIZONS = (1, 5, 20)
_STATE_DIRECTORY_NAME = ".performance_records"
_GENERATIONS_DIRECTORY_NAME = "generations"
_CURRENT_GENERATION_NAME = "current"
_LOCK_FILE_NAME = ".performance_records.lock"
_IC_METRICS = (
    "n_observations",
    "mean_pearson_ic",
    "pearson_icir",
    "mean_rank_ic",
    "rank_icir",
    "hac_t_stat",
    "hac_one_sided_p_value",
)
_PORTFOLIO_METRICS = (
    "n_periods",
    "n_evaluable_periods",
    "annualized_return",
    "volatility",
    "sharpe",
    "max_drawdown",
)
_BASE_COLUMNS = (
    "schema_version",
    "factor_id",
    "run_id",
    "created_at",
    "decision",
    "run_type",
    "start_date",
    "end_date",
    "relative_run_path",
    "git_revision",
    "registry_status",
    "pre_registered_direction",
    "profile_top_k",
    "profile_one_way_cost_bps",
    "profile_json",
    "registry_json",
    "input_sha256_json",
    "portfolio",
    "portfolio_kind",
    "is_diagnostic",
)


def _scoreboard_columns() -> list[str]:
    columns = list(_BASE_COLUMNS)
    for horizon in _HORIZONS:
        for metric in _IC_METRICS:
            columns.append(f"{metric}_{horizon}d")
        for metric in _IC_METRICS:
            columns.append(f"tradable_{metric}_{horizon}d")
        columns.append(f"top_k_mean_turnover_{horizon}d")
        for return_type in ("gross", "net"):
            for metric in _PORTFOLIO_METRICS:
                columns.append(f"top_k_{return_type}_{metric}_{horizon}d")
    return columns


SCOREBOARD_COLUMNS = _scoreboard_columns()


def record_successful_run(data_root: Path, run_directory: Path) -> None:
    """Append one validated immutable run and refresh its latest factor card.

    Parquet, DuckDB, and every factor card are built in one immutable generation.
    A single atomic ``current`` pointer switch makes that generation visible.
    """
    root = _resolved_data_root(data_root)
    run_path = _resolved_run_directory(root, run_directory)
    summary_path = _required_run_file(run_path, "summary.json")
    summary = _load_summary(summary_path)
    _validate_declared_artifacts(run_path, summary)
    ic_path = _required_run_file(run_path, "ic_summary.csv")
    portfolio_path = _required_run_file(run_path, "portfolio_summary.csv")
    factor_id, run_id = _validated_identity(summary, run_path)
    record = _build_record(
        root=root,
        run_path=run_path,
        summary=summary,
        ic_summary=pd.read_csv(ic_path),
        portfolio_summary=pd.read_csv(portfolio_path),
    )

    with _exclusive_records_lock(root):
        existing = _load_scoreboard_unlocked(root)
        if not existing.empty:
            duplicate = existing["factor_id"].eq(factor_id) & existing["run_id"].eq(
                run_id
            )
            if duplicate.any():
                raise ValueError(
                    f"Scoreboard duplicate rejected for factor_id={factor_id!r}, "
                    f"run_id={run_id!r}."
                )
        new_record = pd.DataFrame([record], columns=SCOREBOARD_COLUMNS)
        combined = (
            new_record
            if existing.empty
            else pd.concat([existing, new_record], ignore_index=True)
        )
        combined = combined.loc[:, SCOREBOARD_COLUMNS]

        generation = _write_generation(root, combined)
        created_links = _ensure_public_links(root)
        had_current_generation = _current_link(root).is_symlink()
        try:
            _activate_generation(root, generation)
        except BaseException:
            if not had_current_generation:
                _remove_new_public_links(created_links)
            raise


def load_scoreboard(data_root: Path) -> pd.DataFrame:
    """Load the private Parquet scoreboard, or its empty canonical schema."""
    root = _resolved_data_root(data_root)
    return _load_scoreboard_unlocked(root)


def _load_scoreboard_unlocked(root: Path) -> pd.DataFrame:
    generation = _resolved_current_generation(root)
    if generation is None:
        scoreboard_path = root / "factor_scoreboard.parquet"
        if scoreboard_path.is_symlink():
            raise ValueError("Managed scoreboard link exists without a committed generation.")
    else:
        _validate_public_links(root)
        scoreboard_path = generation / "factor_scoreboard.parquet"
    if not scoreboard_path.exists():
        return pd.DataFrame(columns=SCOREBOARD_COLUMNS)
    if not scoreboard_path.is_file():
        raise ValueError("factor_scoreboard.parquet must be a regular file.")
    scoreboard = pd.read_parquet(scoreboard_path)
    missing = set(SCOREBOARD_COLUMNS).difference(scoreboard.columns)
    extra = set(scoreboard.columns).difference(SCOREBOARD_COLUMNS)
    if missing or extra:
        details = []
        if missing:
            details.append("missing: " + ", ".join(sorted(missing)))
        if extra:
            details.append("unexpected: " + ", ".join(sorted(extra)))
        raise ValueError("Scoreboard schema mismatch (" + "; ".join(details) + ").")
    return scoreboard.loc[:, SCOREBOARD_COLUMNS]


def _resolved_data_root(data_root: Path) -> Path:
    root = Path(data_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("data_root must be an existing directory.")
    return root


def _resolved_run_directory(root: Path, run_directory: Path) -> Path:
    runs_entry = root / "runs"
    if runs_entry.is_symlink():
        raise ValueError("The private runs root must not be a symlink.")
    try:
        runs_root = runs_entry.resolve(strict=True)
    except FileNotFoundError:
        raise ValueError(
            "run_directory must resolve to data_root/runs/<factor_id>/<run_id>."
        ) from None
    if not runs_root.is_relative_to(root) or runs_root.parent != root:
        raise ValueError("The resolved runs root must remain strictly below data_root.")
    run_path = Path(run_directory).expanduser().resolve(strict=True)
    if not runs_root.is_dir() or not run_path.is_dir():
        raise ValueError("run_directory must be a directory below data_root/runs.")
    if not run_path.is_relative_to(runs_root) or run_path.parent.parent != runs_root:
        raise ValueError(
            "run_directory must resolve to data_root/runs/<factor_id>/<run_id>."
        )
    return run_path


def _required_run_file(run_path: Path, relative_name: str) -> Path:
    candidate = run_path / relative_name
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Complete run bundle is missing {relative_name}: {candidate}"
        ) from None
    if not resolved.is_relative_to(run_path) or not resolved.is_file():
        raise ValueError(f"Run artifact must be a contained regular file: {relative_name}.")
    return resolved


def _load_summary(summary_path: Path) -> dict[str, Any]:
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"summary.json is not valid JSON: {error.msg}.") from error
    if not isinstance(summary, dict):
        raise ValueError("summary.json must contain a JSON object.")
    return summary


def _validate_declared_artifacts(run_path: Path, summary: dict[str, Any]) -> None:
    artifacts = summary.get("artifacts")
    if (
        not isinstance(artifacts, list)
        or not all(isinstance(item, str) for item in artifacts)
        or tuple(artifacts) != tuple(REQUIRED_ARTIFACTS)
    ):
        raise ValueError(
            "summary.json artifacts must exactly equal the production REQUIRED_ARTIFACTS manifest."
        )
    for artifact in REQUIRED_ARTIFACTS:
        if not artifact or Path(artifact).is_absolute() or ".." in Path(artifact).parts:
            raise ValueError(f"Unsafe declared run artifact: {artifact!r}.")
        _required_run_file(run_path, artifact)


def _validated_identity(summary: dict[str, Any], run_path: Path) -> tuple[str, str]:
    factor_id = _required_text(summary, "factor_id")
    run_id = _required_text(summary, "run_id")
    for name, value in (("factor_id", factor_id), ("run_id", run_id)):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
            raise ValueError(f"summary.json {name} is unsafe for a path: {value!r}.")
    if factor_id != run_path.parent.name or run_id != run_path.name:
        raise ValueError("summary factor_id/run_id must match the immutable run path.")
    return factor_id, run_id


def _build_record(
    *,
    root: Path,
    run_path: Path,
    summary: dict[str, Any],
    ic_summary: pd.DataFrame,
    portfolio_summary: pd.DataFrame,
) -> dict[str, Any]:
    factor_id, run_id = _validated_identity(summary, run_path)
    created_at = pd.to_datetime(summary.get("created_at_utc"), errors="coerce", utc=True)
    if pd.isna(created_at):
        raise ValueError("summary.json created_at_utc must be a parseable timestamp.")
    date_range = _required_mapping(summary, "date_range")
    registry = _required_mapping(summary, "registry")
    profile = _required_mapping(summary, "profile")
    input_sha256 = _required_mapping(summary, "input_sha256")

    record: dict[str, Any] = {
        "schema_version": _required_integer(summary, "schema_version"),
        "factor_id": factor_id,
        "run_id": run_id,
        "created_at": pd.Timestamp(created_at),
        "decision": _required_text(summary, "decision"),
        "run_type": _required_choice(summary, "run_type", ("formal", "experimental")),
        "start_date": _required_text(date_range, "start", parent="date_range"),
        "end_date": _required_text(date_range, "end", parent="date_range"),
        "relative_run_path": run_path.relative_to(root).as_posix(),
        "git_revision": summary.get("git_revision"),
        "registry_status": _required_text(registry, "status", parent="registry"),
        "pre_registered_direction": _required_text(
            registry, "pre_registered_direction", parent="registry"
        ),
        "profile_top_k": _required_integer(profile, "top_k", parent="profile"),
        "profile_one_way_cost_bps": _required_number(
            profile, "one_way_cost_bps", parent="profile"
        ),
        "profile_json": _canonical_json(profile),
        "registry_json": _canonical_json(registry),
        "input_sha256_json": _canonical_json(input_sha256),
    }
    record.update(_extract_ic_metrics(ic_summary))
    record.update(_extract_portfolio_metrics(portfolio_summary))
    missing = set(SCOREBOARD_COLUMNS).difference(record)
    if missing:
        raise RuntimeError("Internal scoreboard fields are missing: " + ", ".join(sorted(missing)))
    return record


def _extract_ic_metrics(table: pd.DataFrame) -> dict[str, Any]:
    required = {"horizon_days", "eligibility", "sample", *_IC_METRICS}
    _require_columns(table, required, "ic_summary.csv")
    result: dict[str, Any] = {}
    for horizon in _HORIZONS:
        for eligibility in ("basic", "tradable"):
            selected = table.loc[
                table["horizon_days"].eq(horizon)
                & table["eligibility"].eq(eligibility)
                & table["sample"].eq("overlapping")
            ]
            row = _exactly_one(selected, f"overlapping {eligibility} {horizon}D IC")
            prefix = "" if eligibility == "basic" else "tradable_"
            for metric in _IC_METRICS:
                result[f"{prefix}{metric}_{horizon}d"] = _numeric_cell(
                    row[metric], f"{eligibility} {horizon}D {metric}"
                )
    return result


def _extract_portfolio_metrics(table: pd.DataFrame) -> dict[str, Any]:
    required = {
        "horizon_days",
        "portfolio",
        "portfolio_kind",
        "is_diagnostic",
        "return_type",
        "mean_turnover",
        *_PORTFOLIO_METRICS,
    }
    _require_columns(table, required, "portfolio_summary.csv")
    diagnostic = _as_boolean(table["is_diagnostic"], "portfolio_summary.csv is_diagnostic")
    executable = table.loc[table["portfolio_kind"].eq("top_k_long") & ~diagnostic].copy()
    if executable.empty:
        raise ValueError("portfolio_summary.csv has no executable top_k_long rows.")
    portfolios = executable["portfolio"].dropna().astype(str).unique().tolist()
    kinds = executable["portfolio_kind"].dropna().astype(str).unique().tolist()
    if len(portfolios) != 1 or kinds != ["top_k_long"]:
        raise ValueError("Executable Top-K rows must use one portfolio and top_k_long kind.")
    result: dict[str, Any] = {
        "portfolio": portfolios[0],
        "portfolio_kind": "top_k_long",
        "is_diagnostic": False,
    }
    for horizon in _HORIZONS:
        turnovers: list[int | float] = []
        for return_type in ("gross", "net"):
            selected = executable.loc[
                executable["horizon_days"].eq(horizon)
                & executable["return_type"].eq(return_type)
            ]
            row = _exactly_one(selected, f"executable Top-K {return_type} {horizon}D")
            for metric in _PORTFOLIO_METRICS:
                result[f"top_k_{return_type}_{metric}_{horizon}d"] = _numeric_cell(
                    row[metric], f"Top-K {return_type} {horizon}D {metric}"
                )
            turnovers.append(
                _numeric_cell(row["mean_turnover"], f"Top-K {return_type} {horizon}D mean turnover")
            )
        if turnovers[0] != turnovers[1]:
            raise ValueError(
                f"Gross and net Top-K mean turnover must agree for {horizon}D."
            )
        result[f"top_k_mean_turnover_{horizon}d"] = turnovers[0]
    return result


def _write_duckdb_mirror(destination: Path, scoreboard: pd.DataFrame) -> None:
    with duckdb.connect(str(destination)) as database:
        database.execute("BEGIN TRANSACTION")
        try:
            database.register("scoreboard_frame", scoreboard)
            database.execute(
                "CREATE TABLE factor_scoreboard AS SELECT * FROM scoreboard_frame"
            )
            database.execute("COMMIT")
        except BaseException:
            database.execute("ROLLBACK")
            raise


@contextmanager
def _exclusive_records_lock(root: Path):
    """Serialize the full append transaction across local processes."""
    lock_path = root / _LOCK_FILE_NAME
    if lock_path.is_symlink():
        raise ValueError("The performance-record lock file must not be a symlink.")
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        with os.fdopen(descriptor, "a+b") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except BaseException:
        # os.fdopen owns the descriptor after successful construction.
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _write_generation(root: Path, scoreboard: pd.DataFrame) -> Path:
    """Build and seal all reader-visible views in one immutable directory."""
    _, generations = _ensure_state_layout(root)
    generation_id = uuid4().hex
    staging = generations / f".staging-{generation_id}"
    generation = generations / generation_id
    staging.mkdir()
    try:
        scoreboard.to_parquet(staging / "factor_scoreboard.parquet", index=False)
        _write_duckdb_mirror(staging / "factor_scoreboard.duckdb", scoreboard)
        cards = staging / "factor_cards"
        cards.mkdir()
        formal_factor_ids = scoreboard.loc[
            scoreboard["run_type"].eq("formal"), "factor_id"
        ].astype(str).unique()
        for factor_id in sorted(formal_factor_ids):
            (cards / f"{factor_id}.html").write_text(
                _render_latest_factor_card(scoreboard, factor_id), encoding="utf-8"
            )
        os.replace(staging, generation)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return generation


def _activate_generation(root: Path, generation: Path) -> None:
    """Atomically commit one already-complete generation as the only current view."""
    state, generations = _ensure_state_layout(root)
    resolved_generation = generation.resolve(strict=True)
    if resolved_generation.parent != generations or not resolved_generation.is_dir():
        raise ValueError("Generation must be an immutable directory below generations.")
    temporary_link = state / f".current-{uuid4().hex}"
    temporary_link.symlink_to(
        Path(_GENERATIONS_DIRECTORY_NAME) / resolved_generation.name,
        target_is_directory=True,
    )
    try:
        os.replace(temporary_link, _current_link(root))
    finally:
        if temporary_link.is_symlink():
            temporary_link.unlink()


def _ensure_state_layout(root: Path) -> tuple[Path, Path]:
    state = root / _STATE_DIRECTORY_NAME
    if state.is_symlink():
        raise ValueError("Performance-record state directory must not be a symlink.")
    state.mkdir(exist_ok=True)
    if not state.is_dir():
        raise ValueError("Performance-record state path must be a directory.")
    state = state.resolve(strict=True)
    if state.parent != root:
        raise ValueError("Performance-record state must remain below data_root.")
    generations = state / _GENERATIONS_DIRECTORY_NAME
    if generations.is_symlink():
        raise ValueError("Performance-record generations directory must not be a symlink.")
    generations.mkdir(exist_ok=True)
    generations = generations.resolve(strict=True)
    if generations.parent != state or not generations.is_dir():
        raise ValueError("Performance-record generations must remain below state.")
    return state, generations


def _current_link(root: Path) -> Path:
    return root / _STATE_DIRECTORY_NAME / _CURRENT_GENERATION_NAME


def _resolved_current_generation(root: Path) -> Path | None:
    current = _current_link(root)
    if not os.path.lexists(current):
        return None
    if not current.is_symlink():
        raise ValueError("Current performance-record generation must be a symlink.")
    state = root / _STATE_DIRECTORY_NAME
    generations = state / _GENERATIONS_DIRECTORY_NAME
    if state.is_symlink() or generations.is_symlink():
        raise ValueError("Performance-record state paths must not be symlinks.")
    try:
        resolved_generations = generations.resolve(strict=True)
        generation = current.resolve(strict=True)
    except FileNotFoundError:
        raise ValueError("Current performance-record generation is incomplete.") from None
    if generation.parent != resolved_generations or not generation.is_dir():
        raise ValueError("Current generation must remain below the generations directory.")
    required = (
        generation / "factor_scoreboard.parquet",
        generation / "factor_scoreboard.duckdb",
        generation / "factor_cards",
    )
    if not required[0].is_file() or not required[1].is_file() or not required[2].is_dir():
        raise ValueError("Current performance-record generation is incomplete.")
    return generation


def _public_link_specs(root: Path) -> tuple[tuple[Path, str, bool], ...]:
    prefix = f"{_STATE_DIRECTORY_NAME}/{_CURRENT_GENERATION_NAME}"
    return (
        (
            root / "factor_scoreboard.parquet",
            f"{prefix}/factor_scoreboard.parquet",
            False,
        ),
        (
            root / "factor_scoreboard.duckdb",
            f"{prefix}/factor_scoreboard.duckdb",
            False,
        ),
        (root / "factor_cards", f"{prefix}/factor_cards", True),
    )


def _ensure_public_links(root: Path) -> tuple[Path, ...]:
    specs = _public_link_specs(root)
    for path, target, _ in specs:
        if os.path.lexists(path) and (
            not path.is_symlink() or os.readlink(path) != target
        ):
            raise ValueError(
                f"Private output path is not a managed generation link: {path.name}."
            )

    created: list[Path] = []
    temporary_links: list[Path] = []
    try:
        for path, target, is_directory in specs:
            if path.is_symlink():
                continue
            temporary = root / f".{path.name}-link-{uuid4().hex}"
            temporary.symlink_to(target, target_is_directory=is_directory)
            temporary_links.append(temporary)
            os.replace(temporary, path)
            created.append(path)
        return tuple(created)
    except BaseException:
        _remove_new_public_links(tuple(created))
        raise
    finally:
        for temporary in temporary_links:
            if temporary.is_symlink():
                temporary.unlink()


def _validate_public_links(root: Path) -> None:
    for path, target, _ in _public_link_specs(root):
        if not path.is_symlink() or os.readlink(path) != target:
            raise ValueError(f"Private output generation link is invalid: {path.name}.")


def _remove_new_public_links(paths: tuple[Path, ...]) -> None:
    for path in reversed(paths):
        if path.is_symlink():
            path.unlink()


def _render_latest_factor_card(scoreboard: pd.DataFrame, factor_id: str) -> str:
    factor_rows = scoreboard.loc[
        scoreboard["factor_id"].eq(factor_id) & scoreboard["run_type"].eq("formal")
    ].copy()
    if factor_rows.empty:
        raise ValueError(f"Factor {factor_id!r} has no formal runs for a factor card.")
    factor_rows["_parsed_created_at"] = pd.to_datetime(
        factor_rows["created_at"], errors="coerce", utc=True
    )
    if factor_rows["_parsed_created_at"].isna().any():
        raise ValueError("Scoreboard contains an invalid created_at timestamp.")
    row = factor_rows.sort_values(
        ["_parsed_created_at", "run_id"], kind="mergesort"
    ).iloc[-1]

    ic_rows = []
    portfolio_rows = []
    for horizon in _HORIZONS:
        ic_rows.extend(
            [
                {
                    "Horizon": f"{horizon}D",
                    "Eligibility": "basic",
                    "Mean IC": row[f"mean_pearson_ic_{horizon}d"],
                    "Mean Rank IC": row[f"mean_rank_ic_{horizon}d"],
                    "ICIR": row[f"pearson_icir_{horizon}d"],
                    "Rank ICIR": row[f"rank_icir_{horizon}d"],
                },
                {
                    "Horizon": f"{horizon}D",
                    "Eligibility": "tradable",
                    "Mean IC": row[f"tradable_mean_pearson_ic_{horizon}d"],
                    "Mean Rank IC": row[f"tradable_mean_rank_ic_{horizon}d"],
                    "ICIR": row[f"tradable_pearson_icir_{horizon}d"],
                    "Rank ICIR": row[f"tradable_rank_icir_{horizon}d"],
                },
            ]
        )
        for return_type in ("gross", "net"):
            portfolio_rows.append(
                {
                    "Horizon": f"{horizon}D",
                    "Return type": return_type,
                    "Annualized return": row[
                        f"top_k_{return_type}_annualized_return_{horizon}d"
                    ],
                    "Volatility": row[f"top_k_{return_type}_volatility_{horizon}d"],
                    "Sharpe": row[f"top_k_{return_type}_sharpe_{horizon}d"],
                    "Max drawdown": row[
                        f"top_k_{return_type}_max_drawdown_{horizon}d"
                    ],
                }
            )
    ic_table = pd.DataFrame(ic_rows).to_html(index=False, border=0)
    portfolio_table = pd.DataFrame(portfolio_rows).to_html(index=False, border=0)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(str(row['factor_id']))} latest factor card</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 1050px; line-height: 1.45; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; }}
    th, td {{ border: 1px solid #ddd; padding: 0.4rem; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
  </style>
</head>
<body>
  <h1>{escape(str(row['factor_id']))} latest factor card</h1>
  <p><strong>Run ID:</strong> {escape(str(row['run_id']))}</p>
  <p><strong>Decision:</strong> {escape(str(row['decision']))}</p>
  <p><strong>Run type:</strong> {escape(str(row['run_type']))}</p>
  <p><strong>Signal window:</strong> {escape(str(row['start_date']))} to {escape(str(row['end_date']))}</p>
  <p><strong>Immutable run:</strong> {escape(str(row['relative_run_path']))}</p>
  <h2>IC and Rank IC by horizon</h2>
  {ic_table}
  <h2>Long-only Top-K metrics</h2>
  <p>Portfolio: {escape(str(row['portfolio']))}; kind: {escape(str(row['portfolio_kind']))}; diagnostics excluded.</p>
  {portfolio_table}
</body>
</html>
"""


def _require_columns(table: pd.DataFrame, required: set[str], filename: str) -> None:
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(f"{filename} is missing columns: " + ", ".join(sorted(missing)))


def _exactly_one(table: pd.DataFrame, label: str) -> pd.Series:
    if len(table) != 1:
        raise ValueError(f"Run bundle must contain exactly one {label} row; found {len(table)}.")
    return table.iloc[0]


def _as_boolean(series: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        if series.isna().any():
            raise ValueError(f"{label} contains a missing value.")
        return series.astype(bool)
    normalized = series.astype("string").str.strip().str.lower()
    invalid = ~normalized.isin(["true", "false"])
    if invalid.any():
        raise ValueError(f"{label} must contain only true or false values.")
    return normalized.eq("true")


def _numeric_cell(value: Any, label: str) -> int | float:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        raise ValueError(f"Run bundle metric is not numeric: {label}.")
    return numeric.item() if hasattr(numeric, "item") else numeric


def _required_mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"summary.json {key} must be an object.")
    return value


def _required_text(
    mapping: dict[str, Any], key: str, *, parent: str = "summary.json"
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{parent} {key} must be a non-empty string.")
    return value


def _required_choice(
    mapping: dict[str, Any], key: str, choices: tuple[str, ...]
) -> str:
    value = _required_text(mapping, key)
    if value not in choices:
        raise ValueError(f"summary.json {key} must be one of: {', '.join(choices)}.")
    return value


def _required_integer(
    mapping: dict[str, Any], key: str, *, parent: str = "summary.json"
) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{parent} {key} must be an integer.")
    return value


def _required_number(
    mapping: dict[str, Any], key: str, *, parent: str = "summary.json"
) -> int | float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{parent} {key} must be numeric.")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
