"""Leakage-safe cross-sectional preprocessing for Alpha158 features."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PreprocessingParameters:
    """Frozen parameters for one-date cross-sectional preprocessing."""

    mad_scale_constant: float = 1.4826
    winsorize_mad_multiplier: float = 5.0
    zscore_ddof: int = 0
    zero_variance_tolerance: float = 1e-12


def preprocess_cross_sections(
    panel: pd.DataFrame,
    feature_names: Sequence[str],
    *,
    date_column: str = "trade_date",
    instrument_column: str = "instrument",
    parameters: PreprocessingParameters | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Preprocess features independently within each date.

    Processing order is infinite-to-null, cross-sectional median fill,
    median/MAD winsorization, then population-standard-deviation Z-score.
    All-null and zero-variance cross-sections become zero and remain visible
    in the returned quality table.
    """

    params = parameters or PreprocessingParameters()
    features = list(feature_names)
    required = {date_column, instrument_column, *features}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Missing preprocessing columns: {sorted(missing)}")
    if len(features) != len(set(features)):
        raise ValueError("feature_names must be unique")
    if params.zscore_ddof != 0:
        raise ValueError("The frozen v1 preprocessing requires zscore_ddof=0")

    ordered = panel[[date_column, instrument_column, *features]].copy()
    ordered[date_column] = pd.to_datetime(ordered[date_column])
    ordered = ordered.sort_values([date_column, instrument_column]).reset_index(
        drop=True
    )
    empty_features = pd.DataFrame(
        np.nan,
        index=ordered.index,
        columns=features,
        dtype=float,
    )
    transformed = pd.concat(
        [
            ordered[[date_column, instrument_column]].copy(),
            empty_features,
        ],
        axis=1,
    )

    # Work one cross-section at a time, but process all columns as one matrix.
    # This is numerically the same sequence as the factor-by-factor reference
    # implementation above, while avoiding roughly 89,000 pandas operations in
    # a 563-date Alpha158 sample.
    quality_records: list[dict[str, object]] = []
    for signal_date, positions in ordered.groupby(
        date_column, sort=True
    ).groups.items():
        row_positions = np.asarray(list(positions), dtype=int)
        raw = ordered.loc[row_positions, features].apply(
            pd.to_numeric, errors="coerce"
        ).to_numpy(dtype=float)
        infinite_before = np.isinf(raw).sum(axis=0).astype(int)
        clean = raw.copy()
        clean[np.isinf(clean)] = np.nan
        finite_before = np.isfinite(clean).sum(axis=0).astype(int)
        all_null = finite_before == 0

        # np.nanmedian emits a warning for all-null columns.  Their outputs are
        # explicitly overwritten below, so use a finite placeholder first.
        safe_clean = clean.copy()
        safe_clean[:, all_null] = 0.0
        median = np.median(safe_clean, axis=0)
        filled = np.where(np.isnan(clean), median, clean)
        mad = np.median(np.abs(filled - median), axis=0)
        robust_scale = params.mad_scale_constant * mad
        has_positive_scale = np.isfinite(robust_scale) & (robust_scale > 0)
        half_width = params.winsorize_mad_multiplier * robust_scale
        lower = median - half_width
        upper = median + half_width
        winsorized = filled.copy()
        if has_positive_scale.any():
            winsorized[:, has_positive_scale] = np.clip(
                winsorized[:, has_positive_scale],
                lower[has_positive_scale],
                upper[has_positive_scale],
            )
        clipped_count = (
            (filled < lower) | (filled > upper)
        ).sum(axis=0).astype(int)
        clipped_count[~has_positive_scale] = 0

        standard_deviation = winsorized.std(axis=0, ddof=params.zscore_ddof)
        zero_variance = (
            ~np.isfinite(standard_deviation)
        ) | (standard_deviation <= params.zero_variance_tolerance)
        zscore = np.zeros_like(winsorized, dtype=float)
        nonconstant = ~zero_variance
        if nonconstant.any():
            zscore[:, nonconstant] = (
                winsorized[:, nonconstant]
                - winsorized[:, nonconstant].mean(axis=0)
            ) / standard_deviation[nonconstant]

        # Preserve the documented semantics for columns with no observations:
        # their output is zero and their descriptive statistics are null.
        median[all_null] = np.nan
        mad[all_null] = np.nan
        robust_scale[all_null] = np.nan
        lower[all_null] = np.nan
        upper[all_null] = np.nan
        standard_deviation[all_null] = 0.0
        transformed.loc[row_positions, features] = zscore
        post_mean = zscore.mean(axis=0)
        post_std = zscore.std(axis=0, ddof=0)
        for index, name in enumerate(features):
            quality_records.append(
                {
                    date_column: pd.Timestamp(signal_date),
                    "feature": name,
                    "cross_section_rows": int(len(row_positions)),
                    "finite_before": int(finite_before[index]),
                    "missing_before": int(
                        len(row_positions) - finite_before[index]
                    ),
                    "infinite_before": int(infinite_before[index]),
                    "median": float(median[index]),
                    "mad": float(mad[index]),
                    "robust_scale": float(robust_scale[index]),
                    "winsor_lower": float(lower[index]),
                    "winsor_upper": float(upper[index]),
                    "clipped_count": int(clipped_count[index]),
                    "zero_variance": bool(zero_variance[index]),
                    "all_null": bool(all_null[index]),
                    "post_zscore_mean": float(post_mean[index]),
                    "post_zscore_std_ddof0": float(post_std[index]),
                    "finite_after": int(np.isfinite(zscore[:, index]).sum()),
                }
            )

    quality = pd.DataFrame(quality_records).sort_values(
        [date_column, "feature"]
    ).reset_index(drop=True)
    return transformed, quality
