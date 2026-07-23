import pandas as pd
import numpy as np
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'jyb_20260703_11'
FACTOR_TYPE = 'T-1_factor'
FORMULA = 'Cs_Rank(If(Greater(Slope(close, 20), 0), Cs_Rank(Div(Ts_Return(close, 1), Ts_Std(Ts_Return(close, 1), 20))), Neg(Cs_Rank(turn))))'

def factor_jyb_20260703_11(start_date, end_date, md_data_file, return_fillna_dic=False):
    """上升趋势时取收益/波动排名的截面排名，否则取反向换手排名


    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'jyb_20260703_11' 的 DataFrame，index 为 (dt, Ticker)
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

    # 20日线性回归斜率
    slope_x = np.arange(20)
    slope_20 = close_panel.rolling(20, min_periods=1).apply(
        lambda y: np.polyfit(slope_x[:len(y)], y, 1)[0] if len(y) > 1 else 0, raw=True)

    # 1日收益率 / 20日标准差 → 截面排名
    ret_1d = close_panel.pct_change(1)
    ret_std_20 = ret_1d.rolling(20, min_periods=1).std()
    ret_risk = (ret_1d / (ret_std_20 + 1e-12)).rank(axis=1, pct=True)

    # 换手率取负 → 截面排名
    neg_turn_rank = (-turn_panel).rank(axis=1, pct=True)

    # 斜率 > 0 → 取风险调整收益排名; 否则 → 取负换手率排名
    if_val = np.where(slope_20 > 0, ret_risk, neg_turn_rank)

    # Cs_Rank(...): 截面排名
    factor_df = pd.DataFrame()
    factor_df[FACTOR_NAME] = pd.DataFrame(if_val, index=close_panel.index, columns=close_panel.columns).rank(axis=1, pct=True).stack()
    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_jyb_20260703_11(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.describe())
