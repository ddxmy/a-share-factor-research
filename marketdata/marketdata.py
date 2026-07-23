import os
import time
import json
import numpy as np
import pandas as pd

"""
pandas   2.0.3
"""
# 安装 pyarrow（推荐） 或者安装 fastparquet
# pip install pyarrow
# pip install fastparquet

#########
# data_dir_root = '/home/data14_2/data/'
# data_dir_root = '/data/baidu_netdisk/skk_data/data/data/'
data_dir_root = '/workspace/secret/skk/data/data/'
####
# other_data_dir = '/home/data14_2/project/other_data/'
# other_data_dir = '/data/baidu_netdisk/skk_data/data/project/other_data/'
other_data_dir = '/workspace/public/data/project/other_data/'
#########

# 获取交易日
def get_tradingday(pro=None, start_date=None, end_date=None, shift=0):
    """
    tradingday_list = get_tradingday(pro, start_date=20180101, end_date=20181231, shift=-2)
    tradingday_list = get_tradingday(pro, start_date=20180101, end_date=20181231, shift=0)
    """
    start_date = str(start_date)
    end_date = str(end_date)
    trade_day = None
    ####################
    if pro is not None:
        try:
            df = pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)  # exchange 默认上交所，SSE
            # df = pro.query('trade_cal', start_date=start_date, end_date=end_date)
            trade_day = df.loc[df['is_open'] == 1]['cal_date']
            trade_day = list(trade_day)[::-1]
        except Exception as e:
            print("get_tradingday 网络接口报错，已切换到本地交易日文件：", e)

    if trade_day is None:
        fallback_file = os.path.join(other_data_dir, 'tradingday_20120101_.json')
        if not os.path.exists(fallback_file):
            raise FileNotFoundError(f'Fallback tradingday file not found: {fallback_file}')
        with open(fallback_file, 'r', encoding='utf8') as f:
            trade_day = json.load(f)
        trade_day = [term for term in trade_day if term >= start_date and term <= end_date]

    # print(1111111111111111, trade_day)
    ########
    if shift > 0:
        trade_day = trade_day[:shift]
    elif shift < 0:
        trade_day = trade_day[shift:]
    return trade_day

# 获取某天的股票，这里不包含 沪深 B股。
# 稍后改进， TODO
def get_all_codes(date, market=None):
    """
    :param date:
    :param market:  主板、创业板、科创板、北交所
    :return:
    codes = get_all_codes(date=20130103, market=None)
    codes = get_all_codes(date=20230103, market=None)
    codes = get_all_codes(date=20230103, market='主板')
    codes = get_all_codes(date=20230103, market='创业板')
    codes = get_all_codes(date=20230103, market='科创板')
    """
    # all_data = json.load(open('/home/data/my_pro/other/行业上市情况.json', 'r', encoding="utf8"))
    all_data = json.load(open(f'{other_data_dir}/上市日期/list_date_19901219_.json', 'r', encoding="utf8"))
    # print(1111111111111111111, all_data['900921.SH'])
    # print(1111111111111111111, all_data['200625.SZ'])
    # input(11)
    # {'200625.SZ', '900934.SH', '201872.SZ', }
    data_filter = {code:all_data[code] for code in all_data if all_data[code]['上市日期'] <= str(date)}
    if market:
        data_filter = {code: all_data[code] for code in data_filter if data_filter[code]['market'] in market}
    result = list(data_filter.keys())
    result.sort()
    return result

# 获取股票的基础数据，如上市日期。板块等；
# 构造方式在 other/获取上市日期.py  调用 tushare 接口
# 老的结果，需要改进。 TODO
def get_code_basic_data():
    # all_data = json.load(open('/home/data/my_pro/other/行业上市情况.json', 'r', encoding="utf8")) # 不全，pass
    all_data = json.load(open(f'{other_data_dir}/上市日期/list_date_19901219_.json', 'r', encoding="utf8"))
    return all_data

def load_issue_date():
    base_data1 = json.load(open(f'{other_data_dir}/上市日期/list_date_19901219_.json', 'r', encoding="utf8"))
    base_data2 = json.load(open(f'{other_data_dir}/上市日期/new_share_issue_date_19901219_20250706.json', 'r', encoding="utf8"))
    base_data = {}
    for key in base_data1:
        base_data[key] = {"name": base_data1[key]['name'], "上市日期":base_data1[key]['上市日期']}
    for key in base_data2:
        if key not in base_data:
            base_data[key] = {"name": base_data2[key]['name'], "上市日期": base_data2[key]['上市日期']}
    return base_data

