import pandas as pd
import numpy as np
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'close_volume_corr_10_rank'
FACTOR_TYPE = 'T-1_factor'


def factor_close_volume_corr_10_rank(start_date, end_date, md_data_file, return_fillna_dic=False):
    """Returns 分位数组合的横截面排名因子（T-1 日频）。

    计算方法：
        Cs_Rank(Add(Ts_Quantile(Returns, 5, 0.9),
                    Sub(Ts_Quantile(Returns, 10, 0.75),
                        Ts_Quantile(Returns, 10, 0.25))))
    即：
        1. Returns = close / pre_close - 1：日收益率。
        2. Ts_Quantile(Returns, 5, 0.9)：5 日滚动 90% 分位数。
        3. Ts_Quantile(Returns, 10, 0.75)：10 日滚动 75% 分位数。
        4. Ts_Quantile(Returns, 10, 0.25)：10 日滚动 25% 分位数。
        5. raw = quantile_5_90 + quantile_10_75 - quantile_10_25。
        6. Cs_Rank(raw)：横截面排名。
    该因子在 `run_factor` 中自动向后平移一天以用于 T-1 因子。

    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列的 DataFrame，index 为 (dt, Ticker)
    """
    factor_name = FACTOR_NAME
    if return_fillna_dic:
        return {factor_name: np.nan, 'data': ['MD']}

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

    if 'close' not in md_data.columns or 'pre_close' not in md_data.columns:
        raise RuntimeError('market data must contain close and pre_close columns')

    # 计算日收益率 Returns = close / pre_close - 1
    md_data['returns'] = md_data['close'] / md_data['pre_close'] - 1

    # 转为 (dt, Ticker) 的宽表
    returns_df = md_data['returns'].unstack()

    # Ts_Quantile(Returns, 5, 0.9): 5 日滚动 90% 分位数
    quantile_5_90 = returns_df.rolling(5, min_periods=5).quantile(0.9)

    # Ts_Quantile(Returns, 10, 0.75): 10 日滚动 75% 分位数
    quantile_10_75 = returns_df.rolling(10, min_periods=10).quantile(0.75)

    # Ts_Quantile(Returns, 10, 0.25): 10 日滚动 25% 分位数
    quantile_10_25 = returns_df.rolling(10, min_periods=10).quantile(0.25)

    # Add(Ts_Quantile(Returns,5,0.9), Sub(Ts_Quantile(Returns,10,0.75), Ts_Quantile(Returns,10,0.25)))
    raw_factor = quantile_5_90 + quantile_10_75 - quantile_10_25

    # Cs_Rank: 每个交易日横截面分位排名 [0, 1]
    rank_df = raw_factor.rank(axis=1, pct=True)

    factor_series = rank_df.stack()
    factor_df = pd.DataFrame({factor_name: factor_series})

    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_close_volume_corr_10_rank(start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.groupby(level=0).count().head())
