"""Pinned Microsoft Qlib Alpha158 feature catalog.

The expressions and ordering mirror ``Alpha158DL.get_feature_config`` as used
by the default ``Alpha158`` handler.  The upstream source is pinned so future
Qlib changes cannot silently alter this research definition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


QLIB_COMMIT = "79633dd9506ea689e5400dea0197717b5b3d74b7"
QLIB_LOADER_URL = (
    "https://github.com/microsoft/qlib/blob/"
    f"{QLIB_COMMIT}/qlib/contrib/data/loader.py"
)
QLIB_HANDLER_URL = (
    "https://github.com/microsoft/qlib/blob/"
    f"{QLIB_COMMIT}/qlib/contrib/data/handler.py"
)
QLIB_LOADER_SHA256 = (
    "814b7f7ab3d418ae3c87ce352220080b239eba2670eac9e38376b794be4075cb"
)
QLIB_HANDLER_SHA256 = (
    "b621481c6009c39066c67c71390fd2bea635f56daf9f2c4e38817eff268e3232"
)
ROLLING_WINDOWS = (5, 10, 20, 30, 60)


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    expression: str
    operator: str
    family: str
    window: int
    required_inputs: str
    economic_interpretation: str
    expected_direction: str = "not_preassigned"

    def as_record(self, position: int) -> dict[str, object]:
        return {
            "position": position,
            "name": self.name,
            "expression": self.expression,
            "operator": self.operator,
            "family": self.family,
            "window": self.window,
            "required_inputs": self.required_inputs,
            "economic_interpretation": self.economic_interpretation,
            "expected_direction": self.expected_direction,
        }


def _spec(
    name: str,
    expression: str,
    operator: str,
    family: str,
    window: int,
    required_inputs: str,
    economic_interpretation: str,
) -> FeatureSpec:
    return FeatureSpec(
        name=name,
        expression=expression,
        operator=operator,
        family=family,
        window=window,
        required_inputs=required_inputs,
        economic_interpretation=economic_interpretation,
    )


def _rolling_specs(windows: Iterable[int]) -> list[FeatureSpec]:
    specs: list[FeatureSpec] = []
    for d in windows:
        specs.append(_spec(f"ROC{d}", f"Ref($close, {d})/$close", "ROC", "trend", d, "close", "past-to-current price ratio"))
    for d in windows:
        specs.append(_spec(f"MA{d}", f"Mean($close, {d})/$close", "MA", "trend", d, "close", "moving-average distance"))
    for d in windows:
        specs.append(_spec(f"STD{d}", f"Std($close, {d})/$close", "STD", "volatility", d, "close", "normalized price volatility"))
    for d in windows:
        specs.append(_spec(f"BETA{d}", f"Slope($close, {d})/$close", "BETA", "trend", d, "close", "normalized linear trend slope"))
    for d in windows:
        specs.append(_spec(f"RSQR{d}", f"Rsquare($close, {d})", "RSQR", "trend_quality", d, "close", "linearity of the price trend"))
    for d in windows:
        specs.append(_spec(f"RESI{d}", f"Resi($close, {d})/$close", "RESI", "trend_quality", d, "close", "normalized trend residual"))
    for d in windows:
        specs.append(_spec(f"MAX{d}", f"Max($high, {d})/$close", "MAX", "price_location", d, "high,close", "distance to rolling high"))
    for d in windows:
        specs.append(_spec(f"MIN{d}", f"Min($low, {d})/$close", "LOW", "price_location", d, "low,close", "distance to rolling low"))
    for d in windows:
        specs.append(_spec(f"QTLU{d}", f"Quantile($close, {d}, 0.8)/$close", "QTLU", "price_location", d, "close", "distance to upper close quantile"))
    for d in windows:
        specs.append(_spec(f"QTLD{d}", f"Quantile($close, {d}, 0.2)/$close", "QTLD", "price_location", d, "close", "distance to lower close quantile"))
    for d in windows:
        specs.append(_spec(f"RANK{d}", f"Rank($close, {d})", "RANK", "price_location", d, "close", "current close percentile in its window"))
    for d in windows:
        specs.append(
            _spec(
                f"RSV{d}",
                f"($close-Min($low, {d}))/(Max($high, {d})-Min($low, {d})+1e-12)",
                "RSV",
                "price_location",
                d,
                "close,high,low",
                "close location within the rolling high-low range",
            )
        )
    for d in windows:
        specs.append(_spec(f"IMAX{d}", f"IdxMax($high, {d})/{d}", "IMAX", "timing", d, "high", "recency of rolling high"))
    for d in windows:
        specs.append(_spec(f"IMIN{d}", f"IdxMin($low, {d})/{d}", "IMIN", "timing", d, "low", "recency of rolling low"))
    for d in windows:
        specs.append(
            _spec(
                f"IMXD{d}",
                f"(IdxMax($high, {d})-IdxMin($low, {d}))/{d}",
                "IMXD",
                "timing",
                d,
                "high,low",
                "relative timing of recent high and low",
            )
        )
    for d in windows:
        specs.append(
            _spec(
                f"CORR{d}",
                f"Corr($close, Log($volume+1), {d})",
                "CORR",
                "price_volume",
                d,
                "close,volume",
                "price-level and log-volume correlation",
            )
        )
    for d in windows:
        specs.append(
            _spec(
                f"CORD{d}",
                f"Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), {d})",
                "CORD",
                "price_volume",
                d,
                "close,volume",
                "price-ratio and volume-ratio correlation",
            )
        )
    for d in windows:
        specs.append(_spec(f"CNTP{d}", f"Mean($close>Ref($close, 1), {d})", "CNTP", "directional", d, "close", "share of up days"))
    for d in windows:
        specs.append(_spec(f"CNTN{d}", f"Mean($close<Ref($close, 1), {d})", "CNTN", "directional", d, "close", "share of down days"))
    for d in windows:
        specs.append(
            _spec(
                f"CNTD{d}",
                f"Mean($close>Ref($close, 1), {d})-Mean($close<Ref($close, 1), {d})",
                "CNTD",
                "directional",
                d,
                "close",
                "up-day minus down-day share",
            )
        )
    for d in windows:
        specs.append(
            _spec(
                f"SUMP{d}",
                f"Sum(Greater($close-Ref($close, 1), 0), {d})/(Sum(Abs($close-Ref($close, 1)), {d})+1e-12)",
                "SUMP",
                "momentum",
                d,
                "close",
                "positive price change share",
            )
        )
    for d in windows:
        specs.append(
            _spec(
                f"SUMN{d}",
                f"Sum(Greater(Ref($close, 1)-$close, 0), {d})/(Sum(Abs($close-Ref($close, 1)), {d})+1e-12)",
                "SUMN",
                "momentum",
                d,
                "close",
                "negative price change share",
            )
        )
    for d in windows:
        specs.append(
            _spec(
                f"SUMD{d}",
                f"(Sum(Greater($close-Ref($close, 1), 0), {d})-Sum(Greater(Ref($close, 1)-$close, 0), {d}))/(Sum(Abs($close-Ref($close, 1)), {d})+1e-12)",
                "SUMD",
                "momentum",
                d,
                "close",
                "signed price-change balance",
            )
        )
    for d in windows:
        specs.append(_spec(f"VMA{d}", f"Mean($volume, {d})/($volume+1e-12)", "VMA", "volume", d, "volume", "volume moving-average distance"))
    for d in windows:
        specs.append(_spec(f"VSTD{d}", f"Std($volume, {d})/($volume+1e-12)", "VSTD", "volume", d, "volume", "normalized volume volatility"))
    for d in windows:
        specs.append(
            _spec(
                f"WVMA{d}",
                f"Std(Abs($close/Ref($close, 1)-1)*$volume, {d})/(Mean(Abs($close/Ref($close, 1)-1)*$volume, {d})+1e-12)",
                "WVMA",
                "price_volume",
                d,
                "close,volume",
                "dispersion of volume-weighted absolute returns",
            )
        )
    for d in windows:
        specs.append(
            _spec(
                f"VSUMP{d}",
                f"Sum(Greater($volume-Ref($volume, 1), 0), {d})/(Sum(Abs($volume-Ref($volume, 1)), {d})+1e-12)",
                "VSUMP",
                "volume",
                d,
                "volume",
                "positive volume-change share",
            )
        )
    for d in windows:
        specs.append(
            _spec(
                f"VSUMN{d}",
                f"Sum(Greater(Ref($volume, 1)-$volume, 0), {d})/(Sum(Abs($volume-Ref($volume, 1)), {d})+1e-12)",
                "VSUMN",
                "volume",
                d,
                "volume",
                "negative volume-change share",
            )
        )
    for d in windows:
        specs.append(
            _spec(
                f"VSUMD{d}",
                f"(Sum(Greater($volume-Ref($volume, 1), 0), {d})-Sum(Greater(Ref($volume, 1)-$volume, 0), {d}))/(Sum(Abs($volume-Ref($volume, 1)), {d})+1e-12)",
                "VSUMD",
                "volume",
                d,
                "volume",
                "signed volume-change balance",
            )
        )
    return specs


def alpha158_specs() -> list[FeatureSpec]:
    """Return the 158 default Alpha158 features in official Qlib order."""

    specs = [
        _spec("KMID", "($close-$open)/$open", "KMID", "candlestick", 1, "open,close", "intraday body return"),
        _spec("KLEN", "($high-$low)/$open", "KLEN", "candlestick", 1, "open,high,low", "intraday range"),
        _spec("KMID2", "($close-$open)/($high-$low+1e-12)", "KMID2", "candlestick", 1, "open,high,low,close", "body relative to range"),
        _spec("KUP", "($high-Greater($open, $close))/$open", "KUP", "candlestick", 1, "open,high,close", "upper shadow relative to open"),
        _spec("KUP2", "($high-Greater($open, $close))/($high-$low+1e-12)", "KUP2", "candlestick", 1, "open,high,low,close", "upper shadow relative to range"),
        _spec("KLOW", "(Less($open, $close)-$low)/$open", "KLOW", "candlestick", 1, "open,low,close", "lower shadow relative to open"),
        _spec("KLOW2", "(Less($open, $close)-$low)/($high-$low+1e-12)", "KLOW2", "candlestick", 1, "open,high,low,close", "lower shadow relative to range"),
        _spec("KSFT", "(2*$close-$high-$low)/$open", "KSFT", "candlestick", 1, "open,high,low,close", "close displacement from range midpoint"),
        _spec("KSFT2", "(2*$close-$high-$low)/($high-$low+1e-12)", "KSFT2", "candlestick", 1, "open,high,low,close", "normalized close displacement"),
        _spec("OPEN0", "$open/$close", "OPEN", "price_ratio", 0, "open,close", "open-to-close ratio"),
        _spec("HIGH0", "$high/$close", "HIGH", "price_ratio", 0, "high,close", "high-to-close ratio"),
        _spec("LOW0", "$low/$close", "LOW_PRICE", "price_ratio", 0, "low,close", "low-to-close ratio"),
        _spec("VWAP0", "$vwap/$close", "VWAP", "price_ratio", 0, "vwap,close", "VWAP-to-close ratio"),
    ]
    specs.extend(_rolling_specs(ROLLING_WINDOWS))
    if len(specs) != 158:
        raise AssertionError(f"Expected 158 Alpha158 features, got {len(specs)}")
    if len({spec.name for spec in specs}) != len(specs):
        raise AssertionError("Alpha158 feature names are not unique")
    return specs


def alpha158_catalog() -> pd.DataFrame:
    """Return a tabular, reader-facing catalog."""

    return pd.DataFrame(
        [spec.as_record(position) for position, spec in enumerate(alpha158_specs(), 1)]
    )
