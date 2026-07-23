"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_040'
FACTOR_NAME = 'Extreme_Gap_Intraday_Absorption'
FORMULA = 'Neg(Cs_Rank(Ts_Mean(If(Greater(Abs(Div(Sub(open, pre_close), pre_close)), Ts_Std(Div(Sub(open, pre_close), pre_close), 30, 15)), Mul(Sign(Div(Sub(open, pre_close), pre_close)), Div(Sub(close, open), open)), 0), 30, 15)))'
ECONOMIC_HYPOTHESIS = 'Same-day movement aligned with the direction of an unusually large gap indicates continuation, while a negative score captures intraday absorption of extreme overnight shocks.'
ECONOMIC_FAMILY = 'overnight_intraday_decomposition'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['overnight_intraday_decomposition', 'price_pressure_reversal']
INTERNAL_SUB_BATCH = 4
