"""Leakage-free evaluation helpers for locked G4/G5 test predictions."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


KEYS = ["signal_date", "con_code"]
TARGET = "target_excess_return"


def validate_common_prediction_panel(
    ridge: pd.DataFrame, lightgbm: pd.DataFrame
) -> pd.DataFrame:
    """Return a one-to-one common test panel and reject label/key disagreements."""

    required = set(KEYS + [TARGET, "raw_prediction_score", "neutralized_prediction_score"])
    for name, frame in [("ridge", ridge), ("lightgbm", lightgbm)]:
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{name} prediction panel missing columns: {sorted(missing)}")
        if frame.duplicated(KEYS).any():
            raise ValueError(f"{name} prediction panel has duplicate keys")
    ridge_columns = KEYS + [TARGET, "raw_prediction_score", "neutralized_prediction_score"]
    lightgbm_columns = KEYS + [TARGET, "raw_prediction_score", "neutralized_prediction_score"]
    common = ridge[ridge_columns].merge(
        lightgbm[lightgbm_columns],
        on=KEYS,
        how="inner",
        validate="one_to_one",
        suffixes=("_ridge", "_lightgbm"),
    )
    if len(common) != len(ridge) or len(common) != len(lightgbm):
        raise ValueError("Ridge and LightGBM test keys do not match exactly")
    if not np.allclose(
        common[f"{TARGET}_ridge"].to_numpy(dtype=float),
        common[f"{TARGET}_lightgbm"].to_numpy(dtype=float),
        rtol=0.0,
        atol=1e-12,
        equal_nan=False,
    ):
        raise ValueError("Ridge and LightGBM target labels do not match")
    common = common.rename(columns={f"{TARGET}_ridge": TARGET}).drop(
        columns=[f"{TARGET}_lightgbm"]
    )
    for column in [
        "raw_prediction_score_ridge",
        "neutralized_prediction_score_ridge",
        "raw_prediction_score_lightgbm",
        "neutralized_prediction_score_lightgbm",
        TARGET,
    ]:
        if not np.isfinite(common[column].to_numpy(dtype=float)).all():
            raise ValueError(f"common prediction panel has non-finite {column}")
    return common.sort_values(KEYS).reset_index(drop=True)


def rank_ic_summary(weekly_ic: pd.DataFrame) -> dict[str, float | int]:
    """Summarize an equal-date-weight weekly Rank-IC series."""

    values = weekly_ic["rank_ic"].dropna().to_numpy(dtype=float)
    if len(values) < 2:
        raise ValueError("at least two weekly Rank IC values are required")
    standard_deviation = float(values.std(ddof=1))
    return {
        "weeks": int(len(values)),
        "mean_rank_ic": float(values.mean()),
        "std_rank_ic": standard_deviation,
        "rank_icir": float(values.mean() / standard_deviation)
        if standard_deviation > 0
        else float("nan"),
        "positive_ratio": float((values > 0).mean()),
    }


def newey_west_mean_test(
    values: np.ndarray | pd.Series, max_lag: int = 4
) -> dict[str, float | int]:
    """Test a serially correlated weekly mean using Bartlett HAC variance."""

    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or len(array) < 2 or not np.isfinite(array).all():
        raise ValueError("Newey-West input must be a finite one-dimensional series of length >= 2")
    if max_lag < 0 or max_lag >= len(array):
        raise ValueError("Newey-West lag must be non-negative and smaller than sample length")
    centered = array - array.mean()
    long_run_variance = float(np.mean(centered * centered))
    for lag in range(1, max_lag + 1):
        autocovariance = float(np.mean(centered[lag:] * centered[:-lag]))
        long_run_variance += 2.0 * (1.0 - lag / (max_lag + 1.0)) * autocovariance
    standard_error = math.sqrt(max(long_run_variance, 0.0) / len(array))
    statistic = float(array.mean() / standard_error) if standard_error > 0 else float("nan")
    p_value = math.erfc(abs(statistic) / math.sqrt(2.0)) if np.isfinite(statistic) else float("nan")
    return {
        "weeks": int(len(array)),
        "max_lag": int(max_lag),
        "mean": float(array.mean()),
        "hac_standard_error": standard_error,
        "t_statistic": statistic,
        "two_sided_normal_p_value": p_value,
    }


def weekly_quintile_returns(
    panel: pd.DataFrame,
    score_column: str,
    target_column: str = TARGET,
) -> pd.DataFrame:
    """Create equal-count weekly score quintiles and their frictionless spread."""

    required = {"signal_date", score_column, target_column}
    if not required.issubset(panel.columns):
        raise ValueError(f"quintile panel missing columns: {sorted(required - set(panel.columns))}")
    records: list[dict[str, object]] = []
    labels = ["Q1", "Q2", "Q3", "Q4", "Q5"]
    for signal_date, group in panel.groupby("signal_date", sort=True):
        if len(group) < 5 or group[score_column].nunique() < 5:
            raise ValueError(f"signal date {signal_date} cannot form five score quintiles")
        ranked = group[score_column].rank(method="first")
        quintile = pd.qcut(ranked, q=5, labels=labels)
        returns: dict[str, float] = {}
        for label in labels:
            members = group.loc[quintile.eq(label), target_column]
            mean_return = float(members.mean())
            returns[label] = mean_return
            records.append(
                {
                    "signal_date": signal_date,
                    "quintile": label,
                    "mean_excess_return": mean_return,
                    "cross_section_rows": int(len(members)),
                }
            )
        records.append(
            {
                "signal_date": signal_date,
                "quintile": "Q5-Q1",
                "mean_excess_return": returns["Q5"] - returns["Q1"],
                "cross_section_rows": int(len(group)),
            }
        )
    return pd.DataFrame(records)
