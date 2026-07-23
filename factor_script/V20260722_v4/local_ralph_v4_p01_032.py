"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_032'
FACTOR_NAME = 'Positive_Gap_Intraday_Fade'
FORMULA = 'Neg(Cs_Rank(Ts_Mean(If(Greater(Div(Sub(open, pre_close), pre_close), 0), Mul(Div(Sub(open, pre_close), pre_close), Div(Sub(close, open), open)), 0), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'The interaction between positive gaps and same-day intraday moves measures whether overnight optimism is systematically reinforced or faded after the open.'
ECONOMIC_FAMILY = 'overnight_intraday_decomposition'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['overnight_intraday_decomposition']
INTERNAL_SUB_BATCH = 4
