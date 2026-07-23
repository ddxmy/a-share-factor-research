"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_037'
FACTOR_NAME = 'Trading_Amount_Range_Absorption_Beta'
FORMULA = 'Neg(Cs_Rank(Ts_Beta(Div(Sub(high, low), pre_close), Log(amt), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Low range sensitivity to trading amount indicates liquidity absorption, while unusually high sensitivity reveals fragile depth; this differs from shock z-scores and tail replenishment.'
ECONOMIC_FAMILY = 'liquidity_amount_shocks'
DATA_DOMAIN = 'turnover_size_liquidity'
TARGET_PATTERNS = ['liquidity_amount_shocks']
INTERNAL_SUB_BATCH = 4
