"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_028'
FACTOR_NAME = 'Unexpected_Price_Impact_Reversal'
FORMULA = 'Neg(Cs_Rank(Ts_ZScore(Div(Abs(Returns), Add(turn, 0.1)), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'An extreme current price move per unit turnover reflects temporary depth scarcity and should mean-revert as liquidity normalizes.'
ECONOMIC_FAMILY = 'liquidity_amount_shocks'
DATA_DOMAIN = 'turnover_size_liquidity'
TARGET_PATTERNS = ['liquidity_amount_shocks', 'price_pressure_reversal']
INTERNAL_SUB_BATCH = 3
