"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_008'
FACTOR_NAME = 'Prior_Channel_Breakout_Location'
FORMULA = 'Cs_Rank(Div(Sub(close, Ts_Delay(Ts_Min(low, 40, 20), 1)), Add(Sub(Ts_Delay(Ts_Max(high, 40, 20), 1), Ts_Delay(Ts_Min(low, 40, 20), 1)), 0.001)))'
ECONOMIC_HYPOTHESIS = "Positioning the current close against yesterday's completed channel isolates genuine breakouts from mechanically moving same-day range anchors."
ECONOMIC_FAMILY = 'range_location_anchoring'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['range_location_anchoring']
INTERNAL_SUB_BATCH = 1
