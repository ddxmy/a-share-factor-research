import pandas as pd
import numpy as np
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'jyb_20260703_39'
FACTOR_TYPE = 'T-1_factor'
FORMULA = 'If(And(Greater(close, BBands_Upper(close, 20, 2)), Greater(RSI(close, 14), 70)), Neg(Cs_Rank(Ts_Return(close, 1))), Cs_Rank(Ts_Return(close, 1)))'

def factor_jyb_20260703_39(start_date, end_date, md_data_file, return_fillna_dic=False):
    """突破布林上轨且RSI超买时取反向收益排名，否则取收益排名（超买反转）


    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'jyb_20260703_39' 的 DataFrame，index 为 (dt, Ticker)
    """
    if return_fillna_dic:
        fill_val = 0.0
        return {FACTOR_NAME: fill_val, 'data': ['MD']}

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

    # 布林带上轨突破
    bb_ma = close_panel.rolling(20, min_periods=1).mean()
    bb_std = close_panel.rolling(20, min_periods=1).std()
    bb_upper = bb_ma + 2 * bb_std
    above_bb = close_panel > bb_upper

    # RSI超买 (>70)
    delta = close_panel.diff()
    avg_gain = delta.where(delta > 0, 0).rolling(14, min_periods=1).mean()
    avg_loss = (-delta.where(delta < 0, 0)).rolling(14, min_periods=1).mean()
    rsi = 100 - 100 / (1 + avg_gain / (avg_loss + 1e-12))
    overbought = rsi > 70

    # 超买条件 → 反向收益排名
    cond = above_bb & overbought
    ret_1d = close_panel.pct_change(1)
    ret_rank = ret_1d.rank(axis=1, pct=True)
    if_val = np.where(cond, -ret_rank, ret_rank)

    factor_df = pd.DataFrame()
    factor_df[FACTOR_NAME] = pd.DataFrame(if_val, index=close_panel.index, columns=close_panel.columns).stack()
    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_jyb_20260703_39(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.describe())
