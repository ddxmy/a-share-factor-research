"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_018'
FACTOR_NAME = 'VWAP_Open_Close_Range_Alignment'
FORMULA = 'Cs_Rank(Ts_Mean(Mul(Div(Sub(vwap, open), Add(Sub(high, low), 0.001)), Div(Sub(close, vwap), Add(Sub(high, low), 0.001))), 20, 10))'
ECONOMIC_HYPOTHESIS = 'When VWAP moves away from the open and the close extends in the same direction beyond VWAP, the session shows broad participation rather than endpoint noise.'
ECONOMIC_FAMILY = 'range_location_anchoring'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['range_location_anchoring', 'Intraday_Position_Ratio']
INTERNAL_SUB_BATCH = 2
