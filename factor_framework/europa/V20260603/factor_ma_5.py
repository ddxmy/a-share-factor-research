import pandas as pd
import numpy as np
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'ma_5'
FACTOR_TYPE = 'T-1_factor'


def factor_ma_5(start_date, end_date, md_data_file, return_fillna_dic=False):
    """5日均线因子（T-1日频）。

    计算方法：基于日频复权收盘价计算过去5个交易日的简单移动平均线，
    并返回当前价格相对于5日均线的偏离率（close / ma5 - 1）。
    该因子在 `run_factor` 中自动向后平移一天以用于 T-1 因子。

    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'ma_5' 的 DataFrame，index 为 (dt, Ticker)
    """
    factor_name = FACTOR_NAME
    if return_fillna_dic:
        return {factor_name: 0.0, 'data': ['MD']}

    start_date_ = int(get_tradingday(None, start_date=20120101,
                      end_date=start_date, shift=-60)[0])

    md_data = pd.read_parquet(md_data_file, filters=[('dt', '>=', pd.to_datetime(str(
        start_date_))), ('dt', '<=', pd.to_datetime(str(end_date)))])

    for col in ['open', 'close', 'high', 'low', 'vwap', 'pre_close']:
        if col in md_data.columns:
            md_data[col] = md_data[col] * md_data.get('adjfactor', 1)

    md_data['weight'] = 1
    condition = (((md_data.reset_index()["Ticker"].apply(lambda x: x[0] == '3')) & (md_data.reset_index()[
                 "dt"] >= '20200824')) | (md_data.reset_index()["Ticker"].apply(lambda x: x[0:2] == '68'))).values
    md_data.loc[condition, 'weight'] = 2

    def zhucezhi_help(md_data, column):
        if column in md_data.columns:
            md_data[column] = ((md_data[column] / md_data['pre_close'] - 1) /
                               md_data['weight'] + 1) * md_data['pre_close']

    for c in ['open', 'close', 'high', 'low', 'vwap']:
        zhucezhi_help(md_data, c)

    if 'close' not in md_data.columns:
        raise RuntimeError('market data must contain close column')

    close_df = md_data['close'].unstack()
    ma5 = close_df.rolling(5, min_periods=1).mean() 
    ma_df = close_df / ma5 - 1

    factor_series = ma_df.stack()
    factor_df = pd.DataFrame({factor_name: factor_series})

    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_ma_5(start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.groupby(level=0).count().head())