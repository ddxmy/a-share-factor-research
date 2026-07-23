"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_036'
FACTOR_NAME = 'Range_Compression_Mode_Switch'
FORMULA = 'If(Less(Div(Ts_Mean(Div(Sub(high, low), pre_close), 5, 3), Add(Ts_Mean(Div(Sub(high, low), pre_close), 30, 15), 0.001)), 0.7), Cs_Rank(Ts_Return(close, 10)), Neg(Cs_Rank(Ts_Return(close, 3))))'
ECONOMIC_HYPOTHESIS = 'Compressed ranges favor breakout continuation, whereas normal or expanded ranges favor short reversal after pressure has already been expressed.'
ECONOMIC_FAMILY = 'conditional_regimes'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['conditional_regimes', 'range_location_anchoring', 'price_pressure_reversal']
INTERNAL_SUB_BATCH = 4
