"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_033'
FACTOR_NAME = 'Overnight_To_Intraday_Risk_Dominance'
FORMULA = 'Neg(Cs_Rank(Div(Ts_Std(Div(Sub(open, pre_close), pre_close), 40, 20), Add(Ts_Mean(Abs(Div(Sub(close, open), open)), 40, 20), 0.001))))'
ECONOMIC_HYPOTHESIS = 'Stocks whose risk is concentrated in discontinuous overnight gaps rather than intraday price discovery may carry persistent information and execution fragility.'
ECONOMIC_FAMILY = 'overnight_intraday_decomposition'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['overnight_intraday_decomposition', 'volatility_asymmetry']
INTERNAL_SUB_BATCH = 4
