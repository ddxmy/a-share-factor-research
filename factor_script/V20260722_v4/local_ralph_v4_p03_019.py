"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_019'
FACTOR_NAME = 'Median_VWAP_Session_Location'
FORMULA = 'Cs_Rank(Ts_Median(Div(Sub(vwap, low), Add(Sub(high, low), 0.001)), 20, 10))'
ECONOMIC_HYPOTHESIS = 'The median location of VWAP within the daily range measures where trading activity is persistently anchored rather than where the close alone lands.'
ECONOMIC_FAMILY = 'range_location_anchoring'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['range_location_anchoring', 'VWAP_Deviation_Rank']
INTERNAL_SUB_BATCH = 2
