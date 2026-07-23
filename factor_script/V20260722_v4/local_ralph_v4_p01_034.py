"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_034'
FACTOR_NAME = 'Gap_Direction_State_Persistence'
FORMULA = 'Neg(Cs_Rank(Ts_Correlation(Sign(Div(Sub(open, pre_close), pre_close)), Ts_Delay(Sign(Div(Sub(open, pre_close), pre_close)), 1), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Persistent same-direction opening gaps may reflect crowded overnight extrapolation and become vulnerable once repeated opening pressure is exhausted.'
ECONOMIC_FAMILY = 'overnight_intraday_decomposition'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['overnight_intraday_decomposition', 'conditional_regimes']
INTERNAL_SUB_BATCH = 4
