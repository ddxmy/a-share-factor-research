"""Independent Pandas/NumPy implementation of the pinned Alpha158 catalog."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .alpha158_catalog import ROLLING_WINDOWS, alpha158_catalog


EPSILON = 1e-12


def _rolling_regression(
    series: pd.Series,
    window: int,
    output: str,
) -> pd.Series:
    """Match Qlib's rolling slope, R-square, and current-point residual."""

    def calculate(values: np.ndarray) -> float:
        values = np.asarray(values, dtype=float)
        positions = np.arange(1, len(values) + 1, dtype=float)
        valid = np.isfinite(values)
        if valid.sum() < 2:
            return np.nan
        x = positions[valid]
        y = values[valid]
        x_centered = x - x.mean()
        y_centered = y - y.mean()
        x_ss = np.dot(x_centered, x_centered)
        if x_ss == 0:
            return np.nan
        xy = np.dot(x_centered, y_centered)
        slope = xy / x_ss
        if output == "slope":
            return float(slope)
        if output == "rsquare":
            y_ss = np.dot(y_centered, y_centered)
            if y_ss == 0:
                return np.nan
            return float((xy * xy) / (x_ss * y_ss))
        if output == "resi":
            if not np.isfinite(values[-1]):
                return np.nan
            intercept = y.mean() - slope * x.mean()
            return float(values[-1] - (slope * positions[-1] + intercept))
        raise ValueError(output)

    result = series.rolling(window, min_periods=1).apply(calculate, raw=True)
    if output == "rsquare":
        near_constant = np.isclose(
            series.rolling(window, min_periods=1).std(),
            0,
            atol=2e-5,
        )
        result.loc[near_constant] = np.nan
    return result


def _rolling_idx(series: pd.Series, window: int, kind: str) -> pd.Series:
    def locate(values: np.ndarray) -> float:
        if len(values) == 0:
            return np.nan
        if kind == "max":
            return float(np.asarray(values).argmax() + 1)
        if kind == "min":
            return float(np.asarray(values).argmin() + 1)
        raise ValueError(kind)

    return series.rolling(window, min_periods=1).apply(locate, raw=True)


