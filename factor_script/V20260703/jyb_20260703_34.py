import pandas as pd
import numpy as np
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'jyb_20260703_34'
FACTOR_TYPE = 'T-1_factor'
FORMULA = 'If(And(Greater(close, Ts_Quantile(high, 20, 0.9)), Less(Volatility_Ratio(5, 20), 0.8)), Neg(Ts_Return(close, 1)), Ts_Return(close, 1))'

def factor_jyb_20260703_34(start_date, end_date, md_data_file, return_fillna_dic=False):
    """价格突破20日90分位且低波动时取反向收益，否则取收益（高位突破反转）


    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'jyb_20260703_34' 的 DataFrame，index 为 (dt, Ticker)
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
    high_panel = md_data['high'].unstack()

    # 价格突破20日90分位 且 低波动率 → 反向收益
    high_q90 = high_panel.rolling(20, min_periods=1).quantile(0.9)
    vol_ratio = close_panel.rolling(5, min_periods=1).std() / (close_panel.rolling(20, min_periods=1).std() + 1e-12)
    cond = (close_panel > high_q90) & (vol_ratio < 0.8)

    ret_1d = close_panel.pct_change(1)
    if_val = np.where(cond, -ret_1d, ret_1d)

    factor_df = pd.DataFrame()
    factor_df[FACTOR_NAME] = pd.DataFrame(if_val, index=close_panel.index, columns=close_panel.columns).stack()
    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_jyb_20260703_34(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.describe())
