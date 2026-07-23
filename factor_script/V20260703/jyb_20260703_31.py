import pandas as pd
import numpy as np
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'jyb_20260703_31'
FACTOR_TYPE = 'T-1_factor'
FORMULA = 'Cs_Winsorize(Ts_Mean(Power(Log(Div(high, low)), 2), 10), 0.01, 0.99)'

def factor_jyb_20260703_31(start_date, end_date, md_data_file, return_fillna_dic=False):
    """高低价对数差平方的10日均值1%~99%缩尾（对数振幅能量）


    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'jyb_20260703_31' 的 DataFrame，index 为 (dt, Ticker)
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
    high_panel = md_data['high'].unstack()
    low_panel = md_data['low'].unstack()

    # log(high/low)^2 的10日均值 → 截面缩尾
    log_range = np.log(high_panel / (low_panel + 1e-12) + 1e-12)
    log_range_sq = log_range ** 2
    mean_val = log_range_sq.rolling(10, min_periods=1).mean()
    # Cs_Winsorize(..., 0.01, 0.99): 截面缩尾（按截面1%/99%分位数clip）
    lo = mean_val.quantile(0.01, axis=1)
    hi = mean_val.quantile(0.99, axis=1)
    winsorized = mean_val.clip(lower=lo, upper=hi, axis=0)

    factor_df = pd.DataFrame()
    factor_df[FACTOR_NAME] = winsorized.stack()
    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_jyb_20260703_31(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.describe())
