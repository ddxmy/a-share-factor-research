"""Generated factor script for admitted factor #1.

Formula:
    Div(Sub(close, Ts_Min(low, 5)), Sub(Ts_Max(high, 5), Ts_Min(low, 5)))
"""
import os
import sys

import numpy as np
import pandas as pd


FACTOR_NAME = 'Close_Position_Location_5d'
FACTOR_TYPE = "T-1_factor"
FORMULA = 'Div(Sub(close, Ts_Min(low, 5)), Sub(Ts_Max(high, 5), Ts_Min(low, 5)))'


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def factor_1_Close_Position_Location_5d(start_date, end_date, md_data_file, return_fillna_dic=False):
    """Compute this generated formula factor in europa T-1 factor format."""
    if return_fillna_dic:
        return {FACTOR_NAME: np.nan, "data": ["MD"]}

    from evaluation.evaluator import FormulaExecutor
    from marketdata import get_tradingday

    lookback_start = int(get_tradingday(
        None, start_date=20120101, end_date=start_date, shift=-260,
    )[0])
    executor = FormulaExecutor(
        md_data_file=md_data_file,
        start_date=lookback_start,
        end_date=end_date,
    )
    panel = executor.compute(FORMULA)
    stacked = panel.stack()
    stacked.name = FACTOR_NAME
    stacked.index.names = ["dt", "Ticker"]
    return pd.DataFrame(stacked)


if __name__ == "__main__":
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_1_Close_Position_Location_5d(start_date, end_date, md_data_file)
    print(factor_df.groupby(level=0).count().head())
