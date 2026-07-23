"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_034'
FACTOR_NAME = 'Lagged_Amount_Participation_Decoupling'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(Returns, Ts_Delay(Ts_ZScore(Log(amt), 20, 10), 1), 30, 15)))'
ECONOMIC_HYPOTHESIS = 'Returns tightly linked to prior abnormal amount can represent delayed attention pressure, while weak linkage indicates more independent price discovery.'
ECONOMIC_FAMILY = 'price_volume_turnover_divergence'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['price_volume_turnover_divergence']
INTERNAL_SUB_BATCH = 4
