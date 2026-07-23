"""Generated factor script for admitted factor #5.

Formula:
    Add(Div(Sub(close, Ts_Min(low, 5)), Sub(Ts_Max(high, 5), Ts_Min(low, 5))), Div(Sub(close, Ts_Min(low, 10)), Sub(Ts_Max(high, 10), Ts_Min(low, 10))))
"""
import os
import sys

import numpy as np
import pandas as pd


FACTOR_NAME = 'xzt_20260707_4'
FACTOR_TYPE = "T-1_factor"
FORMULA = 'Add(Div(Sub(close, Ts_Min(low, 5)), Sub(Ts_Max(high, 5), Ts_Min(low, 5))), Div(Sub(close, Ts_Min(low, 10)), Sub(Ts_Max(high, 10), Ts_Min(low, 10))))'


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def factor_xzt_20260707_4(start_date, end_date, md_data_file, return_fillna_dic=False):
    """Compute this generated formula factor in europa T-1 factor format."""
    if return_fillna_dic:
        return {FACTOR_NAME: np.nan, "data": ["MD"]}

    from marketdata import get_tradingday

    # 向前取数据：需要足够长的窗口用于时序计算
    start_date_ = int(get_tradingday(None, start_date=20120101,
                      end_date=start_date, shift=-260)[0])
    md_data = pd.read_parquet(md_data_file, filters=[
        ('dt', '>=', pd.to_datetime(str(start_date_))),
        ('dt', '<=', pd.to_datetime(str(end_date)))
    ])

    # ---- 复权 (adjfactor) ----
    for col in ['open', 'close', 'high', 'low', 'vwap', 'pre_close']:
        md_data[col] = md_data[col] * md_data['adjfactor']

    # ---- 注册制修正 (zcz) ----
    md_data['weight'] = 1
    condition = (
        ((md_data.reset_index()["Ticker"].apply(lambda x: x[0] == '3'))
         & (md_data.reset_index()["dt"] >= '20200824'))
        | (md_data.reset_index()["Ticker"].apply(lambda x: x[0:2] == '68'))
    ).values
    md_data.loc[condition, 'weight'] = 2

    def zhucezhi_help(md_data, column):
        md_data[column] = (
            (md_data[column] / md_data['pre_close'] - 1) /
            md_data['weight'] + 1
        ) * md_data['pre_close']

    for col in ['open', 'close', 'high', 'low', 'vwap']:
        zhucezhi_help(md_data, col)
    md_data.loc[condition, 'pct_chg'] = md_data.loc[condition, 'pct_chg'] / 2

    # ---- 因子计算 ----
    close_panel = md_data['close'].unstack()
    high_panel = md_data['high'].unstack()
    low_panel = md_data['low'].unstack()

    # 5日窗口：(close - min_low) / (max_high - min_low)
    min_low_5 = low_panel.rolling(window=5, min_periods=1).min()
    max_high_5 = high_panel.rolling(window=5, min_periods=1).max()
    pos_5d = (close_panel - min_low_5) / (max_high_5 - min_low_5)

    # 10日窗口：(close - min_low) / (max_high - min_low)
    min_low_10 = low_panel.rolling(window=10, min_periods=1).min()
    max_high_10 = high_panel.rolling(window=10, min_periods=1).max()
    pos_10d = (close_panel - min_low_10) / (max_high_10 - min_low_10)

    # 两个窗口的位置值相加
    factor_val = pos_5d + pos_10d

    factor_df = pd.DataFrame()
    factor_df[FACTOR_NAME] = factor_val.stack()

    return factor_df


if __name__ == "__main__":
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_xzt_20260707_4(start_date, end_date, md_data_file)
    print(factor_df.groupby(level=0).count().head())
