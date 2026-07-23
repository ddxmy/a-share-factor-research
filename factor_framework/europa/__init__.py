# coding:utf-8
"""
因子注册表 —— 自动发现 europa/ 下所有 V* 日期目录中的 factor_*.py 模块。

目录结构约定:
    europa/
        V20250930/
            factor_order_example.py
            factor_trade_example.py
            ...

新增因子时，只需在对应日期目录下创建 factor_*.py 文件，并定义:
    FACTOR_NAME:  因子名称
    FACTOR_TYPE:  因子类型 (TOrder / TTransaction / T-1_factor 等)
    factor_{FACTOR_NAME}():  因子计算函数

无需手动修改本文件。
"""

import importlib
import os
import pkgutil
import sys

# 将 marketdata 的父目录加入 sys.path（而非 marketdata 本身），
# 以便 from marketdata import get_tradingday 能正确找到 marketdata 包
_marketdata_path = os.path.join(os.path.dirname(__file__), '..', '..')
_marketdata_path = os.path.abspath(_marketdata_path)
if _marketdata_path not in sys.path:
    sys.path.insert(0, _marketdata_path)
# 备选: 公共 marketdata
_pub_md_path = '/workspace/public/factor_mining'
if os.path.isdir(os.path.join(_pub_md_path, 'marketdata')) and _pub_md_path not in sys.path:
    sys.path.insert(0, _pub_md_path)

FACTORS = {}

# 扫描目录列表: europa/ 和 factor_script/
_scan_dirs = [
    os.path.dirname(__file__),  # europa/
    os.path.join(os.path.dirname(__file__), '..', '..', 'factor_script'),  # factor_script/
]

for _base_dir in _scan_dirs:
    _base_dir = os.path.abspath(_base_dir)
    if not os.path.isdir(_base_dir):
        continue

    _version_dirs = sorted(
        d for d in os.listdir(_base_dir)
        if d.startswith('V') and os.path.isdir(os.path.join(_base_dir, d))
    )

    for _ver_dir in _version_dirs:
        ver_path = os.path.join(_base_dir, _ver_dir)

        # 构建包路径
        rel_path = os.path.relpath(ver_path, os.path.join(os.path.dirname(__file__), '..', '..'))
        ver_package = rel_path.replace(os.sep, '.')

        for _, module_name, _ in pkgutil.iter_modules([ver_path]):
            # factor_script 下的文件名不含 factor_ 前缀，直接导入
            if not module_name.startswith('factor_') and 'factor_script' not in _base_dir:
                continue

            mod = importlib.import_module(f'{ver_package}.{module_name}')

            # 读取模块级元信息常量
            factor_name = getattr(mod, 'FACTOR_NAME', None)
            factor_type = getattr(mod, 'FACTOR_TYPE', None)

            if factor_name is None or factor_type is None:
                continue

            # 按约定获取因子函数: factor_{factor_name}
            func_name = f'factor_{factor_name}'
            factor_func = getattr(mod, func_name, None)

            if factor_func is None:
                continue

            FACTORS[factor_name] = (factor_func, factor_type)
