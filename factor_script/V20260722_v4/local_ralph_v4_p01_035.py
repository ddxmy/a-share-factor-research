"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_035'
FACTOR_NAME = 'Low_Open_Location_Intraday_Recovery'
FORMULA = 'Cs_Rank(Ts_Mean(If(Less(Div(Sub(open, low), Add(Sub(high, low), 0.001)), 0.25), Div(Sub(close, open), open), 0), 40, 20))'
ECONOMIC_HYPOTHESIS = 'Intraday recovery after opening near the session low measures absorption of early selling pressure and may identify resilient demand.'
ECONOMIC_FAMILY = 'range_location_anchoring'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['Intraday_Position_Ratio', 'range_location_anchoring']
INTERNAL_SUB_BATCH = 4
