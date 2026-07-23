"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_030'
FACTOR_NAME = 'Lagged_Return_Volume_Response'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(Ts_Delay(Returns, 1), Ts_Return(volume, 1), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'A strong next-session volume response to prior returns can indicate delayed attention and crowded follow-through, creating reversal pressure after participation catches up.'
ECONOMIC_FAMILY = 'price_volume_turnover_divergence'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 3
