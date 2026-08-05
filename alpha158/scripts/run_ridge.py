#!/usr/bin/env python3
"""Run the frozen weekly-equal-weight pooled Ridge baseline for G4."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import Ridge


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

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
ARTIFACT_DIR = OUTPUT_ROOT / "G4"
VALIDATION_SUMMARY = ARTIFACT_DIR / "ridge_validation_summary_v1.parquet"
VALIDATION_IC = ARTIFACT_DIR / "ridge_validation_weekly_rank_ic_v1.parquet"
TEST_PREDICTIONS = ARTIFACT_DIR / "ridge_test_predictions_v1.parquet"
TEST_IC = ARTIFACT_DIR / "ridge_test_weekly_rank_ic_v1.parquet"
COEFFICIENTS = ARTIFACT_DIR / "ridge_selected_coefficients_v1.parquet"
AUDIT = ARTIFACT_DIR / "ridge_run_audit_v1.json"


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


def load_inputs() -> tuple[dict, pd.DataFrame, pd.DataFrame, list[str]]:
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


def fold_slice(panel: pd.DataFrame, assignments: pd.DataFrame, fold: int, role: str) -> pd.DataFrame:
    keys = assignments.loc[
        assignments["fold"].eq(fold)
        & assignments["role"].eq(role)
        & assignments["included_for_model"].astype(bool),
        ["signal_date", "con_code"],
    ]
    output = keys.merge(panel, on=["signal_date", "con_code"], how="inner", validate="one_to_one")
    if len(output) != len(keys):
        raise ValueError(f"Fold {fold} {role} keys are not all present in model panel")
    return output.sort_values(["signal_date", "con_code"]).reset_index(drop=True)


def weekly_equal_weights(frame: pd.DataFrame) -> np.ndarray:
    """Give each signal date equal total loss weight and rescale mean weight to one."""

    counts = frame.groupby("signal_date")["con_code"].transform("size").to_numpy(dtype=float)
    weights = 1.0 / counts
    return weights / weights.mean()


def weekly_rank_ic(frame: pd.DataFrame, score_column: str) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for signal_date, group in frame.groupby("signal_date", sort=True):
        score = group[score_column]
        target = group["target_excess_return"]
        if score.nunique() < 2 or target.nunique() < 2:
            value = np.nan
        else:
            value = score.rank(method="average").corr(target.rank(method="average"), method="pearson")
        records.append({"signal_date": signal_date, "rank_ic": value, "cross_section_rows": len(group)})
    return pd.DataFrame(records)


def ic_statistics(weekly_ic: pd.DataFrame) -> dict[str, float | int]:
    values = weekly_ic["rank_ic"].dropna()
    return {
        "weeks": int(len(values)),
        "mean_rank_ic": float(values.mean()),
        "std_rank_ic": float(values.std(ddof=1)),
        "rank_icir": float(values.mean() / values.std(ddof=1)),
        "positive_ratio": float(values.gt(0).mean()),
    }


def neutralize_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """Residualize scores within date against size and SW2021 L1 industry only."""

    output = frame.copy()
    residuals = pd.Series(np.nan, index=output.index, dtype=float)
    for _, group in output.groupby("signal_date", sort=False):
        log_size = np.log(group["total_mv_cny"].to_numpy(dtype=float))
        if not np.isfinite(log_size).all():
            raise ValueError("Score neutralization received invalid as-of market cap")
        industry = group["sw2021_l1_name"].fillna("Unknown").astype(str)
        dummies = pd.get_dummies(industry, drop_first=True, dtype=float)
        design = np.column_stack([
            np.ones(len(group)),
            log_size,
            dummies.to_numpy(dtype=float),
        ])
        coefficients, _, _, _ = np.linalg.lstsq(
            design, group["raw_prediction_score"].to_numpy(dtype=float), rcond=None
        )
        residuals.loc[group.index] = group["raw_prediction_score"].to_numpy(dtype=float) - design @ coefficients
    output["neutralized_prediction_score"] = residuals
    if not np.isfinite(output["neutralized_prediction_score"]).all():
        raise ValueError("Neutralized scores contain non-finite values")
    return output


def choose_alpha(summary: pd.DataFrame) -> pd.Series:
    """Apply frozen mean-IC, ICIR, then simpler-model tie breakers."""

    ordered = summary.sort_values(
        ["mean_rank_ic", "rank_icir", "alpha"],
        ascending=[False, False, False],
        kind="stable",
    )
    return ordered.iloc[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Fit and validate without writing artifacts")
    args = parser.parse_args()
    config, panel, assignments, features = load_inputs()
    ridge_config = config["models"]["ridge"]
    alphas = [float(value) for value in ridge_config["alpha_grid"]]
    target = "target_excess_return"
    validation_summary_rows: list[dict[str, object]] = []
    validation_ic_rows: list[pd.DataFrame] = []
    test_prediction_rows: list[pd.DataFrame] = []
    test_ic_rows: list[pd.DataFrame] = []
    coefficient_rows: list[dict[str, object]] = []
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
        candidate_models: dict[float, Ridge] = {}
        for alpha in alphas:
            model = Ridge(alpha=alpha, fit_intercept=True)
            model.fit(train[features], train[target], sample_weight=train_weight)
            candidate_models[alpha] = model
            validation_scores = validation[["signal_date", "con_code", target]].copy()
            validation_scores["raw_prediction_score"] = model.predict(validation[features])
            weekly_ic = weekly_rank_ic(validation_scores, "raw_prediction_score")
            weekly_ic["fold"] = fold
            weekly_ic["alpha"] = alpha
            validation_ic_rows.append(weekly_ic)
            validation_summary_rows.append({"fold": fold, "alpha": alpha, **ic_statistics(weekly_ic)})

        fold_summary = pd.DataFrame(validation_summary_rows).query("fold == @fold")
        selected = choose_alpha(fold_summary)
        selected_alpha = float(selected["alpha"])
        model = candidate_models[selected_alpha]
        predictions = test[[
            "signal_date", "con_code", "entry_date", "label_end_date", target,
            "stock_return", "benchmark_return", "total_mv_cny", "sw2021_l1_name",
        ]].copy()
        predictions["fold"] = fold
        predictions["selected_alpha"] = selected_alpha
        predictions["raw_prediction_score"] = model.predict(test[features])
        predictions = neutralize_scores(predictions)
        test_prediction_rows.append(predictions)
        for score_column, score_name in [
            ("raw_prediction_score", "raw"),
            ("neutralized_prediction_score", "neutralized"),
        ]:
            weekly_ic = weekly_rank_ic(predictions, score_column)
            weekly_ic["fold"] = fold
            weekly_ic["score_type"] = score_name
            test_ic_rows.append(weekly_ic)
        for name, value in zip(features, model.coef_, strict=True):
            coefficient_rows.append({"fold": fold, "selected_alpha": selected_alpha, "feature": name, "coefficient": float(value)})
        coefficient_rows.append({"fold": fold, "selected_alpha": selected_alpha, "feature": "__intercept__", "coefficient": float(model.intercept_)})
        fold_audit.append({
            "fold": fold,
            "train_rows": int(len(train)),
            "validation_rows": int(len(validation)),
            "test_rows": int(len(test)),
            "selected_alpha": selected_alpha,
            "validation_selection": {
                "mean_rank_ic": float(selected["mean_rank_ic"]),
                "rank_icir": float(selected["rank_icir"]),
            },
        })

    validation_summary = pd.DataFrame(validation_summary_rows).sort_values(["fold", "alpha"]).reset_index(drop=True)
    validation_ic = pd.concat(validation_ic_rows, ignore_index=True).sort_values(["fold", "alpha", "signal_date"]).reset_index(drop=True)
    test_predictions = pd.concat(test_prediction_rows, ignore_index=True).sort_values(["signal_date", "con_code"]).reset_index(drop=True)
    test_ic = pd.concat(test_ic_rows, ignore_index=True).sort_values(["fold", "score_type", "signal_date"]).reset_index(drop=True)
    coefficients = pd.DataFrame(coefficient_rows).sort_values(["fold", "feature"]).reset_index(drop=True)
    if test_predictions.duplicated(["signal_date", "con_code"]).any():
        raise ValueError("Test predictions overlap across folds")
    if test_predictions["signal_date"].dt.year.nunique() != 5:
        raise ValueError("Ridge must produce one test prediction year for every fold")
    if not np.isfinite(test_predictions[["raw_prediction_score", "neutralized_prediction_score"]].to_numpy(dtype=float)).all():
        raise ValueError("Ridge score output contains non-finite values")

    audit = {
        "stage": "G4_weekly_equal_weight_pooled_ridge",
        "dry_run": args.dry_run,
        "implementation": {
            "sklearn_version": sklearn.__version__,
            "estimator": ridge_config["estimator"],
            "training_structure": ridge_config["training_structure"],
            "sample_weight": ridge_config["sample_weight"],
            "fit_intercept": ridge_config["fit_intercept"],
            "feature_input": ridge_config["feature_input"],
            "target_input": ridge_config["target_input"],
            "target_winsorization": ridge_config["target_winsorization"],
            "test_refit_policy": ridge_config["test_refit_policy"],
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
            "neutralized_score_finite": bool(np.isfinite(test_predictions["neutralized_prediction_score"]).all()),
        },
        "artifacts": {
            "validation_summary": str(VALIDATION_SUMMARY),
            "validation_weekly_rank_ic": str(VALIDATION_IC),
            "test_predictions": str(TEST_PREDICTIONS),
            "test_weekly_rank_ic": str(TEST_IC),
            "selected_coefficients": str(COEFFICIENTS),
            "audit": str(AUDIT),
        },
    }
    if not args.dry_run:
        write_parquet_stable(validation_summary, VALIDATION_SUMMARY, ["fold", "alpha"])
        write_parquet_stable(validation_ic, VALIDATION_IC, ["fold", "alpha", "signal_date"])
        write_parquet_stable(test_predictions, TEST_PREDICTIONS, ["signal_date", "con_code"])
        write_parquet_stable(test_ic, TEST_IC, ["fold", "score_type", "signal_date"])
        write_parquet_stable(coefficients, COEFFICIENTS, ["fold", "feature"])
        write_json_stable(audit, AUDIT)
    print(render_json(audit))
    print("\nValidation selection summary:\n", validation_summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
