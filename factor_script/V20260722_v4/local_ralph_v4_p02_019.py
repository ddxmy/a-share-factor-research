"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_019'
FACTOR_NAME = 'Amount_Range_Change_Decoupling'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(Ts_Delta(Log(amt), 1), Ts_Delta(Div(Sub(high, low), pre_close), 1), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Large amount changes that fail to translate consistently into range expansion indicate absorption, while tight coupling indicates fragile price impact.'
ECONOMIC_FAMILY = 'price_volume_turnover_divergence'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 2
