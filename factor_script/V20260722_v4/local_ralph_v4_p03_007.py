"""Sealed candidate from local_ralph_20260722_v4, Pack 03."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 3
CANDIDATE_ID = 'local_ralph_v4_p03_007'
FACTOR_NAME = 'Lower_Tail_Event_Frequency_Aversion'
FORMULA = 'Neg(Cs_Rank(Ts_Mean(If(Less(Returns, Ts_Quantile(Returns, 40, 0.1, 20)), 1, 0), 40, 20)))'
ECONOMIC_HYPOTHESIS = 'Frequent lower-tail sessions indicate recurring jump risk even when individual losses are moderate, warranting a preference against clustered downside events.'
ECONOMIC_FAMILY = 'return_tails_skewness'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['return_tails_skewness']
INTERNAL_SUB_BATCH = 1