def compute_alpha158_for_instrument(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute all 158 features for one instrument in official column order."""

    required = {"open", "high", "low", "close", "vwap", "volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing Alpha158 base columns: {sorted(missing)}")

    data = frame.sort_index().copy()
    for column in required:
        data[column] = data[column].astype("float32")
    open_ = data["open"]
    high = data["high"]
    low = data["low"]
    close = data["close"]
    vwap = data["vwap"]
    volume = data["volume"]

    # Accumulate Series in a mapping and materialize once. Repeated column
    # insertion fragments a DataFrame and emits noisy PerformanceWarnings.
    result: dict[str, pd.Series] = {}
    greater_open_close = pd.concat([open_, close], axis=1).max(axis=1)
    less_open_close = pd.concat([open_, close], axis=1).min(axis=1)
    price_range = high - low
    result["KMID"] = (close - open_) / open_
    result["KLEN"] = price_range / open_
    result["KMID2"] = (close - open_) / (price_range + EPSILON)
    result["KUP"] = (high - greater_open_close) / open_
    result["KUP2"] = (high - greater_open_close) / (price_range + EPSILON)
    result["KLOW"] = (less_open_close - low) / open_
    result["KLOW2"] = (less_open_close - low) / (price_range + EPSILON)
    result["KSFT"] = (2 * close - high - low) / open_
    result["KSFT2"] = (2 * close - high - low) / (price_range + EPSILON)
    result["OPEN0"] = open_ / close
    result["HIGH0"] = high / close
    result["LOW0"] = low / close
    result["VWAP0"] = vwap / close

    close_ref1 = close.shift(1)
    volume_ref1 = volume.shift(1)
    price_diff = close - close_ref1
    volume_diff = volume - volume_ref1
    positive_price = price_diff.clip(lower=0)
    negative_price = (-price_diff).clip(lower=0)
    absolute_price = price_diff.abs()
    positive_volume = volume_diff.clip(lower=0)
    negative_volume = (-volume_diff).clip(lower=0)
    absolute_volume = volume_diff.abs()
    price_ratio = close / close_ref1
    volume_ratio = volume / volume_ref1
    absolute_return_volume = (price_ratio - 1).abs() * volume

    for window in ROLLING_WINDOWS:
        roll_close = close.rolling(window, min_periods=1)
        roll_high = high.rolling(window, min_periods=1)
        roll_low = low.rolling(window, min_periods=1)
        roll_volume = volume.rolling(window, min_periods=1)

        result[f"ROC{window}"] = close.shift(window) / close
        result[f"MA{window}"] = roll_close.mean() / close
        result[f"STD{window}"] = roll_close.std() / close
        result[f"BETA{window}"] = (
            _rolling_regression(close, window, "slope") / close
        )
        result[f"RSQR{window}"] = _rolling_regression(
            close, window, "rsquare"
        )
        result[f"RESI{window}"] = (
            _rolling_regression(close, window, "resi") / close
        )
        result[f"MAX{window}"] = roll_high.max() / close
        result[f"MIN{window}"] = roll_low.min() / close
        result[f"QTLU{window}"] = roll_close.quantile(0.8) / close
        result[f"QTLD{window}"] = roll_close.quantile(0.2) / close
        result[f"RANK{window}"] = roll_close.rank(pct=True)
        rolling_min = roll_low.min()
        rolling_max = roll_high.max()
        result[f"RSV{window}"] = (
            close - rolling_min
        ) / (rolling_max - rolling_min + EPSILON)
        result[f"IMAX{window}"] = (
            _rolling_idx(high, window, "max") / window
        )
        result[f"IMIN{window}"] = (
            _rolling_idx(low, window, "min") / window
        )
        result[f"IMXD{window}"] = (
            _rolling_idx(high, window, "max")
            - _rolling_idx(low, window, "min")
        ) / window
        result[f"CORR{window}"] = close.rolling(
            window, min_periods=1
        ).corr(np.log(volume + 1))
        result[f"CORD{window}"] = price_ratio.rolling(
            window, min_periods=1
        ).corr(np.log(volume_ratio + 1))
        result[f"CNTP{window}"] = (
            (close > close_ref1).astype(float).rolling(
                window, min_periods=1
            ).mean()
        )
        result[f"CNTN{window}"] = (
            (close < close_ref1).astype(float).rolling(
                window, min_periods=1
            ).mean()
        )
        result[f"CNTD{window}"] = (
            result[f"CNTP{window}"] - result[f"CNTN{window}"]
        )
        price_denominator = (
            absolute_price.rolling(window, min_periods=1).sum() + EPSILON
        )
        result[f"SUMP{window}"] = (
            positive_price.rolling(window, min_periods=1).sum()
            / price_denominator
        )
        result[f"SUMN{window}"] = (
            negative_price.rolling(window, min_periods=1).sum()
            / price_denominator
        )
        result[f"SUMD{window}"] = (
            positive_price.rolling(window, min_periods=1).sum()
            - negative_price.rolling(window, min_periods=1).sum()
        ) / price_denominator
        result[f"VMA{window}"] = roll_volume.mean() / (
            volume + EPSILON
        )
        result[f"VSTD{window}"] = roll_volume.std() / (
            volume + EPSILON
        )
        weighted_roll = absolute_return_volume.rolling(
            window, min_periods=1
        )
        result[f"WVMA{window}"] = weighted_roll.std() / (
            weighted_roll.mean() + EPSILON
        )
        volume_denominator = (
            absolute_volume.rolling(window, min_periods=1).sum()
            + EPSILON
        )
        result[f"VSUMP{window}"] = (
            positive_volume.rolling(window, min_periods=1).sum()
            / volume_denominator
        )
        result[f"VSUMN{window}"] = (
            negative_volume.rolling(window, min_periods=1).sum()
            / volume_denominator
        )
        result[f"VSUMD{window}"] = (
            positive_volume.rolling(window, min_periods=1).sum()
            - negative_volume.rolling(window, min_periods=1).sum()
        ) / volume_denominator

    official_order = alpha158_catalog()["name"].tolist()
    result_frame = pd.DataFrame(result, index=data.index)
    if set(result_frame.columns) != set(official_order):
        missing_features = set(official_order) - set(result_frame.columns)
        extra_features = set(result_frame.columns) - set(official_order)
        raise AssertionError(
            f"Alpha158 output mismatch: missing={missing_features}, "
            f"extra={extra_features}"
        )
    return result_frame[official_order]


def compute_alpha158_panel(
    panel: pd.DataFrame,
    *,
    instrument_column: str = "instrument",
    date_column: str = "trade_date",
) -> pd.DataFrame:
    """Compute Alpha158 for a long base-field panel."""

    records: list[pd.DataFrame] = []
    for instrument, stock in panel.groupby(instrument_column, sort=True):
        indexed = stock.set_index(pd.to_datetime(stock[date_column])).drop(
            columns=[instrument_column, date_column]
        )
        features = compute_alpha158_for_instrument(indexed).reset_index()
        features = features.rename(columns={"index": date_column})
        features.insert(0, instrument_column, instrument)
        records.append(features)
    return pd.concat(records, ignore_index=True).sort_values(
        [date_column, instrument_column]
    )
