"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_036'
FACTOR_NAME = 'Consecutive_Gain_Turnover_Exhaustion'
FORMULA = 'Neg(Cs_Rank(Ts_Mean(If(And(Greater(Returns, 0), Greater(Ts_Delay(Returns, 1), 0)), Ts_Return(turn, 1), 0), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Turnover acceleration after consecutive gains captures participation exhaustion and crowded continuation rather than generic amount or turnover shocks.'
ECONOMIC_FAMILY = 'liquidity_amount_shocks'
DATA_DOMAIN = 'turnover_size_liquidity'
TARGET_PATTERNS = ['liquidity_amount_shocks', 'price_pressure_reversal']
INTERNAL_SUB_BATCH = 4
