#!/usr/bin/env python3
"""Evaluate locked G4/G5 out-of-sample prediction panels without retraining."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from alpha158_research.evaluation import (  # noqa: E402
    newey_west_mean_test,
    rank_ic_summary,
    validate_common_prediction_panel,
    weekly_quintile_returns,
)
from alpha158_research.modeling import weekly_rank_ic  # noqa: E402
from alpha158_research.public_config import require_data_root  # noqa: E402


CONFIG_PATH = PROJECT_DIR / "config/research_v1.json"
DATA_ROOT = require_data_root()
OUTPUT_ROOT = DATA_ROOT / "alpha158/outputs"
G4_DIR = OUTPUT_ROOT / "G4"
G5_DIR = OUTPUT_ROOT / "G5"
RIDGE_PREDICTIONS = G4_DIR / "ridge_test_predictions_v1.parquet"
LIGHTGBM_PREDICTIONS = G5_DIR / "lightgbm_test_predictions_v1.parquet"
ARTIFACT_DIR = OUTPUT_ROOT / "G6"
WEEKLY_IC = ARTIFACT_DIR / "weekly_rank_ic_v1.parquet"
IC_SUMMARY = ARTIFACT_DIR / "rank_ic_summary_v1.parquet"
IC_DIFFERENCE = ARTIFACT_DIR / "model_ic_difference_newey_west_v1.parquet"
QUINTILE_WEEKLY = ARTIFACT_DIR / "quintile_weekly_returns_v1.parquet"
QUINTILE_SUMMARY = ARTIFACT_DIR / "quintile_summary_v1.parquet"
AUDIT = ARTIFACT_DIR / "g6_run_audit_v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_json_stable(payload: dict[str, object], path: Path) -> None:
    rendered = render_json(payload)
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise FileExistsError(f"Refusing to overwrite non-identical audit: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def write_parquet_stable(frame: pd.DataFrame, path: Path, keys: list[str]) -> None:
    expected = frame.sort_values(keys).reset_index(drop=True)
    if path.exists():
        actual = pd.read_parquet(path).sort_values(keys).reset_index(drop=True)
        if list(actual.columns) != list(expected.columns) or not actual.equals(expected):
            raise FileExistsError(f"Refusing to overwrite non-identical artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    expected.to_parquet(path, index=False)


def summarize_rank_ic(weekly: pd.DataFrame) -> pd.DataFrame:
    """Summarize each model-score series over full and calendar-year samples."""

    records: list[dict[str, object]] = []
    for (model, score_type), group in weekly.groupby(["model", "score_type"], sort=True):
        records.append(
            {
                "model": model,
                "score_type": score_type,
                "period": "full_2021_2025",
                **rank_ic_summary(group),
            }
        )
        for year, year_group in group.groupby(group["signal_date"].dt.year, sort=True):
            records.append(
                {
                    "model": model,
                    "score_type": score_type,
                    "period": str(int(year)),
                    **rank_ic_summary(year_group),
                }
            )
    return pd.DataFrame(records)


def summarize_quintiles(weekly: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for (model, score_type, quintile), group in weekly.groupby(
        ["model", "score_type", "quintile"], sort=True
    ):
        returns = group["mean_excess_return"].to_numpy(dtype=float)
        records.append(
            {
                "model": model,
                "score_type": score_type,
                "quintile": quintile,
                "weeks": int(len(returns)),
                "mean_excess_return": float(returns.mean()),
                "std_excess_return": float(returns.std(ddof=1)),
                "positive_ratio": float((returns > 0).mean()),
            }
        )
    return pd.DataFrame(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Compute but do not write artifacts")
    args = parser.parse_args()
    ridge = pd.read_parquet(RIDGE_PREDICTIONS)
    lightgbm = pd.read_parquet(LIGHTGBM_PREDICTIONS)
    for frame in (ridge, lightgbm):
        frame["signal_date"] = pd.to_datetime(frame["signal_date"])
    panel = validate_common_prediction_panel(ridge, lightgbm)
    years = sorted(panel["signal_date"].dt.year.unique().tolist())
    if years != [2021, 2022, 2023, 2024, 2025]:
        raise ValueError(f"G6 expected 2021–2025 locked tests, received {years}")

    weekly_ic_rows: list[pd.DataFrame] = []
    quintile_rows: list[pd.DataFrame] = []
    score_columns = {
        ("ridge", "raw"): "raw_prediction_score_ridge",
        ("ridge", "neutralized"): "neutralized_prediction_score_ridge",
        ("lightgbm", "raw"): "raw_prediction_score_lightgbm",
        ("lightgbm", "neutralized"): "neutralized_prediction_score_lightgbm",
    }
    for (model, score_type), score_column in score_columns.items():
        weekly_ic = weekly_rank_ic(panel, score_column)
        weekly_ic["model"] = model
        weekly_ic["score_type"] = score_type
        weekly_ic_rows.append(weekly_ic)
        quintiles = weekly_quintile_returns(panel, score_column)
        quintiles["model"] = model
        quintiles["score_type"] = score_type
        quintile_rows.append(quintiles)

    weekly_ic = pd.concat(weekly_ic_rows, ignore_index=True).sort_values(
        ["model", "score_type", "signal_date"]
    ).reset_index(drop=True)
    if not weekly_ic.groupby(["model", "score_type"]).size().eq(256).all():
        raise ValueError("every model-score series must contain exactly 256 weekly Rank IC values")
    if not np.isfinite(weekly_ic["rank_ic"].to_numpy(dtype=float)).all():
        raise ValueError("G6 weekly Rank IC contains non-finite values")
    ic_summary = summarize_rank_ic(weekly_ic).sort_values(
        ["model", "score_type", "period"]
    ).reset_index(drop=True)
    difference_rows: list[dict[str, object]] = []
    for score_type in ("raw", "neutralized"):
        pivot = weekly_ic.loc[weekly_ic["score_type"].eq(score_type)].pivot(
            index="signal_date", columns="model", values="rank_ic"
        )
        if set(pivot.columns) != {"ridge", "lightgbm"} or len(pivot) != 256:
            raise ValueError("paired IC comparison requires both models on all 256 same dates")
        difference = pivot["lightgbm"] - pivot["ridge"]
        difference_rows.append(
            {
                "score_type": score_type,
                "comparison": "lightgbm_minus_ridge",
                **newey_west_mean_test(difference.to_numpy(), max_lag=4),
            }
        )
    ic_difference = pd.DataFrame(difference_rows).sort_values("score_type").reset_index(drop=True)
    quintile_weekly = pd.concat(quintile_rows, ignore_index=True).sort_values(
        ["model", "score_type", "signal_date", "quintile"]
    ).reset_index(drop=True)
    if not np.isfinite(quintile_weekly["mean_excess_return"].to_numpy(dtype=float)).all():
        raise ValueError("G6 quintile returns contain non-finite values")
    quintile_summary = summarize_quintiles(quintile_weekly).sort_values(
        ["model", "score_type", "quintile"]
    ).reset_index(drop=True)

    audit = {
        "stage": "G6_locked_out_of_sample_signal_evaluation",
        "dry_run": args.dry_run,
        "method": {
            "evaluation_years": years,
            "weekly_rank_ic": "Pearson_correlation_of_average_score_and_target_ranks_with_equal_signal_date_weight",
            "icir_standard_deviation_ddof": 1,
            "newey_west": {"max_lag": 4, "kernel": "Bartlett", "p_value": "two_sided_normal_approximation"},
            "quintiles": "equal_count_score_rank_Q1_to_Q5_with_frictionless_Q5_minus_Q1_diagnostic",
            "tradability_claim": "not_evaluated_until_G7",
        },
        "input_lineage": {
            "research_config_sha256": sha256(CONFIG_PATH),
            "ridge_predictions_sha256": sha256(RIDGE_PREDICTIONS),
            "lightgbm_predictions_sha256": sha256(LIGHTGBM_PREDICTIONS),
            "common_rows": int(len(panel)),
            "common_signal_dates": int(panel["signal_date"].nunique()),
            "duplicate_common_keys": int(panel.duplicated(["signal_date", "con_code"]).sum()),
        },
        "artifacts": {
            "weekly_rank_ic": str(WEEKLY_IC),
            "rank_ic_summary": str(IC_SUMMARY),
            "model_ic_difference_newey_west": str(IC_DIFFERENCE),
            "quintile_weekly_returns": str(QUINTILE_WEEKLY),
            "quintile_summary": str(QUINTILE_SUMMARY),
            "audit": str(AUDIT),
        },
    }
    if not args.dry_run:
        write_parquet_stable(weekly_ic, WEEKLY_IC, ["model", "score_type", "signal_date"])
        write_parquet_stable(ic_summary, IC_SUMMARY, ["model", "score_type", "period"])
        write_parquet_stable(ic_difference, IC_DIFFERENCE, ["score_type"])
        write_parquet_stable(quintile_weekly, QUINTILE_WEEKLY, ["model", "score_type", "signal_date", "quintile"])
        write_parquet_stable(quintile_summary, QUINTILE_SUMMARY, ["model", "score_type", "quintile"])
        write_json_stable(audit, AUDIT)
    print(render_json(audit))
    print("\nFull-sample Rank IC summary:\n", ic_summary.loc[ic_summary["period"].eq("full_2021_2025")].to_string(index=False))
    print("\nPaired LightGBM minus Ridge IC:\n", ic_difference.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
