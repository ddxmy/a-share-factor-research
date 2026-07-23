import pandas as pd
import numpy as np
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'momentum_1'
FACTOR_TYPE = 'T-1_factor'


def factor_momentum_1(start_date, end_date, md_data_file, return_fillna_dic=False):
    """1日动量因子（T-1日频）。

    计算方法：基于日频收盘价计算过去1个交易日的收益率（close / close.shift(1) - 1），
    并在 `run_factor` 中自动向后平移一天以用于 T-1 因子。

    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'momentum_20' 的 DataFrame，index 为 (dt, Ticker)
    """
    factor_name = FACTOR_NAME
    if return_fillna_dic:
        return {factor_name: 0.0, 'data': ['MD']}

    # 取足够的历史窗口
    start_date_ = int(get_tradingday(None, start_date=20120101,
                      end_date=start_date, shift=-60)[0])

    md_data = pd.read_parquet(md_data_file, filters=[('dt', '>=', pd.to_datetime(str(
        start_date_))), ('dt', '<=', pd.to_datetime(str(end_date)))])

    # 复权
    for col in ['open', 'close', 'high', 'low', 'vwap', 'pre_close']:
        if col in md_data.columns:
            md_data[col] = md_data[col] * md_data.get('adjfactor', 1)

    # 权重处理（与示例一致）
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

    # 动量实现：计算 1 日动量（反转）

    mom_df = md_data['pct_chg'].unstack()/100  

    factor_series = -mom_df.stack()
    factor_df = pd.DataFrame({factor_name: factor_series})

    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_momentum_1(start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.groupby(level=0).count().head())
