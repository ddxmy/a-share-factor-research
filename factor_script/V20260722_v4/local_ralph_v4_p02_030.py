"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_030'
FACTOR_NAME = 'Bidirectional_Gap_Intraday_Beta_Asymmetry'
FORMULA = 'Cs_Rank(Sub(Ts_Beta(Div(Sub(close, open), open), Div(Sub(open, pre_close), pre_close), 40, 20), Ts_Beta(Div(Sub(open, pre_close), pre_close), Div(Sub(close, open), open), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'The asymmetry between intraday response to gaps and gap response to intraday moves distinguishes overnight information transmission from mechanical daily covariance.'
ECONOMIC_FAMILY = 'overnight_intraday_decomposition'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['overnight_intraday_decomposition']
INTERNAL_SUB_BATCH = 3
