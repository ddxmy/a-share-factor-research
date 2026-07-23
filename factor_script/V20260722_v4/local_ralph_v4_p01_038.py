"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_038'
FACTOR_NAME = 'Session_Close_Location_Instability'
FORMULA = 'Neg(Cs_Rank(Ts_Std(Div(Sub(close, low), Add(Sub(high, low), 0.001)), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Unstable closing location within the daily range indicates inconsistent end-of-day control and lower-quality price discovery.'
ECONOMIC_FAMILY = 'range_location_anchoring'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['Close_Position_Location', 'range_location_anchoring']
INTERNAL_SUB_BATCH = 4
