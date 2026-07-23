"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_040'
FACTOR_NAME = 'Post_Tail_Turnover_Replenishment'
FORMULA = 'Cs_Rank(Ts_Mean(If(Less(Returns, Ts_Quantile(Returns, 40, 0.1, 20)), Ts_Return(turn, 1), 0), 40, 20))'
ECONOMIC_HYPOTHESIS = 'Turnover recovery following lower-tail returns measures whether liquidity providers and new participants replenish immediately after stress.'
ECONOMIC_FAMILY = 'liquidity_amount_shocks'
DATA_DOMAIN = 'turnover_size_liquidity'
TARGET_PATTERNS = ['liquidity_amount_shocks', 'return_tails_skewness']
INTERNAL_SUB_BATCH = 4
