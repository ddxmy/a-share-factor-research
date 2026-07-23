"""Sealed candidate from local_ralph_20260722_v4, Pack 02."""

CAMPAIGN_VERSION = 'local_ralph_20260722_v4'
PACK_NUMBER = 2
CANDIDATE_ID = 'local_ralph_v4_p02_006'
FACTOR_NAME = 'Upper_Lower_Tail_Stretch_Ratio'
FORMULA = 'Neg(Cs_Rank(Div(Sub(Ts_Quantile(Returns, 60, 0.95, 30), Ts_Median(Returns, 60, 30)), Add(Sub(Ts_Median(Returns, 60, 30), Ts_Quantile(Returns, 60, 0.05, 30)), 0.001))))'
ECONOMIC_HYPOTHESIS = 'An unusually stretched upper return tail relative to the lower tail reflects lottery-like upside concentration and subsequent overpricing.'
ECONOMIC_FAMILY = 'return_tails_skewness'
DATA_DOMAIN = 'market_price_volume'
TARGET_PATTERNS = ['return_tails_skewness']
INTERNAL_SUB_BATCH = 1
