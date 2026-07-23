# 本地因子研究流程

该目录替代原仓库中只能在 Linux x86_64 / Python 3.8 环境运行的 `run_factor.so + FactorTest` 评估环节，用于在本机复现因子计算并做透明的截面回测。默认从 `../factor_script/` 的非 `_retired` 脚本读取 `FACTOR_NAME` 和 `FORMULA`，即以项目实际产出的因子脚本为研究对象，而不是只回测当前库中 4 个已入库因子。不会执行脚本中的旧服务器交易日接口；公式含义与脚本一致，数据窗口由本地 parquet 的实际交易日决定。

## 数据契约

传入一个日频 parquet。`dt` 与 `Ticker` 可以是列，也可以是 parquet 中持久化的索引层级；`dt` 可被解析为日期，`Ticker` 为字符串。为保持与原因子计算一致，数据至少应包含：

`dt, Ticker, open, high, low, close, volume, amt, vwap, pre_close, pct_chg, total_shares, free_float_shares, adjfactor, mkt_cap_ard, turn`

`close` 应是复权价；若提供 `adjfactor`，项目公式引擎会按原逻辑再做一次复权，因此请使用**未复权 OHLCV + adjfactor**，或将 `adjfactor` 设为 1。原项目同样会对创业板（2020-08-24 起）和科创板进行涨跌停尺度统一处理。

## 执行

先安装原项目所需的 Python 依赖：

```bash
cd /Users/mingyuxu/Desktop/因子挖掘/factor-mining-experiment-master
python3 -m pip install -r requirements.txt
```

先从 Tushare 拉取可复现的本地数据（默认 2023-01-03 至 2025-06-30）：

```bash
python3 local_research/download_tushare_data.py
```

下载器按交易日合并 `daily`、`daily_basic`、`adj_factor`，并保存数据来源、行数、字段和失败日期到同名 `manifest.json`。需要先在环境中设置 `TUSHARE_TOKEN`；token 不会写入项目。

另行拉取沪深300的月度历史成分权重。脚本会额外请求回测开始月份的前一个月，并仅从快照自身日期开始向后使用，避免用月末成分倒填月初：

```bash
python3 local_research/download_hs300_membership.py \
  --start-date 20220101 --end-date 20240430
```

运行全部入库因子：

```bash
python3 local_research/backtest.py \
  --market-data local_research/data/tushare_a_share_daily.parquet \
  --universe-membership local_research/data/universe/hs300_index_weight.parquet \
  --start-date 20230103 --end-date 20250630 \
  --split-date 20240101 --cost-bps 10
```

只运行某个脚本，例如 `factor_script/V20260707/xzt_20260707_4.py`：

```bash
python3 local_research/backtest.py --market-data /absolute/path/to/market_data.parquet --factor xzt_20260707_4
```

如需只回测 4 个“正式入库”因子，可切换为因子库来源，并传入库中的数值 ID：

```bash
python3 local_research/backtest.py --market-data /absolute/path/to/market_data.parquet --source library --factor 4
```

结果默认写入 `local_research/results/`：

- `factor_summary.csv`：每个因子、每个样本段的 IC、ICIR、年化收益/波动、Sharpe、最大回撤、换手和累计交易成本；
- `factor_<id>_<period>_daily.csv`：每日多空收益、成本、换手和 IC，可用于画净值图；
- `factor_signal_rank_correlation.csv`：股票池内逐日截面排名拼接后的因子相关矩阵，用于识别高度冗余因子；
- `universe_metadata.json`：股票池快照日期、覆盖交易日和平均成分数量；
- `failures.json`：未能计算的因子及原因。

批量回测后，以训练期平均 Rank IC 的符号确定因子方向，并冻结到验证期，再执行稳定性门槛与相关性聚类：

```bash
python3 local_research/analyze_hs300_results.py \
  --results-dir local_research/results/hs300_all_factors_202202_202404
```

该步骤生成 `factor_oriented_audit.csv` 和 `factor_audit_report.json`。默认门槛为训练/验证定向后 Rank IC 均不低于 0.02、验证期月度 IC 胜率不低于 50%、信号覆盖率不低于 95%；再按绝对相关系数 0.8 聚类。因子方向不会根据验证期重新选择。

## 口径与边界

- **T-1 对齐**：`t` 日收盘后可观测的因子预测 `t→t+1` 的复权 close-to-close 收益；收益目标向前移动一日，因子本身不再额外滞后。
- **收益口径**：因子值继续沿用原项目的注册制尺度归一化，但组合收益使用原始行情乘复权因子的真实复权收盘价，避免将创业板和科创板实际收益错误减半。
- **组合构建**：每日按因子值等权分为 5 组，做多最高组、做空最低组；默认单边成本 10 bps，按权重变化计算换手与成本。
- **股票池**：传入 `--universe-membership` 时，使用每个交易日当时已知的最近一期沪深300权重快照；快照公布日前不会向后看。月末权重并不等同于精确的指数调仓生效记录，因此最终报告会把这一点列为数据边界。
- **样本外检验**：传入 `--split-date` 后，脚本分别产出切分日前后的结果；简历中应重点报告样本外 IC/IR、成本后 Sharpe 与最大回撤，而不是沿用旧 `tot_score`。
- **尚未纳入的现实约束**：停牌、涨跌停不可交易、ST、新股、行业/市值中性化以及融资融券可得性。这些需要结合你最终使用的数据字段和实盘约束再补充，不能默认声称已处理。
