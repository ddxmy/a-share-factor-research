"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_037'
FACTOR_NAME = 'Serial_Confirmation_Weighted_Trend'
FORMULA = 'Cs_Rank(Mul(Ts_Return(close, 40), Ts_Correlation(Returns, Ts_Delay(Returns, 1), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Medium-horizon returns supported by positive serial dependence represent persistent repricing, whereas the same endpoint return with alternating daily signs is less reliable.'
ECONOMIC_FAMILY = 'trend_quality_path_efficiency'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['trend_quality_path_efficiency']
INTERNAL_SUB_BATCH = 4
