"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_026'
FACTOR_NAME = 'Turnover_Shock_Price_Fragility'
FORMULA = 'Neg(Cs_Rank(Mul(Abs(Returns), Ts_ZScore(turn, 40, 20))))'
ECONOMIC_HYPOTHESIS = 'Large price moves occurring with unusually high turnover expose fragile attention shocks that are more likely to reverse than low-impact participation.'
ECONOMIC_FAMILY = 'liquidity_amount_shocks'
DATA_DOMAIN = 'turnover_size_liquidity'
TARGET_PATTERNS = ['liquidity_amount_shocks']
INTERNAL_SUB_BATCH = 3
