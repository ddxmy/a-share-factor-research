# coding:utf-8
# CreatDate:2026/2/12
# Author:KangkangSun
import os
import time
import pandas as pd

try:
    from clickhouse_driver import Client
    host = "192.168.76.172"
    user = "default"
    password = os.environ.get("CLICKHOUSE_PASSWORD")
    if not password:
        raise RuntimeError("CLICKHOUSE_PASSWORD is not configured")
    port = "9000"
    port_for_sqlalchemy = "8123"
    database = "default"
    client = Client(
        host=host,
        user=user,
        password=password,
        port=port,
        database=database,
    )
except Exception as e:
    print('jiekou.py', e)

columns_dict_trans = {
    "date": "dt",
    "stk": "Ticker",
    'time': "MDTime",
    # 'trd_prc': 'TradePrice',
    'trade_price': 'TradePrice',
    # 'trd_vol': 'TradeQty',
    'trade_vol': 'TradeQty',
    'index': 'TradeIndex',
    'ask_order': 'TradeSellNo',
    'bid_order': 'TradeBuyNo',
    'func_code': 'TradeType',  # 67 c 撤单
    'bs': 'TradeBSFlag',  # 66-B, 83-S
}

columns_dict_order = {
    "stk": "Ticker",

    # 'trd_date': 'dt',
    # 'trd_time': "MDTime",
    # 'trd_order': 'OrderIndex',

    'date': 'dt',
    'time': "MDTime",
    'trade_order': 'OrderIndex',

    'trade_price': 'OrderPrice',
    'trade_vol': 'OrderQty',

    # 'trd_index': 'TradeIndex',  # trd_index  SZ 每个股票独立，从0开始累加; SH 貌似所有股票公用一个？
    'order_kind': 'OrderType',
    'func_code': 'OrderBSFlag',  # 66-B买，83-S 卖
}

# 'index'

columns_dict_tick = {
    "stk": "Ticker",
    "date": "dt",
    'time': "MDTime",
    # 'ask_vol_all': '',
    # 'bid_vol_all': '',
}

def connent_by_clickhouse(code, date, data_type):
    # "20160104", '000002.SZ' # 停牌
    if data_type == 'Transaction':
        columns = ['exchange', 'stk', 'date', 'time', 'datetime', 'index', 'func_code', 'order_type', 'bs', 'trade_price', 'trade_vol', 'ask_order', 'bid_order']
        data_partition = 'transe_gpt4'
    elif data_type == 'Order':
        columns = ['exchange', 'stk', 'date', 'time', 'datetime', 'index', 'trade_order', 'order_kind', 'func_code', 'trade_price', 'trade_vol']
        data_partition = 'order_gpt4'
    elif data_type == 'Stock_base':
        columns = ['stk', 'date', 'time', 'datetime', 'ask_vol_all', 'bid_vol_all', 'ask_prc_1', 'bid_prc_1', 'ask_vol_1', 'bid_vol_1',]
        data_partition = 'tick_gpt4'

    columns_str = ",".join(columns)
    sql = f"""SELECT {columns_str}
    FROM default.{data_partition}
    WHERE
        stk = '{code}'
        AND date = {date}
    """ # LIMIT 10;
    result = client.execute(sql)
    data = pd.DataFrame(result, columns=columns)
    if data_type == 'Transaction':
        # print(11111111111111111, data[['index', 'func_code']])
        data = data.rename(columns=columns_dict_trans)
        data['TradeType'] = data['TradeType'].map({48: 0, 67: 1}).fillna(data['TradeType'])  # 48:0：成交； 67：1 其他：撤销等; 只有2个值。大部分float，个别 int
        data['TradeBSFlag'] = data['TradeBSFlag'].map({66: 1, 83: 2}).fillna(data['TradeBSFlag'])  # 66-B, 83-S
        data['TradePrice'] = data['TradePrice'].astype(float)
        data['TradeMoney'] = data['TradeQty'] * data['TradePrice']
        for column in data.columns:
            if column not in ['exchange', 'datetime']:
                data[column] = data[column].astype(float)
        data = data.sort_values(by=['MDTime', 'TradeIndex'])

    elif data_type == 'Order':
        data = data.rename(columns=columns_dict_order)
        data['OrderType'] = data['OrderType'].map({48:2, 49:1, 85:3,    65:2, 68:10}).fillna(data['OrderType'])  ##SZ;SH
        data['OrderBSFlag'] = data['OrderBSFlag'].map({66:1, 83:2}).fillna(data['OrderBSFlag'])  # SZ/SH
        data['OrderType'] = data['OrderType'].map({50:5, 86:6, 87:7, 88:3, 89:4}).fillna(data['OrderType']) ## SZ 2016及之前
        data['OrderBSFlag'] = data['OrderBSFlag'].map({67:5}).fillna(data['OrderBSFlag'])  # SZ67:5 2016及之前
        data['OrderPrice'] = data['OrderPrice'].astype(float)
        # print(111111111111, data)
        for column in data.columns:
            if column not in ['exchange', 'datetime']:
                data[column] = data[column].astype(float)
        data = data.sort_values(by=['MDTime', 'index'])

    elif data_type == 'Stock_base':
        data = data.rename(columns=columns_dict_tick)
        for column in data.columns:
            if column not in ['exchange', 'datetime']:
                data[column] = data[column].astype(float)

    if data.shape[0]:
        data['dt'] = pd.to_datetime(str(int(float(data['dt'].iloc[0]))))
    # code = code_help(data['Ticker'].iloc[0])
    # data['Ticker'] = code
    # data = data.set_index(['dt', 'Ticker'])
    return data


if __name__ == "__main__":
    print("Connecting to ClickHouse database...")
    code = "600519"
    date = 20241009
    # data_type = 'Transaction'
    # data_type = 'Order'
    data_type = 'tick'
    df = connent_by_clickhouse(code, date, data_type)  # 这个更快
    print(111111111111, df)
    ####################
    # from joblib import Parallel, delayed
    # from codes import codes
    # begin_time = time.time()
    # job_list = []
    # for code in codes[:100]:
    #     ############
    #     # df = connent_by_clickhouse(code, date, data_type)
    #     # print(11111111111111, code, df.shape)
    #     #########
    #     job_list.append(delayed(connent_by_clickhouse)(code, date, data_type))  # , seedseedseed=0
    # multi_work = Parallel(n_jobs=5, backend='multiprocessing')
    # result = multi_work(job_list)
    # ############
    # print(time.time()-begin_time)

"""
112.20528602600098
35.27163624763489
"""

