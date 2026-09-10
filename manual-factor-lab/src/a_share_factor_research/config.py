"""Configuration and private catalog paths for factor research."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping

import yaml


@dataclass(frozen=True)
class ResearchProfile:
    """The immutable settings used to evaluate a research run."""

    universe: str
    signal_price: str
    execution_price: str
    signal_frequency_days: int
    holding_period_days: tuple[int, ...]
    horizons: tuple[int, ...]
    ic_metric: str
    top_k: int
    quintiles: int
    one_way_cost_bps: int
    test_years: tuple[int, ...]


@dataclass(frozen=True)
class ResolvedPaths:
    """The fixed private catalog inputs beneath ``A_SHARE_DATA_ROOT``."""

    data_root: Path
    daily_panel: Path
    pit_csi300: Path
    csi300_open: Path
    open_eligibility: Path


def load_profile(path: Path) -> ResearchProfile:
    """Load and validate a frozen research profile from YAML."""
    with Path(path).open(encoding="utf-8") as profile_file:
        values = yaml.safe_load(profile_file)

    if not isinstance(values, dict):
        raise ValueError("Research profile must be a YAML mapping.")

    try:
        profile = ResearchProfile(
            universe=values["universe"],
            signal_price=values["signal_price"],
            execution_price=values["execution_price"],
            signal_frequency_days=values["signal_frequency_days"],
            holding_period_days=tuple(values["holding_period_days"]),
            horizons=tuple(values["horizons"]),
            ic_metric=values["ic_metric"],
            top_k=values["top_k"],
            quintiles=values["quintiles"],
            one_way_cost_bps=values["one_way_cost_bps"],
            test_years=tuple(values["test_years"]),
        )
    except KeyError as exc:
        raise ValueError(f"Research profile is missing {exc.args[0]!r}.") from exc

    _validate_profile(profile)
    return profile


def resolve_data_root(environ: Mapping[str, str] | None = None) -> ResolvedPaths:
    """Resolve the existing private catalog root and its fixed child paths."""
    environment = os.environ if environ is None else environ
    data_root_value = environment.get("A_SHARE_DATA_ROOT")
    if not data_root_value:
        raise RuntimeError("A_SHARE_DATA_ROOT must name the existing private data directory.")

    data_root = Path(data_root_value).expanduser()
    if not data_root.is_dir():
        raise RuntimeError("A_SHARE_DATA_ROOT must name an existing directory.")

    return ResolvedPaths(
        data_root=data_root,
        daily_panel=data_root / "derived" / "daily_panel.parquet",
        pit_csi300=data_root / "derived" / "universe" / "pit_csi300.parquet",
        csi300_open=data_root / "derived" / "benchmark" / "csi300_open.parquet",
        open_eligibility=data_root / "derived" / "tradability" / "open_eligibility.parquet",
    )


def _validate_profile(profile: ResearchProfile) -> None:
    if profile.signal_price != "close":
        raise ValueError("signal_price must be 'close'.")
    if profile.execution_price != "next_open":
        raise ValueError("execution_price must be 'next_open'.")
    if (
        not profile.horizons
        or profile.horizons[0] != 1
        or any(horizon <= 0 for horizon in profile.horizons)
        or any(left >= right for left, right in zip(profile.horizons, profile.horizons[1:]))
    ):
        raise ValueError("horizons must be positive, strictly increasing, and include 1.")
    if profile.holding_period_days != profile.horizons:
        raise ValueError("holding_period_days must exactly match horizons.")
