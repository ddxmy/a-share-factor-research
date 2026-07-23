"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_026'
FACTOR_NAME = 'Range_Normalized_Return_Pressure'
FORMULA = 'Neg(Cs_Rank(Ts_EMA(Div(Returns, Add(Div(Sub(high, low), pre_close), 0.001)), 5, 3)))'
ECONOMIC_HYPOTHESIS = 'Recent returns large relative to their intraday ranges proxy for concentrated directional pressure that is more likely to mean-revert.'
ECONOMIC_FAMILY = 'price_pressure_reversal'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_pressure_reversal']
INTERNAL_SUB_BATCH = 3
