"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_024'
FACTOR_NAME = 'Range_Kurtosis_Aversion'
FORMULA = 'Neg(Cs_Rank(Ts_Kurtosis(Div(Sub(high, low), pre_close), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Frequent extreme intraday ranges reveal discontinuous liquidity and tail-prone price formation even when close-to-close volatility appears moderate.'
ECONOMIC_FAMILY = 'volatility_asymmetry'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['volatility_asymmetry', 'return_tails_skewness']
INTERNAL_SUB_BATCH = 3
