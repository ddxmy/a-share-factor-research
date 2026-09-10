"""Compatibility bridges for the original manual-factor function names."""

import pandas as pd

from factor_modules import (
    amihud20,
    close_pos5,
    idiovol20,
    mom20,
    mom60,
    pv_corr20,
    rev5,
    turn20,
    vol20,
    volsurp20,
)


def compute_rev5(panel: pd.DataFrame) -> pd.DataFrame:
    return rev5.compute(panel)


def compute_mom20(panel: pd.DataFrame) -> pd.DataFrame:
    return mom20.compute(panel)


def compute_mom60(panel: pd.DataFrame) -> pd.DataFrame:
    return mom60.compute(panel)


def compute_vol20(panel: pd.DataFrame) -> pd.DataFrame:
    return vol20.compute(panel)


def compute_idiovol20(panel: pd.DataFrame) -> pd.DataFrame:
    return idiovol20.compute(panel)


def compute_turn20(panel: pd.DataFrame) -> pd.DataFrame:
    return turn20.compute(panel)


def compute_volsurp20(panel: pd.DataFrame) -> pd.DataFrame:
    return volsurp20.compute(panel)


def compute_amihud20(panel: pd.DataFrame) -> pd.DataFrame:
    return amihud20.compute(panel)


def compute_pv_corr20(panel: pd.DataFrame) -> pd.DataFrame:
    return pv_corr20.compute(panel)


def compute_close_pos5(panel: pd.DataFrame) -> pd.DataFrame:
    return close_pos5.compute(panel)
