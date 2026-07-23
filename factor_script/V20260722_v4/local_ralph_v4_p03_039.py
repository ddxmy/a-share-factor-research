"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_039'
FACTOR_NAME = 'Prior_Return_Overnight_Response_Reversal'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(Div(Sub(open, pre_close), pre_close), Ts_Delay(Returns, 1), 30, 15)))'
ECONOMIC_HYPOTHESIS = 'Systematic overnight continuation of the prior full-session return can reflect delayed extrapolation that is subsequently vulnerable to reversal.'
ECONOMIC_FAMILY = 'overnight_intraday_decomposition'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['overnight_intraday_decomposition']
INTERNAL_SUB_BATCH = 4
