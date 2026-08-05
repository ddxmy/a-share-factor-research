"""Researcher-owned implementations for the frozen manual-factor registry.

Factor formulas intentionally remain unimplemented until a researcher supplies
and validates a point-in-time daily panel.
"""

import pandas as pd


def compute_rev5(panel: pd.DataFrame) -> pd.Series:
    raise NotImplementedError("Researcher implementation required: REV5")


def compute_mom20(panel: pd.DataFrame) -> pd.Series:
    raise NotImplementedError("Researcher implementation required: MOM20")


def compute_mom60(panel: pd.DataFrame) -> pd.Series:
    raise NotImplementedError("Researcher implementation required: MOM60")


def compute_vol20(panel: pd.DataFrame) -> pd.Series:
    raise NotImplementedError("Researcher implementation required: VOL20")


def compute_idiovol20(panel: pd.DataFrame) -> pd.Series:
    raise NotImplementedError("Researcher implementation required: IDIOVOL20")


def compute_turn20(panel: pd.DataFrame) -> pd.Series:
    raise NotImplementedError("Researcher implementation required: TURN20")


def compute_volsurp20(panel: pd.DataFrame) -> pd.Series:
    raise NotImplementedError("Researcher implementation required: VOLSURP20")


def compute_amihud20(panel: pd.DataFrame) -> pd.Series:
    raise NotImplementedError("Researcher implementation required: AMIHUD20")


def compute_pv_corr20(panel: pd.DataFrame) -> pd.Series:
    raise NotImplementedError("Researcher implementation required: PV_CORR20")


def compute_close_pos5(panel: pd.DataFrame) -> pd.Series:
    raise NotImplementedError("Researcher implementation required: CLOSE_POS5")
