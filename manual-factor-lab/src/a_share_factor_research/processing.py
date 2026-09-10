"""Cross-sectional transformations for registered raw factor values."""

import numpy as np
import pandas as pd

from .registry import FactorDefinition


_MAD_SCALE = 1.4826
_MAD_LIMIT = 5
_REQUIRED_COLUMNS = {"trade_date", "security_id", "raw_value"}


def prepare_factor_cross_sections(
    raw_panel: pd.DataFrame, definition: FactorDefinition
) -> pd.DataFrame:
    """Impute, MAD-clip, z-score, and direct a raw factor independently per date."""
    missing_columns = _REQUIRED_COLUMNS.difference(raw_panel.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Raw factor panel is missing required columns: {missing}.")
    if definition.pre_registered_direction not in {"positive", "negative"}:
        raise ValueError("pre_registered_direction must be 'positive' or 'negative'.")

    prepared = raw_panel.copy()
    original_index = prepared.index.copy()
    prepared.index = pd.RangeIndex(len(prepared))
    prepared["winsorized_value"] = np.nan
    prepared["zscore_value"] = np.nan

    for _, index in prepared.groupby("trade_date", sort=False, dropna=False).groups.items():
        raw_values = pd.to_numeric(prepared.loc[index, "raw_value"], errors="coerce")
        finite_values = raw_values.where(np.isfinite(raw_values))
        median = finite_values.median()
        imputed_values = finite_values.fillna(median)

        if imputed_values.notna().any():
            mad = (imputed_values - median).abs().median()
            lower_bound = median - _MAD_LIMIT * _MAD_SCALE * mad
            upper_bound = median + _MAD_LIMIT * _MAD_SCALE * mad
            winsorized_values = imputed_values.clip(lower=lower_bound, upper=upper_bound)
        else:
            winsorized_values = imputed_values

        prepared.loc[index, "winsorized_value"] = winsorized_values
        if np.isfinite(winsorized_values).sum() >= 2:
            standard_deviation = winsorized_values.std(ddof=0)
            if pd.notna(standard_deviation) and standard_deviation != 0:
                prepared.loc[index, "zscore_value"] = (
                    (winsorized_values - winsorized_values.mean()) / standard_deviation
                )

    direction = 1 if definition.pre_registered_direction == "positive" else -1
    prepared["directed_score"] = direction * prepared["zscore_value"]
    prepared.index = original_index
    return prepared
