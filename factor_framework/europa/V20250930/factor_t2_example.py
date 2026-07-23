import pandas as pd
import numpy as np
##########
from marketdata import get_tradingday
##########

# ---- 因子元信息 ----
FACTOR_NAME = 't2_example'
FACTOR_TYPE = 'T-1_factor'


def factor_t2_example(start_date, end_date, md_data_file, return_fillna_dic=False):
    """波动率因子（T-1日频，无注册制修正）。

    基于日频行情数据，计算 (high - low) / close，
    取60日滚动0.75分位数，再截面排序为百分位数作为因子值，
    并在 run_factor 中自动向后平移一天。

    与 t1_example 的区别：仅做 adjfactor 复权，不进行科创板/创业板的
    涨跌幅 ±20% → ±10% 的注册制修正（zcz）。

    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 't2_example' 的 DataFrame，index 为 (dt, Ticker)
    """
    factor_name = 't2_example'
    if return_fillna_dic:
        # 返回因子为 nan 时的填充值, Todo:T-1_factor类因子需要包括数据源缩写(其列表在因子规范数据源检测一节)
        return {factor_name: 0.7312307334581126, 'data': ['MD']}

    # 计算全部股票在全部时间区间上的因子值,之后会在run_factor_demo函数中进行向后平移一天和样本的筛选
    start_date_ = int(get_tradingday(None, start_date=20120101,
                      end_date=start_date, shift=-70)[0])  # 60日滚动窗口 + 缓冲，至少取70天
    md_data = pd.read_parquet(md_data_file, filters=[('dt', '>=', pd.to_datetime(str(
        start_date_))), ('dt', '<=', pd.to_datetime(str(end_date)))])  # columns=['pct_chg']
    # adj
    md_data['open'] = md_data['open'] * md_data['adjfactor']
    md_data['close'] = md_data['close'] * md_data['adjfactor']
    md_data['high'] = md_data['high'] * md_data['adjfactor']
    md_data['low'] = md_data['low'] * md_data['adjfactor']
    md_data['vwap'] = md_data['vwap'] * md_data['adjfactor']
    md_data['pre_close'] = md_data['pre_close'] * md_data['adjfactor']

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
    # Div(Sub(high, low), close) = (high - low) / close
    factor_df[factor_name] = (md_data['high'] - md_data['low']) / md_data['close']
    # Ts_Quantile(..., 60, 0.75): 60日滚动0.75分位数
    factor_df[factor_name] = factor_df[factor_name].unstack().rolling(
        60, min_periods=1).quantile(0.75).stack()
    # Cs_Rank(..., pct=True): 截面排序为百分位数
    factor_df[factor_name] = factor_df[factor_name].unstack().rank(
        axis=1, pct=True).stack()

    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_t2_example(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(99999999999, factor_df.describe())
