"""Shared, leakage-safe utilities for the G4/G5 predictive baselines."""

from __future__ import annotations

import numpy as np
import pandas as pd
import lightgbm as lgb


def weekly_equal_weights(frame: pd.DataFrame) -> np.ndarray:
    """Give every signal date equal total loss weight and mean weight one."""

    if "signal_date" not in frame:
        raise ValueError("sample-weight frame requires signal_date")
    counts = frame.groupby("signal_date")["signal_date"].transform("size").to_numpy(
        dtype=float
    )
    if (counts <= 0).any():
        raise ValueError("signal-date sample counts must be positive")
    weights = 1.0 / counts
    return weights / weights.mean()


def choose_candidate(summary: pd.DataFrame) -> pd.Series:
    """Select by mean IC, ICIR, then stronger Ridge regularization."""

    required = {"alpha", "mean_rank_ic", "rank_icir"}
    if not required.issubset(summary.columns) or summary.empty:
        raise ValueError("candidate summary requires alpha, mean_rank_ic, and rank_icir")
    return summary.sort_values(
        ["mean_rank_ic", "rank_icir", "alpha"],
        ascending=[False, False, False],
        kind="stable",
    ).iloc[0]


def weekly_rank_ic(
    frame: pd.DataFrame,
    score_column: str,
    target_column: str = "target_excess_return",
) -> pd.DataFrame:
    """Calculate one Spearman-equivalent Rank IC for each signal date."""

    required = {"signal_date", score_column, target_column}
    if not required.issubset(frame.columns):
        raise ValueError(f"Rank IC frame missing columns: {sorted(required - set(frame.columns))}")
    records: list[dict[str, object]] = []
    for signal_date, group in frame.groupby("signal_date", sort=True):
        score = group[score_column]
        target = group[target_column]
        if score.nunique() < 2 or target.nunique() < 2:
            rank_ic = np.nan
        else:
            rank_ic = score.rank(method="average").corr(
                target.rank(method="average"), method="pearson"
            )
        records.append(
            {
                "signal_date": signal_date,
                "rank_ic": rank_ic,
                "cross_section_rows": int(len(group)),
            }
        )
    return pd.DataFrame(records)


def ic_statistics(weekly_ic: pd.DataFrame) -> dict[str, float | int]:
    """Summarize a weekly Rank-IC series without making significance claims."""

    values = weekly_ic["rank_ic"].dropna()
    if len(values) < 2:
        raise ValueError("at least two non-null weeks are required for ICIR")
    standard_deviation = float(values.std(ddof=1))
    return {
        "weeks": int(len(values)),
        "mean_rank_ic": float(values.mean()),
        "std_rank_ic": standard_deviation,
        "rank_icir": float(values.mean() / standard_deviation),
        "positive_ratio": float(values.gt(0).mean()),
    }


def neutralize_scores(frame: pd.DataFrame, score_column: str) -> pd.Series:
    """Residualize a score within date against intercept, size, and industry."""

    required = {"signal_date", "total_mv_cny", "sw2021_l1_name", score_column}
    if not required.issubset(frame.columns):
        raise ValueError(f"neutralization frame missing: {sorted(required - set(frame.columns))}")
    residuals = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, group in frame.groupby("signal_date", sort=False):
        log_size = np.log(group["total_mv_cny"].to_numpy(dtype=float))
        if not np.isfinite(log_size).all():
            raise ValueError("neutralization received invalid total market cap")
        industry = group["sw2021_l1_name"].fillna("Unknown").astype(str)
        dummies = pd.get_dummies(industry, drop_first=True, dtype=float)
        design = np.column_stack(
            [np.ones(len(group)), log_size, dummies.to_numpy(dtype=float)]
        )
        score = group[score_column].to_numpy(dtype=float)
        coefficients, _, _, _ = np.linalg.lstsq(design, score, rcond=None)
        residuals.loc[group.index] = score - design @ coefficients
    if not np.isfinite(residuals).all():
        raise ValueError("score neutralization produced non-finite residuals")
    return residuals


