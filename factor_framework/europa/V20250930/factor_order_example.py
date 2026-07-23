import pandas as pd
import datetime as dt

# ---- 因子元信息 ----
FACTOR_NAME = 'order_example'
FACTOR_TYPE = 'TOrder'
FACTOR_OWNER = 'example'


def factor_order_example(transaction_df, return_fillna_dic=False):
    """委买委卖单量比因子（逐笔委托）。

    取最近100笔连续竞价阶段（MDTime >= 93000000）的限价委托单（OrderType==2），
    计算买入委托量（OrderBSFlag==1）与卖出委托量（OrderBSFlag==2）的比值作为因子值。

    Args:
        transaction_df: 单只股票单日的逐笔委托 DataFrame，index 为 (dt, Ticker)
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.Series: {'order_example': score}
    """
    factor_name = 'order_example'
    if return_fillna_dic:
        # 返回因子为 nan 时的填充值
        return {factor_name: 0}

    dt, Ticker = transaction_df.index[0]
    condition = (Ticker[0] == '3' and dt.strftime(
        '%Y-%m-%d') >= '20200824') or (Ticker[0:2] == '68')

    def zhucezhi_help(md_data, column, weight):
        md_data[column] = (
            (md_data[column] / md_data['pre_close'] - 1) / weight + 1) * md_data['pre_close']
    if condition:
        zhucezhi_help(transaction_df, 'OrderPrice', weight=2)
        zhucezhi_help(transaction_df, 'ul_price', weight=2)
        zhucezhi_help(transaction_df, 'dl_price', weight=2)

    transaction_df = transaction_df[(transaction_df['OrderType'] == 2)]    #
    # 选择连续竞价阶段的逐笔成交数据
    transaction_df = transaction_df[transaction_df['MDTime'] >= 93000000]

    # 取两个时间,比值
    transaction_df1 = transaction_df.iloc[-100:]
    transaction_df11 = transaction_df1[transaction_df1['OrderBSFlag'] == 1]
    transaction_df12 = transaction_df1[transaction_df1['OrderBSFlag'] == 2]
    amt11 = transaction_df11['OrderQty'].sum()
    amt12 = transaction_df12['OrderQty'].sum()
    score = amt11 / (amt12 + 1)
    factor_dict = {factor_name: score}

    return pd.Series(factor_dict)


if __name__ == '__main__':
    data_file = "/workspace/public/data/project/for_factor/project1_prod/order_europa/20190805.pq"
    tmp_df = pd.read_parquet(data_file).groupby(level=[0, 1]).apply(
        lambda x: factor_order_example(x))  # 对 index 分组
    print(9999999999999999999, tmp_df.describe())
