"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_029'
FACTOR_NAME = 'Stable_Medium_Channel_Location'
FORMULA = 'Cs_Rank(Div(Sub(Ts_Median(close, 10, 5), Ts_Min(low, 30, 15)), Add(Sub(Ts_Max(high, 30, 15), Ts_Min(low, 30, 15)), 0.001)))'
ECONOMIC_HYPOTHESIS = 'A short median price located high within a medium channel captures persistent anchoring with less turnover than the current close location.'
ECONOMIC_FAMILY = 'range_location_anchoring'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['range_location_anchoring', 'Extended_Position_Location']
INTERNAL_SUB_BATCH = 3