# 获取MD数据
def get_md_data(columns=None, start_date=None, end_date=None):
    ############
    # data_file = "/home/data/my_pro/MD/md_20230103_20240223.pkl"
    # data = pd.read_pickle(data_file)
    ############
    data_file = f"{other_data_dir}/MD_data/md_20120101_20250706.pq"
    if start_date:
        data = pd.read_parquet(data_file, columns=columns, filters=[('dt', '>=', pd.to_datetime(str(start_date))), ('dt', '<=', pd.to_datetime(str(end_date)))])
    else:
        data = pd.read_parquet(data_file, columns=columns)
    ############
    return data

# 获取 trade， order ， stock  数据
def get_data_by_date_my(data_type, code, date):
    # 每天每个股票一个文件， 都是 float64（order的 TradingPhaseCode 除外，字符串）
    date = str(date).replace('-', '')
    if data_type == "Transaction":
        # ['time_trade', 'trade_index', 'trade_buy_no', 'trade_sell_no', 'trade_price', 'trade_volume', 'trade_money', 'trade_bs_flag']
        # 20230103 '000004.SZ';'600345.SH' 验证，数量和值都OK
        # data_dir = '/home/data/my_pro/trade/'
        # data_file = f"{data_dir}/{date}/{code}.pkl"
        # data = pd.read_pickle(data_file)
        # data = data.rename(columns={"time_trade": 'MDTime', 'trade_volume': 'TradeQty', 'trade_money': 'TradeMoney', 'trade_price': 'LastPx'})
        # data['MDTime'] = data['MDTime'].astype(float)
        # data['LastPx'] = data['LastPx'].astype(float)
        # data['TradeQty'] = data['TradeQty'].astype(float)
        # data['TradeMoney'] = data['TradeMoney'].astype(float)
        ##################
        data_dir = f'{data_dir_root}/trans/'
        data_file = f"{data_dir}/{date[:4]}/{date}/{code}.pq"
        # print(111111111, data_file)
        # data_file = f"{data_dir}/{date[:4]}/{date}/{code}_ni.pq"
        if os.path.exists(data_file):
            data = pd.read_parquet(data_file)
            data['TradeMoney'] = data['TradeQty']*data['TradePrice']
            # print(11111111, data[['TradeQty', 'TradePrice', 'TradeMoney']])
            # print(11111111111, data.columns)
        else:
            data = pd.DataFrame(columns=['MDTime', 'TradeIndex', 'TradeType', 'order_type', 'TradeBSFlag', 'TradePrice', 'TradeQty', 'TradeSellNo', 'TradeBuyNo', 'TradeMoney'])
        data = data.sort_values(by=['MDTime', 'TradeIndex'])
        ##################
    elif data_type == "Order":
        # # ['time_trade', 'order_index', 'order_price', 'order_volume', 'order_code', 'order_type']  # sh  order_type  A/D  SZ 一个数字，每个股票就一个值。 应该是保留A
        # # 20230103 '000004.SZ';'600345.SH' 验证，数量和值都OK。
        # data_dir = '/home/data/my_pro/order/'
        # data_file = f"{data_dir}/{date}/{code}.pkl"
        # data = pd.read_pickle(data_file)
        # # data = data[data['order_type'] == "A"]
        # data = data.rename(columns={"time_trade": 'MDTime', 'order_index': 'OrderIndex'})
        # data['MDTime'] = data['MDTime'].astype(float)
        ###################
        data_dir = f'{data_dir_root}/order/'
        data_file = f"{data_dir}/{date[:4]}/{date}/{code}.pq"
        data = pd.read_parquet(data_file)
        data = data.sort_values(by=['MDTime', 'trd_index']) #
        ###################
    elif data_type == "Stock":
        # ['time_trade', 'order_index', 'order_price', 'order_volume', 'order_code', 'order_type']  # sh  order_type  A/D  SZ 一个数字，每个股票就一个值。 应该是保留A
        ###################
        # ['MDTime', 'TotaLVolumeTrade', 'TotalValueTrade', 'LastPx', 'HighPx', 'LowPx', 'vwap_tick', 'Open', 'PreClosePx']
        data_dir = f'{data_dir_root}/tick/'
        data_file = f"{data_dir}/{date[:4]}/{date}/{code}.pq"
        data = pd.read_parquet(data_file)
        data = data.rename(columns={"TotaLVolumeTrade":"TotalVolumeTrade", "Open":"OpenPx"})  # 临时
        data['TradingPhaseCode'] = '3'
        condition = (code == '3' and str(date) >= '20200824') or (code == '68')
        ul_pct = 1.2 if condition else 1.1
        dl_pct = 0.8 if condition else 0.9
        data['MaxPx'] = np.floor(data['PreClosePx'] * 100 * ul_pct + 0.5 + 1e-8) / 100
        data['MinPx'] = np.floor(data['PreClosePx'] * 100 * dl_pct + 0.5 + 1e-8) / 100
        data['Buy1OrderQty'] = 1e8  # 临时
        ###################
    elif data_type == "Stock":
        pass
    else:
        raise '不支持的格式，参考格式: Transaction、Order'
    return data

