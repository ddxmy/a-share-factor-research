"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_028'
FACTOR_NAME = 'Volatility_Of_Volatility_Instability'
FORMULA = 'Neg(Cs_Rank(Div(Ts_Std(Ts_Std(Returns, 10, 5), 30, 15), Add(Ts_Mean(Ts_Std(Returns, 10, 5), 30, 15), 0.001))))'
ECONOMIC_HYPOTHESIS = 'Variation in short-run realized volatility relative to its level identifies unstable risk regimes even when average volatility is moderate.'
ECONOMIC_FAMILY = 'volatility_asymmetry'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['volatility_asymmetry', 'conditional_regimes']
INTERNAL_SUB_BATCH = 3
