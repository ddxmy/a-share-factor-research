"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_009'
FACTOR_NAME = 'Median_Session_Close_Location'
FORMULA = 'Cs_Rank(Ts_Median(Div(Sub(close, low), Add(Sub(high, low), 0.001)), 20, 10))'
ECONOMIC_HYPOTHESIS = 'The rolling median of daily close location distinguishes consistently strong session finishes from noisy one-day range endpoints.'
ECONOMIC_FAMILY = 'range_location_anchoring'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['range_location_anchoring', 'Close_Position_Location']
INTERNAL_SUB_BATCH = 1
