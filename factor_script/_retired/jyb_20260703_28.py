import pandas as pd
import numpy as np
import sys, os
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
_scripts_dir = os.path.join(_project_root, 'scripts')
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
from marketdata import get_tradingday

# ---- 因子元信息 ----
FACTOR_NAME = 'jyb_20260703_28'
FACTOR_TYPE = 'T-1_factor'

# Cache the fill value from the computed result (matching FormulaExecutor's dynamic median)
_fill_cache: dict = {}


def factor_jyb_20260703_28(start_date, end_date, md_data_file, return_fillna_dic=False):
    """收益与归一化换手20日协动性的10日衰减加权截面Z-Score

    复现公式: Cs_ZScore(Ts_DecayExp(Ts_Correlation(Ts_Return(close, 1), Cs_Rank(turn), 20), 10))
    原始分数: 48.7

    Args:
        start_date: 起始日期
        end_date: 结束日期
        md_data_file: 市场数据 parquet 文件路径
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.DataFrame: 包含因子列 'jyb_20260703_28' 的 DataFrame，index 为 (dt, Ticker)
    """
    factor_name = FACTOR_NAME
    if return_fillna_dic:
        fill_val = _fill_cache.get(factor_name, 0.0)
        return {factor_name: fill_val, 'data': ['MD']}

    # 向前取数据：需要足够长的窗口用于时序计算
    start_date_ = int(get_tradingday(None, start_date=20120101,
                      end_date=start_date, shift=-260)[0])
    md_data = pd.read_parquet(md_data_file, filters=[
        ('dt', '>=', pd.to_datetime(str(start_date_))),
        ('dt', '<=', pd.to_datetime(str(end_date)))
    ])

    # ---- 复权 (adjfactor) ----
    for col in ['open', 'close', 'high', 'low', 'vwap', 'pre_close']:
        if col in md_data.columns:
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
        if col in md_data.columns:
            zhucezhi_help(md_data, col)
    md_data.loc[condition, 'pct_chg'] = md_data.loc[condition, 'pct_chg'] / 2

    # ---- 因子计算 ----
    from evaluation.evaluator import FormulaExecutor

    executor = FormulaExecutor(md_data_file=md_data_file, start_date=start_date_, end_date=end_date)

    result_panel = executor.compute("Cs_ZScore(Ts_DecayExp(Ts_Correlation(Ts_Return(close, 1), Cs_Rank(turn), 20), 10))")

    factor_df = pd.DataFrame()
    factor_df[factor_name] = result_panel.stack()

    # Cache fill value from actual computed panel median
    _fill_cache[factor_name] = float(factor_df[factor_name].unstack().median().median())

    return factor_df


if __name__ == '__main__':
    start_date, end_date = 20160101, 20161231
    md_data_file = "/workspace/public/data/project/other_data/MD_data/md_20120101_20250706.pq"
    factor_df = factor_jyb_20260703_28(
        start_date, end_date, md_data_file, return_fillna_dic=False)
    print(factor_df.describe())
