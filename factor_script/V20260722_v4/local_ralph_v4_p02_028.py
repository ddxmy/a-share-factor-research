"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_028'
FACTOR_NAME = 'Close_Location_Two_Sided_Anchor_Recency'
FORMULA = 'Cs_Rank(Mul(Div(Sub(close, Ts_Min(low, 60, 30)), Add(Sub(Ts_Max(high, 60, 30), Ts_Min(low, 60, 30)), 0.001)), Div(Sub(Ts_ArgMin(low, 60, 30), Ts_ArgMax(high, 60, 30)), 60)))'
ECONOMIC_HYPOTHESIS = 'Current range location is more informative when combined with the ordering of the most recent low and high, distinguishing mature trends from stale endpoints.'
ECONOMIC_FAMILY = 'range_location_anchoring'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['range_location_anchoring', 'Close_Position_Location']
INTERNAL_SUB_BATCH = 3
