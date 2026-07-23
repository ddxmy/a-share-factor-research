"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_027'
FACTOR_NAME = 'Amount_Volume_Growth_Decoupling'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(Ts_Return(amt, 2), Ts_Return(volume, 2), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Weak co-movement between trading amount and share volume can reveal price-level or trade-size distortions not explained by ordinary participation growth.'
ECONOMIC_FAMILY = 'price_volume_turnover_divergence'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 3
