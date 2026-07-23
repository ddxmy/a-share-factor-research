import pandas as pd
import numpy as np
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'volume_price_flow_20'
FACTOR_TYPE = 'T-1_factor'


def factor_volume_price_flow_20(start_date, end_date, md_data_file, return_fillna_dic=False):
    """20 日 open-volume 相关因子（T-1 日频）。

    计算方法：基于每只股票 20 日滚动相关系数：
        factor = -1 * corr(open, volume, 20)
    该因子在 `run_factor` 中自动向后平移一天以用于 T-1 因子。

    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'volume_price_flow_20' 的 DataFrame，index 为 (dt, Ticker)
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
    condition = (((md_data.reset_index()["Ticker"].apply(lambda x: x[0] == '3')) & (md_data.reset_index()["dt"] >= '20200824')) |
                 (md_data.reset_index()["Ticker"].apply(lambda x: x[0:2] == '68'))).values
    md_data.loc[condition, 'weight'] = 2

    def zhucezhi_help(md_data, column):
        if column in md_data.columns:
            md_data[column] = ((md_data[column] / md_data['pre_close'] - 1) /
                               md_data['weight'] + 1) * md_data['pre_close']

    for c in ['open', 'close', 'high', 'low', 'vwap']:
        zhucezhi_help(md_data, c)

    if 'open' not in md_data.columns or 'volume' not in md_data.columns:
        raise RuntimeError('market data must contain open and volume columns')

    open_df = md_data['open'].unstack()
    volume_df = md_data['volume'].unstack()

    corr_df = abs(open_df.rolling(20, min_periods=20).corr(volume_df))
    factor_series = corr_df.stack()
    factor_df = pd.DataFrame({factor_name: factor_series})

    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20181231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_volume_price_flow_20(start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.groupby(level=0).count().head())
