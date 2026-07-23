import pandas as pd
import numpy as np
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'xzt_20260622_8'
FACTOR_TYPE = 'T-1_factor'
FORMULA = 'Cs_Rank(Mul(Sign(Div(Sub(close,vwap),vwap)), Exp(Abs(Div(Sub(close,vwap),vwap)))))'

def factor_xzt_20260622_8(start_date, end_date, md_data_file, return_fillna_dic=False):
    """对VWAP偏离做指数级放大（保留符号）


    注：VWAP偏离百分比的单调变换在Cs_Rank下等价，多种公式均得到32.22分。
    此处选择语义最匹配的Exp形式。

    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'xzt_20260622_8' 的 DataFrame，index 为 (dt, Ticker)
    """
    if return_fillna_dic:
        fill_val = 0.0
        return {FACTOR_NAME: fill_val, 'data': ['MD']}

    # 向前取数据：无需长窗口
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
    # Div(Sub(close, vwap), vwap): VWAP偏离百分比
    vwap_dev_pct = (md_data['close'] - md_data['vwap']) / md_data['vwap']

    # Mul(Sign(...), Exp(Abs(...))): 指数级放大（保留符号）
    exp_amplified = np.sign(vwap_dev_pct) * np.exp(np.clip(np.abs(vwap_dev_pct), -50, 50))

    # Cs_Rank(...): 截面排名
    factor_df = pd.DataFrame()
    factor_df[FACTOR_NAME] = exp_amplified.unstack().rank(axis=1, pct=True).stack()
    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_xzt_20260622_8(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.describe())
