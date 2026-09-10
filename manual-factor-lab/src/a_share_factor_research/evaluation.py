"""Multi-horizon cross-sectional IC evidence and frozen factor decisions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from .registry import FactorDefinition


_DAILY_COLUMNS = [
    "signal_date",
    "horizon_days",
    "eligibility",
    "pearson_ic",
    "rank_ic",
    "n_names",
]
_SUMMARY_COLUMNS = [
    "horizon_days",
    "eligibility",
    "n_observations",
    "mean_pearson_ic",
    "pearson_ic_std",
    "pearson_icir",
    "positive_pearson_ic_ratio",
    "cumulative_pearson_ic",
    "mean_rank_ic",
    "rank_ic_std",
    "rank_icir",
    "positive_rank_ic_ratio",
    "cumulative_rank_ic",
    "hac_lag",
    "hac_standard_error",
    "hac_t_stat",
    "hac_one_sided_p_value",
]
_YEARLY_COLUMNS = [
    "horizon_days",
    "eligibility",
    "year",
    "n_observations",
    "mean_pearson_ic",
    "pearson_ic_std",
    "pearson_icir",
    "positive_pearson_ic_ratio",
    "cumulative_pearson_ic",
    "mean_rank_ic",
    "rank_ic_std",
    "rank_icir",
    "positive_rank_ic_ratio",
    "cumulative_rank_ic",
]
_ELIGIBILITY_KINDS = {"basic", "tradable"}


@dataclass(frozen=True)
class ICEvaluation:
    """Tables needed to inspect IC evidence and apply the frozen decision rule."""

    daily: pd.DataFrame
    summary: pd.DataFrame
    yearly: pd.DataFrame
    non_overlapping: pd.DataFrame
    non_overlapping_summary: pd.DataFrame


def hac_lag_for_horizon(horizon_days: int) -> int:
    """Return the overlap-aware Bartlett Newey--West lag for a daily horizon."""
    if not isinstance(horizon_days, (int, np.integer)) or horizon_days <= 0:
        raise ValueError("horizon_days must be a positive integer")
    return int(horizon_days) - 1


def evaluate_ic(
    panel: pd.DataFrame,
    horizons: Iterable[int],
    eligibility: str | Iterable[str],
) -> ICEvaluation:
    """Evaluate daily Pearson and Spearman IC for one or both eligibility masks.

    ``directed_score`` is already aligned by factor processing: evidence in the
    pre-registered direction is therefore positive for both positive and
    negative raw factor definitions.
    """
    requested_horizons = _validated_horizons(horizons)
    eligibility_kinds = _validated_eligibility(eligibility)
    required_columns = {"signal_date", "directed_score", "basic_eligible"}
    required_columns.update(f"label_excess_o2o_{horizon}d" for horizon in requested_horizons)
    if "tradable" in eligibility_kinds:
        required_columns.add("tradable_next_open")
    missing_columns = required_columns.difference(panel.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"IC panel is missing required columns: {missing}.")

    evaluated = panel.copy().reset_index(drop=True)
    evaluated["signal_date"] = pd.to_datetime(evaluated["signal_date"], errors="coerce")
    if evaluated["signal_date"].isna().any():
        raise ValueError("IC panel contains an unparsable signal_date.")

    records: list[dict[str, object]] = []
    for eligibility_kind in eligibility_kinds:
        eligible = _eligibility_mask(evaluated, eligibility_kind)
        for horizon in requested_horizons:
            label_column = f"label_excess_o2o_{horizon}d"
            for signal_date, cross_section in evaluated.groupby("signal_date", sort=True):
                cross_section_eligible = eligible.loc[cross_section.index]
                scores = pd.to_numeric(
                    cross_section.loc[cross_section_eligible, "directed_score"], errors="coerce"
                )
                labels = pd.to_numeric(
                    cross_section.loc[cross_section_eligible, label_column], errors="coerce"
                )
                finite_pairs = np.isfinite(scores.to_numpy(dtype=float)) & np.isfinite(
                    labels.to_numpy(dtype=float)
                )
                scores = scores.loc[finite_pairs]
                labels = labels.loc[finite_pairs]
                n_names = len(scores)
                pearson_ic = np.nan
                rank_ic = np.nan
                if n_names >= 3 and scores.nunique() >= 2 and labels.nunique() >= 2:
                    pearson_ic = scores.corr(labels, method="pearson")
                    rank_ic = scores.corr(labels, method="spearman")
                records.append(
                    {
                        "signal_date": signal_date,
                        "horizon_days": horizon,
                        "eligibility": eligibility_kind,
                        "pearson_ic": pearson_ic,
                        "rank_ic": rank_ic,
                        "n_names": n_names,
                    }
                )

    daily = pd.DataFrame.from_records(records, columns=_DAILY_COLUMNS)
    daily["signal_date"] = pd.to_datetime(daily["signal_date"])
    daily = daily.sort_values(["eligibility", "horizon_days", "signal_date"]).reset_index(drop=True)
    summary = _summarize(daily, overlap_adjusted=True)
    yearly = _summarize_yearly(daily)
    non_overlapping = _non_overlapping_samples(daily)
    non_overlapping_summary = _summarize(non_overlapping, overlap_adjusted=False)
    return ICEvaluation(
        daily=daily,
        summary=summary,
        yearly=yearly,
        non_overlapping=non_overlapping,
        non_overlapping_summary=non_overlapping_summary,
    )


def classify_factor(
    ic_evaluation: ICEvaluation,
    definition: FactorDefinition,
    test_years: Iterable[int],
) -> str:
    """Apply the frozen Admit/Review/Reject policy to 1D Rank-IC evidence.

    Classification is intentionally based on the direction-aligned
    ``directed_score`` evaluated above.  Thus the expected Rank IC is positive
    even when the registered raw factor direction is negative.
    """
    if definition.pre_registered_direction not in {"positive", "negative"}:
        raise ValueError("pre_registered_direction must be 'positive' or 'negative'.")
    years = tuple(int(year) for year in test_years)
    locked_daily = ic_evaluation.daily.loc[
        ic_evaluation.daily["signal_date"].dt.year.isin(years)
    ]
    locked_summary = _summarize(locked_daily, overlap_adjusted=True)

    basic = _one_summary_row(locked_summary, "basic")
    if basic is None or int(basic["n_observations"]) < 500:
        return "Reject"

    basic_mean = float(basic["mean_rank_ic"])
    if np.isfinite(basic_mean) and basic_mean < 0:
        return "Reject"
    if not np.isfinite(basic_mean) or basic_mean == 0:
        return "Review"

    tradable = _one_summary_row(locked_summary, "tradable")
    tradable_has_expected_direction = (
        tradable is not None
        and np.isfinite(tradable["mean_rank_ic"])
        and float(tradable["mean_rank_ic"]) > 0
    )
    basic_years = ic_evaluation.yearly.loc[
        (ic_evaluation.yearly["horizon_days"] == 1)
        & (ic_evaluation.yearly["eligibility"] == "basic")
        & (ic_evaluation.yearly["year"].isin(years))
    ]
    correct_years = int((basic_years["mean_rank_ic"] > 0).sum())
    significant = (
        np.isfinite(basic["hac_one_sided_p_value"])
        and float(basic["hac_one_sided_p_value"]) < 0.05
    )
    if significant and correct_years >= 4 and tradable_has_expected_direction:
        return "Admit"
    return "Review"


def _validated_horizons(horizons: Iterable[int]) -> tuple[int, ...]:
    values = tuple(horizons)
    if not values or any(
        not isinstance(horizon, (int, np.integer)) or horizon <= 0 for horizon in values
    ):
        raise ValueError("horizons must contain positive integers")
    if len(set(values)) != len(values):
        raise ValueError("horizons must not contain duplicates")
    return tuple(sorted(int(horizon) for horizon in values))


def _validated_eligibility(eligibility: str | Iterable[str]) -> tuple[str, ...]:
    values = (eligibility,) if isinstance(eligibility, str) else tuple(eligibility)
    if not values or len(set(values)) != len(values) or set(values).difference(_ELIGIBILITY_KINDS):
        raise ValueError("eligibility must contain unique 'basic' and/or 'tradable' values")
    return values


def _eligibility_mask(panel: pd.DataFrame, eligibility: str) -> pd.Series:
    basic = panel["basic_eligible"].astype("boolean").fillna(False)
    if eligibility == "basic":
        return basic.astype(bool)
    tradable = panel["tradable_next_open"].astype("boolean").fillna(False)
    return (basic & tradable).astype(bool)


def _summarize(daily: pd.DataFrame, *, overlap_adjusted: bool) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for (eligibility, horizon), group in daily.groupby(
        ["eligibility", "horizon_days"], sort=True
    ):
        rank_ic = group["rank_ic"].dropna().astype(float)
        pearson_ic = group["pearson_ic"].dropna().astype(float)
        lag = hac_lag_for_horizon(int(horizon)) if overlap_adjusted else 0
        hac_standard_error, hac_t_stat, one_sided_p_value = _hac_mean_test(rank_ic, lag)
        rank_std = rank_ic.std(ddof=1)
        pearson_std = pearson_ic.std(ddof=1)
        records.append(
            {
                "horizon_days": int(horizon),
                "eligibility": eligibility,
                "n_observations": int(rank_ic.size),
                "mean_pearson_ic": pearson_ic.mean(),
                "pearson_ic_std": pearson_std,
                "pearson_icir": _safe_ratio(pearson_ic.mean(), pearson_std),
                "positive_pearson_ic_ratio": (pearson_ic > 0).mean(),
                "cumulative_pearson_ic": pearson_ic.sum(min_count=1),
                "mean_rank_ic": rank_ic.mean(),
                "rank_ic_std": rank_std,
                "rank_icir": _safe_ratio(rank_ic.mean(), rank_std),
                "positive_rank_ic_ratio": (rank_ic > 0).mean(),
                "cumulative_rank_ic": rank_ic.sum(min_count=1),
                "hac_lag": lag,
                "hac_standard_error": hac_standard_error,
                "hac_t_stat": hac_t_stat,
                "hac_one_sided_p_value": one_sided_p_value,
            }
        )
    return pd.DataFrame.from_records(records, columns=_SUMMARY_COLUMNS)


def _summarize_yearly(daily: pd.DataFrame) -> pd.DataFrame:
    annual = daily.copy()
    annual["year"] = annual["signal_date"].dt.year
    records: list[dict[str, object]] = []
    for (eligibility, horizon, year), group in annual.groupby(
        ["eligibility", "horizon_days", "year"], sort=True
    ):
        rank_ic = group["rank_ic"].dropna().astype(float)
        pearson_ic = group["pearson_ic"].dropna().astype(float)
        rank_std = rank_ic.std(ddof=1)
        pearson_std = pearson_ic.std(ddof=1)
        records.append(
            {
                "horizon_days": int(horizon),
                "eligibility": eligibility,
                "year": int(year),
                "n_observations": int(rank_ic.size),
                "mean_pearson_ic": pearson_ic.mean(),
                "pearson_ic_std": pearson_std,
                "pearson_icir": _safe_ratio(pearson_ic.mean(), pearson_std),
                "positive_pearson_ic_ratio": (pearson_ic > 0).mean(),
                "cumulative_pearson_ic": pearson_ic.sum(min_count=1),
                "mean_rank_ic": rank_ic.mean(),
                "rank_ic_std": rank_std,
                "rank_icir": _safe_ratio(rank_ic.mean(), rank_std),
                "positive_rank_ic_ratio": (rank_ic > 0).mean(),
                "cumulative_rank_ic": rank_ic.sum(min_count=1),
            }
        )
    return pd.DataFrame.from_records(records, columns=_YEARLY_COLUMNS)


def _non_overlapping_samples(daily: pd.DataFrame) -> pd.DataFrame:
    samples = []
    for (_, horizon), group in daily.groupby(["eligibility", "horizon_days"], sort=True):
        if horizon in {5, 20}:
            samples.append(group.sort_values("signal_date").iloc[:: int(horizon)])
    if not samples:
        return pd.DataFrame(columns=_DAILY_COLUMNS)
    return pd.concat(samples, ignore_index=True)[_DAILY_COLUMNS]


def _hac_mean_test(values: pd.Series, lag: int) -> tuple[float, float, float]:
    observations = values.to_numpy(dtype=float)
    n_observations = observations.size
    if n_observations == 0:
        return np.nan, np.nan, np.nan
    effective_lag = min(lag, n_observations - 1)
    residuals = observations - observations.mean()
    long_run_variance = float(residuals @ residuals / n_observations)
    for offset in range(1, effective_lag + 1):
        bartlett_weight = 1.0 - offset / (effective_lag + 1.0)
        autocovariance = float(residuals[offset:] @ residuals[:-offset] / n_observations)
        long_run_variance += 2.0 * bartlett_weight * autocovariance
    variance_of_mean = max(long_run_variance, 0.0) / n_observations
    standard_error = float(np.sqrt(variance_of_mean))
    mean = float(observations.mean())
    if standard_error == 0:
        if mean > 0:
            return standard_error, np.inf, 0.0
        if mean < 0:
            return standard_error, -np.inf, 1.0
        return standard_error, np.nan, np.nan
    t_stat = mean / standard_error
    return standard_error, t_stat, float(stats.norm.sf(t_stat))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(denominator) or denominator == 0:
        return np.nan
    return float(numerator / denominator)


def _one_summary_row(summary: pd.DataFrame, eligibility: str) -> pd.Series | None:
    rows = summary.loc[
        (summary["horizon_days"] == 1) & (summary["eligibility"] == eligibility)
    ]
    if len(rows) != 1:
        return None
    return rows.iloc[0]
