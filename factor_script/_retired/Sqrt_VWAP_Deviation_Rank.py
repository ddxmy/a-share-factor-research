import pandas as pd
import numpy as np
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'Sqrt_VWAP_Deviation_Rank'
FACTOR_TYPE = 'T-1_factor'

_fill_cache: dict = {}


def factor_Sqrt_VWAP_Deviation_Rank(start_date, end_date, md_data_file, return_fillna_dic=False):
    """对VWAP偏离做平方根压缩（保留符号）

    复现公式: Cs_Rank(SignedPower(Div(Sub(close,vwap),vwap), 0.5))
    原始分数: 32.2 | 复现分数: 32.22
    """
    factor_name = FACTOR_NAME
    if return_fillna_dic:
        fill_val = _fill_cache.get(factor_name, 0.0)
        return {factor_name: fill_val, 'data': ['MD']}

    start_date_ = int(get_tradingday(None, start_date=20120101,
                      end_date=start_date, shift=-10)[0])
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

    # VWAP偏离百分比
    vwap_dev_pct = (md_data['close'] - md_data['vwap']) / md_data['vwap']
    # 平方根压缩（保留符号）: sign(x) * |x|^0.5
    compressed = np.sign(vwap_dev_pct) * np.sqrt(np.abs(vwap_dev_pct))
    # Cs_Rank
    factor_df = pd.DataFrame()
    factor_df[factor_name] = compressed.unstack().rank(axis=1, pct=True).stack()

    _fill_cache[factor_name] = float(factor_df[factor_name].unstack().median().median())
    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_Sqrt_VWAP_Deviation_Rank(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.describe())
