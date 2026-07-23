"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_018'
FACTOR_NAME = 'Intraday_Range_Direction_Asymmetry'
FORMULA = 'Neg(Cs_Rank(Sub(Ts_Mean(If(Less(Sub(close, open), 0), Div(Sub(high, low), pre_close), 0), 30, 15), Ts_Mean(If(Greater(Sub(close, open), 0), Div(Sub(high, low), pre_close), 0), 30, 15))))'
ECONOMIC_HYPOTHESIS = 'Wider ranges on down intraday sessions than on up sessions reveal downside price-formation fragility beyond close-to-close volatility.'
ECONOMIC_FAMILY = 'volatility_asymmetry'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['volatility_asymmetry', 'Intraday_Position_Ratio']
INTERNAL_SUB_BATCH = 2
