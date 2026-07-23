import pandas as pd
import numpy as np
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'jyb_20260703_22'
FACTOR_TYPE = 'T-1_factor'
FORMULA = 'Cs_Rank(Ts_MAD(Abs(Ts_Residual(Div(close, vwap), turn, 20)), 10))'

def factor_jyb_20260703_22(start_date, end_date, md_data_file, return_fillna_dic=False):
    """收盘/均价对换手20日残差的10日绝对偏差截面排名


    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'jyb_20260703_22' 的 DataFrame，index 为 (dt, Ticker)
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
    turn_panel = md_data['turn'].unstack()
    vwap_panel = md_data['vwap'].unstack()

    # close/vwap 对换手率的20日滚动回归残差
    price_ratio = close_panel / (vwap_panel + 1e-12)
    x_mean = turn_panel.rolling(20, min_periods=1).mean()
    y_mean = price_ratio.rolling(20, min_periods=1).mean()
    x_var = ((turn_panel - x_mean) ** 2).rolling(20, min_periods=1).mean()
    xy_cov = ((turn_panel - x_mean) * (price_ratio - y_mean)).rolling(20, min_periods=1).mean()
    beta = xy_cov / (x_var + 1e-12)
    residual = price_ratio - (y_mean + beta * (turn_panel - x_mean))

    # |残差| 的10日MAD
    abs_res = residual.abs()
    abs_res_mean = abs_res.rolling(10, min_periods=1).mean()
    mad_val = (abs_res - abs_res_mean).abs().rolling(10, min_periods=1).mean()

    # Cs_Rank(...): 截面排名
    factor_df = pd.DataFrame()
    factor_df[FACTOR_NAME] = mad_val.rank(axis=1, pct=True).stack()
    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_jyb_20260703_22(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.describe())
