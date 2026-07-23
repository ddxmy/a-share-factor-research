import datetime as dt
import pandas as pd
import numpy as np
pd.set_option('display.max_columns', None)   # show all columns

# ---- 因子元信息 ----
FACTOR_NAME = 'trade_example'
FACTOR_TYPE = 'TTransaction'

# T日因子逻辑类别
# 放量角度
# 价格波动
# 筹码分布
# 价格形态
# 买单强度-挂单价格激进度
# 买单强度-订单结构
# 买单强度-总量强度
# 买单强度-时间强度
# 卖单强度-挂单价格激进度
# 卖单强度-订单结构
# 卖单强度-总量强度
# 卖单强度-时间强度


def fun_get_time(time1, sec_delta):
    # 计算给定时间戳 time1 在 sec_delta 秒后的时间戳
    tmp_time = dt.datetime.strptime(str(time1)[:-3], '%H%M%S')
    tmp_time2 = tmp_time + dt.timedelta(seconds=sec_delta)
    tmp_time2_str = tmp_time2.strftime('%H%M%S') + str(time1)[-3:]
    if (int(tmp_time2_str) > 113000000) & (time1 <= 113000000):
        adj_tmp_time2 = tmp_time2 + dt.timedelta(seconds=1.5 * 3600)
        adj_tmp_time2_str = adj_tmp_time2.strftime('%H%M%S') + str(time1)[-3:]
        return int(adj_tmp_time2_str)
    elif (int(tmp_time2_str) < 130000000) & (time1 >= 130000000):
        adj_tmp_time2 = tmp_time2 - dt.timedelta(seconds=1.5 * 3600)
        adj_tmp_time2_str = adj_tmp_time2.strftime('%H%M%S') + str(time1)[-3:]
        return int(adj_tmp_time2_str)
    elif (int(tmp_time2_str) < 93000000) & (time1 >= 93000000):
        adj_tmp_time2_str = '92500000'
        return int(adj_tmp_time2_str)
    elif (time1 < 93000000):
        adj_tmp_time2 = tmp_time2 + dt.timedelta(seconds=4 * 60)
        adj_tmp_time2_str = adj_tmp_time2.strftime('%H%M%S') + str(time1)[-3:]
        return int(adj_tmp_time2_str)
    else:
        return int(tmp_time2_str)


def factor_trade_example(transaction_df, return_fillna_dic=False):
    """主动买入金额因子（逐笔成交）。

    取最近100笔连续竞价阶段的逐笔成交数据，
    计算主动买入（TradeBSFlag==1）的成交金额总和作为因子值。

    Args:
        transaction_df: 单只股票单日的逐笔成交 DataFrame，index 为 (dt, Ticker)
        return_fillna_dic: 若为 True，返回因子缺失时的填充值字典

    Returns:
        pd.Series: {'trade_example': score}
    """
    factor_name = 'trade_example'
    if return_fillna_dic:
        # 返回因子为 nan 时的填充值
        return {factor_name: 12.9}
    # 注册制
    dt, Ticker = transaction_df.index[0]
    condition = (Ticker[0] == '3' and dt.strftime(
        '%Y-%m-%d') >= '20200824') or (Ticker[0:2] == '68')

    def zhucezhi_help(md_data, column, weight):
        md_data[column] = (
            (md_data[column] / md_data['pre_close'] - 1) / weight + 1) * md_data['pre_close']
    if condition:
        zhucezhi_help(transaction_df, 'TradePrice', weight=2)
    # 数据过滤
    transaction_df = transaction_df[(transaction_df['TradePrice'] > 0) & (
        transaction_df['TradeMoney'] > 0)]  # 去除深圳撤单的逐笔成交数据
    # 选择连续竞价阶段的逐笔成交数据
    transaction_df = transaction_df[transaction_df['MDTime'] >= 93000000]

    transaction_df = transaction_df.iloc[-100:]
    # 交易时间取数据
    # transaction_df = transaction_df[transaction_df['MDTime'] >= max(fun_get_time(int(transaction_df.iloc[-1]['MDTime']), -300), 93000000)]  # 30/60/300

    # if transaction_df.shape[0] == 0:
    #     return pd.Series({factor_name: None})
    transaction_df1 = transaction_df[transaction_df['TradeBSFlag'] == 1]  # 主动买
    score = transaction_df1['TradeMoney'].sum()
    factor_dict = {factor_name: score}
    return pd.Series(factor_dict)

    # 格式上需要注意的部分：
    # 1.因子文件代码名称为'factor_因子名称.py';
    # 2.函数名称为'factor_因子名称()';
    # 3.在return_fillna_dic中返回的dict的key为因子名称;
    # 4.在返回的fDataFrame中列名也为因子名称;
    # 以上的四个因子名称应该统一。


if __name__ == '__main__':
    data_file = "/workspace/public/data/project/for_factor/project1_prod/transaction_europa/20160104.pq"
    data = pd.read_parquet(data_file)
    tmp_df = data.groupby(level=[0, 1]).apply(
        lambda x: factor_trade_example(x))  # 对 index 分组
    print(9999999999999999999, tmp_df.describe())
