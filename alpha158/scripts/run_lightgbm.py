#!/usr/bin/env python3
"""Run the frozen LightGBM baseline after G5 pipeline helpers are completed."""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import product
from pathlib import Path
import sys

import lightgbm
import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from alpha158_research.modeling import (  # noqa: E402
    fit_lightgbm_candidate,
    fit_lightgbm_fixed_iterations,
    ic_statistics,
    neutralize_scores,
    weekly_equal_weights,
    weekly_rank_ic,
)
from alpha158_research.public_config import require_data_root  # noqa: E402


CONFIG_PATH = PROJECT_DIR / "config/research_v1.json"
DATA_ROOT = require_data_root()
INPUT_ROOT = DATA_ROOT / "alpha158/inputs"
OUTPUT_ROOT = DATA_ROOT / "alpha158/outputs"
G2_CATALOG = INPUT_ROOT / "G2/alpha158_catalog.csv"
G3_DIR = INPUT_ROOT / "G3"
G3_MODEL_ROOT = G3_DIR / "weekly_model_panel_v1"
G3_FOLD_ASSIGNMENTS = G3_DIR / "fold_assignments_v1.parquet"
G3_LABEL_AUDIT = G3_DIR / "label_audit_v1.json"
ARTIFACT_DIR = OUTPUT_ROOT / "G5"
VALIDATION_SUMMARY = ARTIFACT_DIR / "lightgbm_validation_summary_v1.parquet"
VALIDATION_IC = ARTIFACT_DIR / "lightgbm_validation_weekly_rank_ic_v1.parquet"
TEST_PREDICTIONS = ARTIFACT_DIR / "lightgbm_test_predictions_v1.parquet"
TEST_IC = ARTIFACT_DIR / "lightgbm_test_weekly_rank_ic_v1.parquet"
FEATURE_IMPORTANCE = ARTIFACT_DIR / "lightgbm_feature_importance_v1.parquet"
AUDIT = ARTIFACT_DIR / "lightgbm_run_audit_v1.json"


def candidate_parameter_grid(
    lightgbm_config: dict,
    *,
    random_seed: int,
) -> list[dict[str, float | int]]:
    """Expand only the frozen four-axis LightGBM candidate grid."""

    shared = {
        "feature_fraction": float(lightgbm_config["feature_fraction"]),
        "bagging_fraction": float(lightgbm_config["bagging_fraction"]),
        "bagging_freq": int(lightgbm_config["bagging_freq"]),
        "max_boost_rounds": int(lightgbm_config["max_boost_rounds"]),
        "early_stopping_rounds": int(lightgbm_config["early_stopping_rounds"]),
        "seed": int(random_seed),
        "num_threads": int(lightgbm_config["num_threads"]),
        "deterministic": bool(lightgbm_config["deterministic"]),
    }
    return [
        {
            **shared,
            "num_leaves": int(num_leaves),
            "learning_rate": float(learning_rate),
            "min_data_in_leaf": int(min_data_in_leaf),
            "lambda_l2": float(lambda_l2),
        }
        for num_leaves, learning_rate, min_data_in_leaf, lambda_l2 in product(
            lightgbm_config["num_leaves_grid"],
            lightgbm_config["learning_rate_grid"],
            lightgbm_config["min_data_in_leaf_grid"],
            lightgbm_config["lambda_l2_grid"],
        )
    ]


def choose_lightgbm_candidate(summary: pd.DataFrame) -> pd.Series:
    """Apply frozen validation and lower-tree-complexity tie breakers."""

    required = {
        "candidate_id",
        "mean_rank_ic",
        "rank_icir",
        "num_leaves",
        "min_data_in_leaf",
        "lambda_l2",
        "learning_rate",
    }
    if summary.empty or not required.issubset(summary.columns):
        raise ValueError("LightGBM candidate summary is incomplete")
    return summary.sort_values(
        [
            "mean_rank_ic",
            "rank_icir",
            "num_leaves",
            "min_data_in_leaf",
            "lambda_l2",
            "learning_rate",
            "candidate_id",
        ],
        ascending=[False, False, True, False, False, False, True],
        kind="stable",
    ).iloc[0]


