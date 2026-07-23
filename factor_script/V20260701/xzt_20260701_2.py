import pandas as pd
import numpy as np
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'xzt_20260701_2'
FACTOR_TYPE = 'T-1_factor'
FORMULA = 'Cs_Rank(Div(Inverse(Ts_MAD(turn, 20)), Ts_Median(turn, 20)))'

def factor_xzt_20260701_2(start_date, end_date, md_data_file, return_fillna_dic=False):
    """过去20日换手率绝对中位差的倒数除以过去20日换手率中位数的截面排名

    """
    if return_fillna_dic:
        fill_val = 0.0
        return {FACTOR_NAME: fill_val, 'data': ['MD']}

    start_date_ = int(get_tradingday(None, start_date=20120101,
                      end_date=start_date, shift=-260)[0])
    md_data = pd.read_parquet(md_data_file, filters=[
        ('dt', '>=', pd.to_datetime(str(start_date_))),
        ('dt', '<=', pd.to_datetime(str(end_date)))
    ])

    for col in ['open', 'close', 'high', 'low', 'vwap', 'pre_close']:
        md_data[col] = md_data[col] * md_data['adjfactor']

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

    # Ts_MAD(turn, 20): 过去20日换手率平均绝对偏差
    def rolling_mad(s):
        return (s - s.mean()).abs().mean()
    turn_panel = md_data['turn'].unstack()
    mad_20 = turn_panel.rolling(20, min_periods=1).apply(rolling_mad, raw=True)
    # Ts_Median(turn, 20): 过去20日换手率中位数
    median_20 = turn_panel.rolling(20, min_periods=1).median()
    # Div(Inverse(mad_20), median_20)
    result = (1.0 / mad_20) / median_20
    # Cs_Rank
    factor_df = pd.DataFrame()
    factor_df[FACTOR_NAME] = result.rank(axis=1, pct=True).stack()
    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_xzt_20260701_2(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.describe())