def get_data_by_date_2(data_type, code, date):
    # 合并一些小文件
    date = str(date).replace('-', '')
    if data_type == "Transaction":
        # # ['time_trade', 'trade_index', 'trade_buy_no', 'trade_sell_no', 'trade_price', 'trade_volume', 'trade_money', 'trade_bs_flag']
        # # 20230103 '000004.SZ';'600345.SH' 验证，数量和值都OK
        # data_dir = '/home/data/my_pro/trade/'
        # data_file = f"{data_dir}/{date}/{code}.pkl"
        # data = pd.read_pickle(data_file)
        # data = data.rename(columns={"time_trade": 'MDTime', 'trade_volume': 'TradeQty', 'trade_money': 'TradeMoney', 'trade_price': 'LastPx'})
        # data['MDTime'] = data['MDTime'].astype(float)
        # data['LastPx'] = data['LastPx'].astype(float)
        # data['TradeQty'] = data['TradeQty'].astype(float)
        # data['TradeMoney'] = data['TradeMoney'].astype(float)
        ##################
        # data_dir = '/home/data14_2/data/trans/'
        # data_file = f"{data_dir}/{date[:4]}/{date}/{code}.pq"
        # # data_file = f"{data_dir}/{date[:4]}/{date}/{code}_ni.pq"
        # data = pd.read_parquet(data_file)
        # data['TradeMoney'] = data['TradeQty']*data['TradePrice']
        # ################## 读大文件，读的时候直接过滤
        data_dir = '/home/data14_2/data_code/trans/'
        data_file = f"{data_dir}/{date[:4]}/{code}.pq"
        data = pd.read_parquet(data_file, filters=[('dt', '=', pd.to_datetime(str(date)))])
        data['TradeMoney'] = data['TradeQty']*data['TradePrice']
        ##################
    elif data_type == "Order":
        # # ['time_trade', 'order_index', 'order_price', 'order_volume', 'order_code', 'order_type']  # sh  order_type  A/D  SZ 一个数字，每个股票就一个值。 应该是保留A
        # # 20230103 '000004.SZ';'600345.SH' 验证，数量和值都OK。
        # data_dir = '/home/data/my_pro/order/'
        # data_file = f"{data_dir}/{date}/{code}.pkl"
        # data = pd.read_pickle(data_file)
        # # data = data[data['order_type'] == "A"]
        # data = data.rename(columns={"time_trade": 'MDTime', 'order_index': 'OrderIndex'})
        # data['MDTime'] = data['MDTime'].astype(float)
        ###################
        data_dir = '/home/data14_2/data/order/'
        data_file = f"{data_dir}/{date[:4]}/{date}/{code}.pq"
        data = pd.read_parquet(data_file)
        ###################
    else:
        raise '不支持的格式，参考格式: Transaction、Order'
    return data

########################################
from marketdata.jiekou import connent_by_clickhouse
def code_help(code):
    # 在 tushare 2012-2024 上验证过
    # 上海 6开头，    '600'   '601'  '603'   '605'  '688'  '689'
    # 深圳 0,3开头   '000', '001',  '002', '003',   '300', '301',  '302',
    code = str(int(float(code)))
    code = (6 - len(code)) * '0' + code
    if code[0] == '6':
        code += ".SH"
    elif code[0] in ['0', '3']:
        code += '.SZ'
    return code

