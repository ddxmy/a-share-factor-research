"""Sealed candidate from local_ralph_20260722_v4, Pack 01."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 1
CANDIDATE_ID = 'local_ralph_v4_p01_021'
FACTOR_NAME = 'Upper_Tail_Return_Aversion'
FORMULA = 'Neg(Cs_Rank(Ts_Quantile(Returns, 40, 0.9, 20)))'
ECONOMIC_HYPOTHESIS = 'Repeatedly large upside returns can reflect lottery-like demand and over-extrapolation, creating a preference against high upper-tail realizations.'
ECONOMIC_FAMILY = 'return_tails_skewness'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['return_tails_skewness']
INTERNAL_SUB_BATCH = 3
