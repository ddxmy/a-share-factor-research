"""Immutable configuration checks for the R1 Qlib-parameter transfer experiment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


QLIB_FIXED_PARAMETERS: dict[str, float | int | str] = {
    "loss": "mse",
    "colsample_bytree": 0.8879,
    "learning_rate": 0.2,
    "subsample": 0.8789,
    "lambda_l1": 205.6999,
    "lambda_l2": 580.9768,
    "max_depth": 8,
    "num_leaves": 210,
}
EXPECTED_TEST_YEARS = [2021, 2022, 2023, 2024, 2025]


def load_r1_config(path: Path) -> dict[str, Any]:
    """Load an R1 JSON configuration from an explicit path."""
    return json.loads(path.read_text(encoding="utf-8"))


def validate_r1_config(config: dict[str, Any]) -> None:
    """Reject parameter drift or any test-period model-selection rule."""
    if config.get("schema_version") != "1.0":
        raise ValueError("R1 schema version must be 1.0")
    if config.get("selection") != "validation_best_iteration_only":
        raise ValueError("R1 may select only a validation-set boosting iteration")
    if config.get("training_label_preprocessing") != "cross_sectional_zscore_per_signal_date":
        raise ValueError("R1 must use Qlib-style cross-sectional training-label Z-scores")
    lightgbm = config.get("lightgbm", {})
    for key, expected in QLIB_FIXED_PARAMETERS.items():
        if lightgbm.get(key) != expected:
            raise ValueError(f"R1 parameter {key} must equal Qlib value {expected!r}")
    if lightgbm.get("num_threads") != 4:
        raise ValueError("R1 uses four local LightGBM threads for deterministic portability")
    if lightgbm.get("objective") != "regression" or lightgbm.get("metric") != "None":
        raise ValueError("R1 LightGBM objective/metric contract changed")
    if lightgbm.get("max_boost_rounds") != 2000 or lightgbm.get("early_stopping_rounds") != 100:
        raise ValueError("R1 local iteration-selection controls changed")
    folds = config.get("rolling_folds", [])
    if [fold.get("test_year") for fold in folds] != EXPECTED_TEST_YEARS:
        raise ValueError("R1 must contain exactly one test fold for each year 2021–2025")
    for fold in folds:
        train_years = fold.get("train_years", [])
        validation_year = fold.get("validation_year")
        test_year = fold.get("test_year")
        if len(train_years) != 5 or max(train_years) >= validation_year or validation_year >= test_year:
            raise ValueError(f"R1 fold is not chronological: {fold}")


def cross_sectional_zscore_label(frame: pd.DataFrame, target_column: str) -> pd.Series:
    """Return Qlib Alpha158-style label normalization independently for every signal date."""
    if "signal_date" not in frame or target_column not in frame:
        raise ValueError("label normalization requires signal_date and target columns")
    target = frame[target_column].astype(float)
    means = target.groupby(frame["signal_date"]).transform("mean")
    standard_deviations = target.groupby(frame["signal_date"]).transform(lambda values: values.std(ddof=0))
    if not np.isfinite(standard_deviations).all() or standard_deviations.le(0).any():
        raise ValueError("Qlib-style label normalization requires non-zero within-date variation")
    normalized = (target - means) / standard_deviations
    if not np.isfinite(normalized).all():
        raise ValueError("Qlib-style label normalization produced non-finite values")
    return normalized
