"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_010'
FACTOR_NAME = 'Smoothed_Gap_Intraday_Residual'
FORMULA = 'Cs_Rank(Ts_Mean(Ts_Residual(Div(Sub(open, pre_close), pre_close), Div(Sub(close, open), open), 40, 20), 10, 5))'
ECONOMIC_HYPOTHESIS = 'The component of overnight gaps unexplained by same-session intraday returns captures information arriving outside continuous trading rather than simple daily continuation.'
ECONOMIC_FAMILY = 'overnight_intraday_decomposition'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['overnight_intraday_decomposition']
INTERNAL_SUB_BATCH = 1