def get_data_by_date(data_type, code, date):
    date = str(date).replace('-', '')
    if data_type in ['Transaction', 'Order', 'Stock_base']:
        # trans order_type
        data = connent_by_clickhouse(code.split('.')[0], date, data_type)
        if data.shape[0]:
            code = code_help(data['Ticker'].iloc[0])
            data['Ticker'] = code
        data = data.set_index(['dt', 'Ticker'])
    elif data_type in ['Stock']:
        # ['time_trade', 'order_index', 'order_price', 'order_volume', 'order_code', 'order_type']  # sh  order_type  A/D  SZ 一个数字，每个股票就一个值。 应该是保留A
        ###################
        # ['MDTime', 'TotaLVolumeTrade', 'TotalValueTrade', 'LastPx', 'HighPx', 'LowPx', 'vwap_tick', 'Open', 'PreClosePx']
        data_dir = '/data/baidu_netdisk/skk_data/data/data/tick/2016/'
        # data_dir = '/data/baidu_netdisk/skk_data/data/data/tick_ceshi/'
        data_file = f"{data_dir}/{date}/{code}.pq"
        if not os.path.exists(data_file):
            columns = ['MDTime', 'TotalVolumeTrade', 'TotalValueTrade', 'LastPx', 'HighPx', 'LowPx', 'vwap_tick', 'OpenPx', 'PreClosePx', 'TradingPhaseCode', 'MaxPx', 'MinPx', 'Buy1OrderQty']
            data = pd.DataFrame(columns=columns)
        else:
            data = pd.read_parquet(data_file)
            data = data.rename(columns={"TotaLVolumeTrade" : "TotalVolumeTrade", "Open" : "OpenPx"})  # 临时
            data['TradingPhaseCode'] = '3'
            condition = (code == '3' and str(date) >= '20200824') or (code == '68')
            ul_pct = 1.2 if condition else 1.1
            dl_pct = 0.8 if condition else 0.9
            data['MaxPx'] = np.floor(data['PreClosePx'] * 100 * ul_pct + 0.5 + 1e-8) / 100
            data['MinPx'] = np.floor(data['PreClosePx'] * 100 * dl_pct + 0.5 + 1e-8) / 100
            data['Buy1OrderQty'] = 1e8  # 临时
            data = data.drop_duplicates(subset=['MDTime'], keep='first')
            # data = data.astype(float)
            data['TradingPhaseCode'] = data['TradingPhaseCode'].astype(str)
            # for column in data.columns:
            #     if column not in ['exchange', 'datetime']:
            #         data[column] = data[column].astype(float)
        ###################
    else:
        raise '不支持的格式，参考格式: Transaction、Order'
    return data

if __name__ == '__main__':
    # date = "20230103"; code = '000004.SZ'; data_type = 'Transaction'
    # date = "20230103"; code = '600345.SH'; data_type = 'Transaction'
    # date = "20230103"; code = '000004.SZ'; data_type = 'Order'
    # date = "20230103"; code = '600345.SH'; data_type = 'Order'

    # date = "20230103"; code = '688246.SH'; data_type = 'Order'
    # date = "20230103"; code = '605288.SH'; data_type = 'Order'
    # date = "20230103"; code = '300576.SZ'; data_type = 'Order'  # 不同 code
    # date = "20230103"; code = '300222.SZ'; data_type = 'Order'
    # date = "20230103"; code = '002809.SZ'; data_type = 'Order'

    date = "20160104"; code = '000001.SZ'; data_type = 'Transaction'
    date = "20160104"; code = '000001.SZ'; data_type = 'Order'
    # date = "20160104"; code = '000001.SZ'; data_type = 'Stock'
    date = "20171229"; code = '300023.SZ'; data_type = 'Stock'
    data = get_data_by_date(data_type, code, date)  ##
    aaa = data.loc[data['TotalVolumeTrade']!=data['TotalVolumeTrade']]
    print(111111111, data.columns)
    print(111111111, data[['MDTime', 'TotalVolumeTrade']])
    print(111111111, aaa[['MDTime', 'TotalVolumeTrade']])

    begin_time = time.time()
    # date = "20160104"; code = '000001.SZ'; data_type = 'Transaction'
    # data = get_data_by_date_2(data_type, code, date)  ##
    # data['time_trade'] = data['time_trade'].astype(int)
    # data = data.query('time_trade>=103000000')
    # # data = data[['time_trade', 'trade_buy_no', 'trade_sell_no', 'trade_price', 'trade_volume']]  # trade
    # data = data[['time_trade', 'order_index', 'order_price', 'order_volume', 'order_code', 'order_type']]  ## Order
    print(time.time() - begin_time)
    # print(1111111111, data)
    # print(1111111111, data['order_type'].value_counts())

    # data = get_md_data()
    # print(data)
    # begin, end = 20230106, 20230114
    # begin, end = 20230113, -1
    # begin, end = 20230114, -1
    # begin, end = 20230113, 1
    # begin, end = 20230114, 1
    # result = get_trading_day(begin, end)
    # print(111111, result)

    # codes = get_all_codes(date=20230103, market='科创板')
    # print(111, len(codes), codes)

    # get_tradingday(pro, start_date, end_date=0, shift=0)
    trade_day = get_tradingday(None, start_date=20120101, end_date=20160104, shift=-40)
    print(1111111, trade_day)
