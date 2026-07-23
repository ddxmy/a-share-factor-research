import pandas as pd
import numpy as np
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'jyb_20260701_54'
FACTOR_TYPE = 'T-1_factor'
FORMULA = 'Cs_ZScore(Mul(Ts_MAD(turn, 10), Ts_Residual(turn, Log(amt), 20)))'

def factor_jyb_20260701_54(start_date, end_date, md_data_file, return_fillna_dic=False):
    """10日MAD加权的20日换手率对对数成交额残差的截面ZScore


    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'jyb_20260701_54' 的 DataFrame，index 为 (dt, Ticker)
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
    amt_panel = md_data['amt'].unstack()
    turn_panel = md_data['turn'].unstack()

    # 换手率10日MAD
    turn_mean_10 = turn_panel.rolling(10, min_periods=1).mean()
    mad_turn_10 = (turn_panel - turn_mean_10).abs().rolling(10, min_periods=1).mean()

    # turn ~ ln(amt) 的20日滚动回归残差
    log_amt = np.log(amt_panel + 1e-12)
    x_mean = log_amt.rolling(20, min_periods=1).mean()
    y_mean = turn_panel.rolling(20, min_periods=1).mean()
    x_var = ((log_amt - x_mean) ** 2).rolling(20, min_periods=1).mean()
    xy_cov = ((log_amt - x_mean) * (turn_panel - y_mean)).rolling(20, min_periods=1).mean()
    beta = xy_cov / (x_var + 1e-12)
    residual = turn_panel - (y_mean + beta * (log_amt - x_mean))

    # MAD × 残差
    prod = mad_turn_10 * residual

    # Cs_ZScore(...): 截面Z-Score
    cs_mean = prod.mean(axis=1)
    cs_std = prod.std(axis=1)
    zscore = (prod - cs_mean) / (cs_std + 1e-12)

    factor_df = pd.DataFrame()
    factor_df[FACTOR_NAME] = zscore.stack()
    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_jyb_20260701_54(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.describe())