def sha256(path: Path) -> str:
    """Return a reproducible fingerprint for an input artifact."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_json_stable(payload: dict[str, object], path: Path) -> None:
    """Write only a new or byte-identical audit, preserving prior evidence."""

    rendered = render_json(payload)
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise FileExistsError(f"Refusing to overwrite non-identical audit: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def write_parquet_stable(frame: pd.DataFrame, path: Path, keys: list[str]) -> None:
    """Write only a new or identical sorted table, never overwriting results."""

    expected = frame.sort_values(keys).reset_index(drop=True)
    if path.exists():
        actual = pd.read_parquet(path).sort_values(keys).reset_index(drop=True)
        if list(actual.columns) != list(expected.columns) or not actual.equals(expected):
            raise FileExistsError(f"Refusing to overwrite non-identical artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    expected.to_parquet(path, index=False)


def load_inputs() -> tuple[dict, pd.DataFrame, pd.DataFrame, list[str]]:
    """Load the frozen G2/G3 inputs and enforce their basic invariants."""

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    feature_names = pd.read_csv(G2_CATALOG)["name"].tolist()
    paths = sorted(G3_MODEL_ROOT.glob("year=*/part-0000.parquet"))
    if len(paths) != 11:
        raise FileNotFoundError("G3 model panel must contain 2015–2025 partitions")
    panel = pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True)
    assignments = pd.read_parquet(G3_FOLD_ASSIGNMENTS)
    for frame in (panel, assignments):
        for column in ("signal_date", "entry_date", "label_end_date"):
            frame[column] = pd.to_datetime(frame[column])
    if panel.duplicated(["signal_date", "con_code"]).any():
        raise ValueError("G3 model panel contains duplicate keys")
    if not panel["label_eligible"].astype(bool).all():
        raise ValueError("G3 model panel must contain only label-eligible rows")
    if len(feature_names) != 158 or not set(feature_names).issubset(panel.columns):
        raise ValueError("G3 model panel does not contain exactly Alpha158 inputs")
    if not np.isfinite(panel[feature_names].to_numpy(dtype=float)).all():
        raise ValueError("G3 feature matrix contains non-finite values")
    return config, panel, assignments, feature_names


def fold_slice(
    panel: pd.DataFrame, assignments: pd.DataFrame, fold: int, role: str
) -> pd.DataFrame:
    """Return one leakage-controlled fold role from G3's frozen assignments."""

    keys = assignments.loc[
        assignments["fold"].eq(fold)
        & assignments["role"].eq(role)
        & assignments["included_for_model"].astype(bool),
        ["signal_date", "con_code"],
    ]
    output = keys.merge(
        panel, on=["signal_date", "con_code"], how="inner", validate="one_to_one"
    )
    if len(output) != len(keys):
        raise ValueError(f"Fold {fold} {role} keys are not all present in model panel")
    return output.sort_values(["signal_date", "con_code"]).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Fit and validate without writing artifacts"
    )
    args = parser.parse_args()
    config, panel, assignments, features = load_inputs()
    lightgbm_config = config["models"]["lightgbm"]
    candidates = candidate_parameter_grid(
        lightgbm_config, random_seed=int(config["models"]["random_seed"])
    )
    target = "target_excess_return"
    validation_summary_rows: list[dict[str, object]] = []
    validation_ic_rows: list[pd.DataFrame] = []
    test_prediction_rows: list[pd.DataFrame] = []
    test_ic_rows: list[pd.DataFrame] = []
    importance_rows: list[dict[str, object]] = []
    fold_audit: list[dict[str, object]] = []

    for fold in range(1, 6):
        train = fold_slice(panel, assignments, fold, "train")
        validation = fold_slice(panel, assignments, fold, "validation")
        test = fold_slice(panel, assignments, fold, "test")
        if not (train["label_end_date"] < validation["signal_date"].min()).all():
            raise ValueError(f"Fold {fold} train purge gate failed")
        if not (validation["label_end_date"] < test["signal_date"].min()).all():
            raise ValueError(f"Fold {fold} validation purge gate failed")
        train_weight = weekly_equal_weights(train)
        for candidate_id, parameters in enumerate(candidates):
            print(f"G5 fold {fold}/5, candidate {candidate_id + 1}/{len(candidates)}", flush=True)
            model, best_iteration = fit_lightgbm_candidate(
                train, validation, features, target, train_weight, parameters
            )
            validation_scores = validation[["signal_date", "con_code", target]].copy()
            validation_scores["raw_prediction_score"] = model.predict(
                validation[features], num_iteration=best_iteration
            )
            weekly_ic = weekly_rank_ic(validation_scores, "raw_prediction_score", target)
            weekly_ic["fold"] = fold
            weekly_ic["candidate_id"] = candidate_id
            validation_ic_rows.append(weekly_ic)
            validation_summary_rows.append(
                {
                    "fold": fold,
                    "candidate_id": candidate_id,
                    "best_iteration": best_iteration,
                    **parameters,
                    **ic_statistics(weekly_ic),
                }
            )

        fold_summary = pd.DataFrame(validation_summary_rows).query("fold == @fold")
        selected = choose_lightgbm_candidate(fold_summary)
        selected_candidate_id = int(selected["candidate_id"])
        selected_parameters = candidates[selected_candidate_id]
        selected_best_iteration = int(selected["best_iteration"])
        refit_model = fit_lightgbm_fixed_iterations(
            train,
            features,
            target,
            train_weight,
            selected_parameters,
            selected_best_iteration,
        )
        predictions = test[
            [
                "signal_date",
                "con_code",
                "entry_date",
                "label_end_date",
                target,
                "stock_return",
                "benchmark_return",
                "total_mv_cny",
                "sw2021_l1_name",
            ]
        ].copy()
        predictions["fold"] = fold
        predictions["selected_candidate_id"] = selected_candidate_id
        predictions["selected_best_iteration"] = selected_best_iteration
        predictions["raw_prediction_score"] = refit_model.predict(
            test[features], num_iteration=selected_best_iteration
        )
        predictions["neutralized_prediction_score"] = neutralize_scores(
            predictions, "raw_prediction_score"
        )
        test_prediction_rows.append(predictions)
        for score_column, score_type in [
            ("raw_prediction_score", "raw"),
            ("neutralized_prediction_score", "neutralized"),
        ]:
            weekly_ic = weekly_rank_ic(predictions, score_column, target)
            weekly_ic["fold"] = fold
            weekly_ic["score_type"] = score_type
            test_ic_rows.append(weekly_ic)
        gain = refit_model.feature_importance(importance_type="gain")
        split = refit_model.feature_importance(importance_type="split")
        for name, gain_value, split_value in zip(features, gain, split, strict=True):
            importance_rows.append(
                {
                    "fold": fold,
                    "selected_candidate_id": selected_candidate_id,
                    "feature": name,
                    "gain_importance": float(gain_value),
                    "split_importance": int(split_value),
                }
            )
        fold_audit.append(
            {
                "fold": fold,
                "train_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                "test_rows": int(len(test)),
                "selected_candidate_id": selected_candidate_id,
                "selected_best_iteration": selected_best_iteration,
                "selected_parameters": {
                    key: selected_parameters[key]
                    for key in ("num_leaves", "learning_rate", "min_data_in_leaf", "lambda_l2")
                },
                "validation_selection": {
                    "mean_rank_ic": float(selected["mean_rank_ic"]),
                    "rank_icir": float(selected["rank_icir"]),
                },
            }
        )

    validation_summary = pd.DataFrame(validation_summary_rows).sort_values(
        ["fold", "candidate_id"]
    ).reset_index(drop=True)
    validation_ic = pd.concat(validation_ic_rows, ignore_index=True).sort_values(
        ["fold", "candidate_id", "signal_date"]
    ).reset_index(drop=True)
    test_predictions = pd.concat(test_prediction_rows, ignore_index=True).sort_values(
        ["signal_date", "con_code"]
    ).reset_index(drop=True)
    test_ic = pd.concat(test_ic_rows, ignore_index=True).sort_values(
        ["fold", "score_type", "signal_date"]
    ).reset_index(drop=True)
    feature_importance = pd.DataFrame(importance_rows).sort_values(
        ["fold", "feature"]
    ).reset_index(drop=True)
    if test_predictions.duplicated(["signal_date", "con_code"]).any():
        raise ValueError("Test predictions overlap across folds")
    if test_predictions["signal_date"].dt.year.nunique() != 5:
        raise ValueError("LightGBM must produce one test prediction year for every fold")
    score_columns = ["raw_prediction_score", "neutralized_prediction_score"]
    if not np.isfinite(test_predictions[score_columns].to_numpy(dtype=float)).all():
        raise ValueError("LightGBM score output contains non-finite values")

    audit = {
        "stage": "G5_weekly_equal_weight_pooled_lightgbm",
        "dry_run": args.dry_run,
        "implementation": {
            "lightgbm_version": lightgbm.__version__,
            "objective": lightgbm_config["objective"],
            "training_structure": lightgbm_config["training_structure"],
            "sample_weight": lightgbm_config["sample_weight"],
            "feature_input": lightgbm_config["feature_input"],
            "target_input": lightgbm_config["target_input"],
            "target_winsorization": lightgbm_config["target_winsorization"],
            "early_stopping_metric": lightgbm_config["early_stopping_metric"],
            "test_refit_policy": lightgbm_config["test_refit_policy"],
            "deterministic": lightgbm_config["deterministic"],
            "num_threads": lightgbm_config["num_threads"],
            "candidates_per_fold": len(candidates),
            "selection_metric": config["models"]["selection_metric"],
            "neutralization": config["neutralization"],
        },
        "input_lineage": {
            "research_config_sha256": sha256(CONFIG_PATH),
            "g3_label_audit_sha256": sha256(G3_LABEL_AUDIT),
            "g3_fold_assignments_sha256": sha256(G3_FOLD_ASSIGNMENTS),
            "g3_model_panel_root": str(G3_MODEL_ROOT),
            "features": len(features),
        },
        "folds": fold_audit,
        "test_output": {
            "rows": int(len(test_predictions)),
            "signal_dates": int(test_predictions["signal_date"].nunique()),
            "test_years": sorted(test_predictions["signal_date"].dt.year.unique().tolist()),
            "duplicate_keys": int(test_predictions.duplicated(["signal_date", "con_code"]).sum()),
            "raw_score_finite": bool(np.isfinite(test_predictions["raw_prediction_score"]).all()),
            "neutralized_score_finite": bool(
                np.isfinite(test_predictions["neutralized_prediction_score"]).all()
            ),
        },
        "artifacts": {
            "validation_summary": str(VALIDATION_SUMMARY),
            "validation_weekly_rank_ic": str(VALIDATION_IC),
            "test_predictions": str(TEST_PREDICTIONS),
            "test_weekly_rank_ic": str(TEST_IC),
            "feature_importance": str(FEATURE_IMPORTANCE),
            "audit": str(AUDIT),
        },
    }
    if not args.dry_run:
        write_parquet_stable(validation_summary, VALIDATION_SUMMARY, ["fold", "candidate_id"])
        write_parquet_stable(validation_ic, VALIDATION_IC, ["fold", "candidate_id", "signal_date"])
        write_parquet_stable(test_predictions, TEST_PREDICTIONS, ["signal_date", "con_code"])
        write_parquet_stable(test_ic, TEST_IC, ["fold", "score_type", "signal_date"])
        write_parquet_stable(feature_importance, FEATURE_IMPORTANCE, ["fold", "feature"])
        write_json_stable(audit, AUDIT)
    print(render_json(audit))
    print("\nValidation selection summary:\n", validation_summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