def _validation_rank_ic_metric(
    validation: pd.DataFrame,
    target_column: str,
):
    """Build a LightGBM custom metric that averages Rank IC equally by week."""

    signal_dates = validation["signal_date"].to_numpy()
    targets = validation[target_column].to_numpy(dtype=float)

    def metric(predictions: np.ndarray, _dataset: lgb.Dataset):
        frame = pd.DataFrame(
            {
                "signal_date": signal_dates,
                "prediction": predictions,
                "target": targets,
            }
        )
        value = weekly_rank_ic(frame, "prediction", "target")["rank_ic"].mean()
        return "mean_weekly_rank_ic", float(value), True

    return metric


def fit_lightgbm_candidate(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    feature_names: list[str],
    target_column: str,
    train_weight: np.ndarray,
    parameters: dict[str, float | int],
) -> tuple[lgb.Booster, int]:
    """Fit one candidate using validation-only Rank-IC early stopping."""

    if len(train_weight) != len(train):
        raise ValueError("LightGBM training weights must align with training rows")
    required = {"signal_date", target_column, *feature_names}
    if not required.issubset(train.columns) or not required.issubset(validation.columns):
        raise ValueError("LightGBM candidate frame is missing required columns")
    train_dataset = lgb.Dataset(
        train[feature_names],
        label=train[target_column],
        weight=train_weight,
        free_raw_data=False,
    )
    validation_dataset = lgb.Dataset(
        validation[feature_names], label=validation[target_column], reference=train_dataset, free_raw_data=False
    )
    lgb_parameters = {
        "objective": "regression",
        "metric": "None",
        "verbosity": -1,
        "seed": int(parameters["seed"]),
        "feature_fraction": float(parameters["feature_fraction"]),
        "bagging_fraction": float(parameters["bagging_fraction"]),
        "bagging_freq": int(parameters["bagging_freq"]),
        "num_leaves": int(parameters["num_leaves"]),
        "learning_rate": float(parameters["learning_rate"]),
        "min_data_in_leaf": int(parameters["min_data_in_leaf"]),
        "lambda_l2": float(parameters["lambda_l2"]),
        "deterministic": bool(parameters.get("deterministic", True)),
        "force_col_wise": True,
        "num_threads": int(parameters.get("num_threads", 4)),
    }
    booster = lgb.train(
        lgb_parameters,
        train_dataset,
        num_boost_round=int(parameters["max_boost_rounds"]),
        valid_sets=[validation_dataset],
        feval=_validation_rank_ic_metric(validation, target_column),
        callbacks=[
            lgb.early_stopping(
                stopping_rounds=int(parameters["early_stopping_rounds"]),
                verbose=False,
            )
        ],
    )
    best_iteration = int(booster.best_iteration or parameters["max_boost_rounds"])
    if best_iteration <= 0:
        raise ValueError("LightGBM returned a non-positive best iteration")
    return booster, best_iteration


def fit_lightgbm_fixed_iterations(
    train: pd.DataFrame,
    feature_names: list[str],
    target_column: str,
    train_weight: np.ndarray,
    parameters: dict[str, float | int],
    num_boost_round: int,
) -> lgb.Booster:
    """Refit a selected candidate on training data only for its fixed rounds."""

    if len(train_weight) != len(train) or num_boost_round <= 0:
        raise ValueError("invalid LightGBM training weights or iteration count")
    train_dataset = lgb.Dataset(
        train[feature_names],
        label=train[target_column],
        weight=train_weight,
        free_raw_data=False,
    )
    lgb_parameters = {
        "objective": "regression",
        "metric": "None",
        "verbosity": -1,
        "seed": int(parameters["seed"]),
        "feature_fraction": float(parameters["feature_fraction"]),
        "bagging_fraction": float(parameters["bagging_fraction"]),
        "bagging_freq": int(parameters["bagging_freq"]),
        "num_leaves": int(parameters["num_leaves"]),
        "learning_rate": float(parameters["learning_rate"]),
        "min_data_in_leaf": int(parameters["min_data_in_leaf"]),
        "lambda_l2": float(parameters["lambda_l2"]),
        "deterministic": bool(parameters.get("deterministic", True)),
        "force_col_wise": True,
        "num_threads": int(parameters.get("num_threads", 4)),
    }
    return lgb.train(lgb_parameters, train_dataset, num_boost_round=num_boost_round)
