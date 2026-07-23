"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_031'
FACTOR_NAME = 'Gap_Intraday_Skew_Differential'
FORMULA = 'Neg(Cs_Rank(Sub(Ts_Skewness(Div(Sub(open, pre_close), pre_close), 40, 20), Ts_Skewness(Div(Sub(close, open), open), 40, 20))))'
ECONOMIC_HYPOTHESIS = 'A more positively skewed overnight component than intraday component can reflect opening-price lottery demand that is subsequently absorbed during continuous trading.'
ECONOMIC_FAMILY = 'overnight_intraday_decomposition'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['overnight_intraday_decomposition']
INTERNAL_SUB_BATCH = 4
