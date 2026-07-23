import pandas as pd
import numpy as np
##########
from marketdata import get_tradingday
##########

# ---- 因子元信息 ----
FACTOR_NAME = 't1_example'
FACTOR_TYPE = 'T-1_factor'

# run_factor.so calls factor_func twice: first to compute, then to get fill value.
# Cache the fill value from the computed result so it matches FormulaExecutor's dynamic median.
_fill_cache: dict = {}


def factor_t1_example(start_date, end_date, md_data_file, return_fillna_dic=False):
    """波动率因子（T-1日频）。

    基于日频行情数据，计算 (high - low) / open，
    再取5日滚动标准差作为因子值，并在 run_factor 中自动向后平移一天。

    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 't1_example' 的 DataFrame，index 为 (dt, Ticker)
    """
    factor_name = 't1_example'
    if return_fillna_dic:
        fill_val = _fill_cache.get(factor_name, 0.0)
        return {factor_name: fill_val, 'data': ['MD']}

    # 计算全部股票在全部时间区间上的因子值,之后会在run_factor_demo函数中进行向后平移一天和样本的筛选
    start_date_ = int(get_tradingday(None, start_date=20120101,
                      end_date=start_date, shift=-40)[0])  # 向前取的天数至少大于要用到的数据日期数+1天
    md_data = pd.read_parquet(md_data_file, filters=[('dt', '>=', pd.to_datetime(str(
        start_date_))), ('dt', '<=', pd.to_datetime(str(end_date)))])  # columns=['pct_chg']
    # adj
    md_data['open'] = md_data['open'] * md_data['adjfactor']
    md_data['close'] = md_data['close'] * md_data['adjfactor']
    md_data['high'] = md_data['high'] * md_data['adjfactor']
    md_data['low'] = md_data['low'] * md_data['adjfactor']
    md_data['vwap'] = md_data['vwap'] * md_data['adjfactor']
    md_data['pre_close'] = md_data['pre_close'] * md_data['adjfactor']
    # zcz
    md_data['weight'] = 1
    condition = (((md_data.reset_index()["Ticker"].apply(lambda x: x[0] == '3')) & (md_data.reset_index()[
                 "dt"] >= '20200824')) | (md_data.reset_index()["Ticker"].apply(lambda x: x[0:2] == '68'))).values
    md_data.loc[condition, 'weight'] = 2

    def zhucezhi_help(md_data, column):
        md_data[column] = ((md_data[column] / md_data['pre_close'] - 1) /
                           md_data['weight'] + 1) * md_data['pre_close']
    zhucezhi_help(md_data, 'open')
    zhucezhi_help(md_data, 'close')
    zhucezhi_help(md_data, 'high')
    zhucezhi_help(md_data, 'low')
    zhucezhi_help(md_data, 'vwap')
    md_data.loc[condition, 'pct_chg'] = md_data.loc[condition, 'pct_chg'] / 2

    factor_df = pd.DataFrame()
    factor_df[factor_name] = (md_data['high'] - md_data['low'])/md_data['open']
    panel = factor_df[factor_name].unstack().rolling(5, min_periods=5).std()
    factor_df[factor_name] = panel.stack()

    # Cache fill value from actual computed panel median (matching FormulaExecutor)
    _fill_cache[factor_name] = float(panel.median().median())

    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_t1_example(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(99999999999, factor_df.describe())
